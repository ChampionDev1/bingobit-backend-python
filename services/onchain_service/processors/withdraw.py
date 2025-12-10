"""
Withdraw Processor - Handles user withdrawal requests
Executes transactions from hot wallet to user's external address
"""
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from common import (
    Config, setup_logger,
    lamports_to_sol, sol_to_lamports
)
from common.kafka_producer import DepositEventProducer
from services.onchain_service.blockchain import SolanaClient

logger = setup_logger(__name__)

class WithdrawProcessor:
    """
    Process withdrawal requests from users
    
    Flow:
    1. Validate request (address, amount, balance)
    2. Execute transaction from hot wallet
    3. Monitor transaction confirmations
    4. Broadcast status via Kafka
    """
    
    def __init__(self, chain: str = "solana"):
        self.chain = chain.lower()
        self.solana_client = SolanaClient()
        self.kafka_producer = DepositEventProducer()
        
        self.hot_wallet_address = Config.SOLANA_HOT_WALLET_ADDRESS
        self.hot_wallet_keypair = None
        
        if Config.SOLANA_HOT_WALLET_PRIVATE_KEY:
            self.hot_wallet_keypair = self.solana_client.keypair_from_private_key(
                Config.SOLANA_HOT_WALLET_PRIVATE_KEY
            )
        
        logger.info(f"WithdrawProcessor initialized for chain: {self.chain}")
    
    def process_withdrawal(
        self,
        user_id: str,
        to_address: str,
        amount: str
    ) -> Dict[str, Any]:
        """
        Process withdrawal request
        
        Args:
            user_id: User identifier
            to_address: Destination address
            amount: Amount to withdraw (in SOL)
        
        Returns:
            Result dict with success status and tx_hash
        """
        logger.info(
            f"Processing withdrawal: user={user_id}, "
            f"to={to_address}, amount={amount} {self.chain.upper()}"
        )
        
        try:
            # Step 1: Validate request
            validation_result = self._validate_withdrawal(to_address, amount)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": validation_result["error"],
                    "tx_hash": ""
                }
            
            amount_lamports = validation_result["amount_lamports"]
            
            # Step 2: Broadcast initiated event
            self._send_withdraw_initiated_event(user_id, to_address, amount)
            
            # Step 3: Execute transaction
            tx_hash = self._execute_withdrawal(to_address, amount_lamports)
            
            if not tx_hash:
                self._send_withdraw_failed_event(
                    user_id, to_address, amount,
                    "Failed to execute transaction"
                )
                return {
                    "success": False,
                    "message": "Failed to execute withdrawal transaction",
                    "tx_hash": ""
                }
            
            logger.info(f"Withdrawal transaction sent: {tx_hash}")
            
            # Step 4: Broadcast pending event
            self._send_withdraw_pending_event(user_id, to_address, amount, tx_hash)
            
            # Step 5: Monitor confirmations (async in background)
            # Note: In production, this should be handled by a separate monitor
            # For now, we'll wait for initial confirmation
            confirmed = self.solana_client.wait_for_confirmation(
                tx_hash,
                timeout=Config.TRANSACTION_TIMEOUT,
                required_confirmations=1  # Just initial confirmation
            )
            
            if confirmed:
                # Broadcast confirming event
                self._send_withdraw_confirming_event(user_id, to_address, amount, tx_hash)
                
                # Full confirmation will be monitored separately
                logger.info(f"Withdrawal confirmed: {tx_hash}")
                
                return {
                    "success": True,
                    "message": "Withdrawal transaction confirmed",
                    "tx_hash": tx_hash
                }
            else:
                logger.warning(f"Withdrawal not confirmed in time: {tx_hash}")
                return {
                    "success": True,  # Transaction sent, but not confirmed yet
                    "message": "Withdrawal transaction sent, pending confirmation",
                    "tx_hash": tx_hash
                }
            
        except Exception as e:
            logger.error(f"Withdrawal processing error: {e}", exc_info=True)
            self._send_withdraw_failed_event(user_id, to_address, amount, str(e))
            return {
                "success": False,
                "message": f"Withdrawal failed: {str(e)}",
                "tx_hash": ""
            }
    
    def _validate_withdrawal(self, to_address: str, amount: str) -> Dict[str, Any]:
        """
        Validate withdrawal request
        
        Checks:
        1. Valid destination address
        2. Valid amount
        3. Sufficient hot wallet balance
        4. Amount above minimum
        """
        try:
            # Validate address format
            from common.utils import validate_solana_address
            if not validate_solana_address(to_address):
                return {
                    "valid": False,
                    "error": "Invalid destination address format"
                }
            
            # Validate amount
            try:
                amount_float = float(amount)
                if amount_float <= 0:
                    return {
                        "valid": False,
                        "error": "Amount must be positive"
                    }
                
                amount_lamports = sol_to_lamports(amount_float)
                
            except ValueError:
                return {
                    "valid": False,
                    "error": "Invalid amount format"
                }
            
            # Check minimum withdrawal amount
            if amount_lamports < Config.MIN_DEPOSIT_AMOUNT:  # Reuse same minimum
                min_sol = lamports_to_sol(Config.MIN_DEPOSIT_AMOUNT)
                return {
                    "valid": False,
                    "error": f"Amount below minimum: {min_sol} SOL"
                }
            
            # Check hot wallet balance
            hot_wallet_balance = self.solana_client.get_balance(self.hot_wallet_address)
            estimated_fee = self.solana_client.estimate_fee()
            required_balance = amount_lamports + estimated_fee
            
            if hot_wallet_balance < required_balance:
                return {
                    "valid": False,
                    "error": f"Insufficient hot wallet balance. "
                            f"Required: {lamports_to_sol(required_balance)} SOL, "
                            f"Available: {lamports_to_sol(hot_wallet_balance)} SOL"
                }
            
            logger.info(
                f"Withdrawal validation passed: {amount} SOL to {to_address}"
            )
            
            return {
                "valid": True,
                "amount_lamports": amount_lamports
            }
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "valid": False,
                "error": f"Validation failed: {str(e)}"
            }
    
    def _execute_withdrawal(self, to_address: str, amount_lamports: int) -> Optional[str]:
        """
        Execute withdrawal transaction from hot wallet
        
        Args:
            to_address: Destination address
            amount_lamports: Amount in lamports
        
        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            if not self.hot_wallet_keypair:
                raise ValueError("Hot wallet keypair not configured")
            
            logger.info(
                f"Executing withdrawal: {lamports_to_sol(amount_lamports)} SOL "
                f"from hot wallet to {to_address}"
            )
            
            # Send transaction with retry
            tx_hash = self.solana_client.send_transaction_with_retry(
                self.hot_wallet_keypair,
                to_address,
                amount_lamports,
                max_retries=Config.MAX_RETRIES
            )
            
            if tx_hash:
                logger.info(f"Withdrawal transaction sent: {tx_hash}")
            else:
                logger.error("Failed to send withdrawal transaction")
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error executing withdrawal: {e}")
            raise
    
    def _send_withdraw_initiated_event(self, user_id: str, to_address: str, amount: str):
        """Send withdrawal initiated event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": user_id,
            "to_address": to_address,
            "amount": amount,
            "status": "initiated"
        }
        
        # Reuse kafka producer's send_event method
        self.kafka_producer.send_event("withdraw.initiated", event_data)
        logger.info(f"Sent withdraw.initiated event for user {user_id}")
    
    def _send_withdraw_pending_event(
        self,
        user_id: str,
        to_address: str,
        amount: str,
        tx_hash: str
    ):
        """Send withdrawal pending event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": user_id,
            "to_address": to_address,
            "amount": amount,
            "tx_hash": tx_hash,
            "status": "pending",
            "confirmations": 0
        }
        
        self.kafka_producer.send_event("withdraw.pending", event_data)
        logger.info(f"Sent withdraw.pending event: {tx_hash}")
    
    def _send_withdraw_confirming_event(
        self,
        user_id: str,
        to_address: str,
        amount: str,
        tx_hash: str
    ):
        """Send withdrawal confirming event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": user_id,
            "to_address": to_address,
            "amount": amount,
            "tx_hash": tx_hash,
            "status": "confirming"
        }
        
        self.kafka_producer.send_event("withdraw.confirming", event_data)
        logger.info(f"Sent withdraw.confirming event: {tx_hash}")
    
    def _send_withdraw_completed_event(
        self,
        user_id: str,
        to_address: str,
        amount: str,
        tx_hash: str,
        confirmations: int
    ):
        """Send withdrawal completed event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": user_id,
            "to_address": to_address,
            "amount": amount,
            "tx_hash": tx_hash,
            "status": "completed",
            "confirmations": confirmations
        }
        
        self.kafka_producer.send_event("withdraw.completed", event_data)
        logger.info(f"Sent withdraw.completed event: {tx_hash}")
    
    def _send_withdraw_failed_event(
        self,
        user_id: str,
        to_address: str,
        amount: str,
        error: str
    ):
        """Send withdrawal failed event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": user_id,
            "to_address": to_address,
            "amount": amount,
            "status": "failed",
            "error": error
        }
        
        self.kafka_producer.send_event("withdraw.failed", event_data)
        logger.error(f"Sent withdraw.failed event for user {user_id}: {error}")
