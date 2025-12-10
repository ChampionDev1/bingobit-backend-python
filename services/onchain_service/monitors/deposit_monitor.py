"""
Deposit transaction monitoring service - Redis Version
Monitors blockchain for deposits to user addresses and manages sweep operations

ARCHITECTURE:
- Reads deposit addresses from Redis (NOT database)
- Broadcasts ALL events to Kafka
- Go API Gateway handles ALL database writes
- NO database operations in this service
"""
import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from common import (
    Config, DepositStatus, setup_logger,
    lamports_to_sol, sol_to_lamports, calculate_fee_with_buffer,
    RedisClient
)
from common.kafka_producer import DepositEventProducer
from services.onchain_service.blockchain import SolanaClient

logger = setup_logger(__name__)

class DepositMonitor:
    """
    Monitor deposit addresses and process incoming transactions
    Handles edge cases like insufficient fees for sweep operations
    
    IMPORTANT:
    - Reads deposit addresses from Redis
    - Broadcasts events to Kafka
    - NO database operations
    """
    
    def __init__(self, chain: str = "solana"):
        self.chain = chain.lower()
        self.redis = RedisClient()
        self.kafka_producer = DepositEventProducer()
        self.solana_client = SolanaClient()
        
        self.hot_wallet_address = Config.SOLANA_HOT_WALLET_ADDRESS
        self.hot_wallet_keypair = None
        
        if Config.SOLANA_HOT_WALLET_PRIVATE_KEY:
            self.hot_wallet_keypair = self.solana_client.keypair_from_private_key(
                Config.SOLANA_HOT_WALLET_PRIVATE_KEY
            )
        
        self.running = False
        self.monitor_thread = None
        
        # Cache for deposit addresses
        self.deposit_addresses: Dict[str, Dict[str, Any]] = {}
        self.last_address_refresh = 0
        self.address_refresh_interval = 300  # 5 minutes
        
        # Track processed transactions (in-memory cache)
        self.processed_transactions: Dict[str, str] = {}  # tx_hash -> status
        
        logger.info(f"DepositMonitor initialized for chain: {self.chain}")
    
    def start(self):
        """Start monitoring service"""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Deposit monitor started")
    
    def stop(self):
        """Stop monitoring service"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        self.kafka_producer.close()
        self.redis.close()
        logger.info("Deposit monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Refresh deposit addresses periodically
                if time.time() - self.last_address_refresh > self.address_refresh_interval:
                    self._refresh_deposit_addresses()
                
                # Check for new deposits
                self._check_new_deposits()
                
                # Monitor pending transactions
                self._monitor_pending_transactions()
                
                # Sleep before next iteration
                time.sleep(Config.POLL_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                time.sleep(5)
    
    def _refresh_deposit_addresses(self):
        """Refresh deposit addresses from Redis"""
        try:
            addresses = self.redis.get_all_deposit_addresses(self.chain)
            
            self.deposit_addresses = {
                addr["address"]: addr for addr in addresses
            }
            
            self.last_address_refresh = time.time()
            logger.info(f"Refreshed {len(self.deposit_addresses)} deposit addresses from Redis")
            
        except Exception as e:
            logger.error(f"Failed to refresh deposit addresses from Redis: {e}")
    
    def _check_new_deposits(self):
        """Check all deposit addresses for new transactions"""
        for address, addr_info in self.deposit_addresses.items():
            try:
                self._check_address_deposits(address, addr_info)
                
            except Exception as e:
                logger.error(f"Error checking deposits for {address}: {e}")
    
    def _check_address_deposits(self, address: str, addr_info: Dict[str, Any]):
        """Check specific address for new deposits"""
        try:
            # Get current balance
            balance = self.solana_client.get_balance(address)
            
            if balance < Config.MIN_DEPOSIT_AMOUNT:
                return
            
            # Get recent transactions
            transactions = self.solana_client.get_transaction_history(
                address,
                limit=5
            )
            
            for tx in transactions:
                self._process_transaction(tx, address, addr_info, balance)
                
        except Exception as e:
            logger.error(f"Error checking address {address}: {e}")
    
    def _process_transaction(
        self,
        tx: Dict[str, Any],
        deposit_address: str,
        addr_info: Dict[str, Any],
        current_balance: int
    ):
        """
        Process individual transaction
        
        NO database writes - only Kafka events
        Go API Gateway handles database based on events
        """
        try:
            tx_hash = tx["signature"]
            amount = tx["amount"]
            
            # Skip if already processed
            if tx_hash in self.processed_transactions:
                return
            
            # Skip if amount too small
            if amount < Config.MIN_DEPOSIT_AMOUNT:
                logger.debug(f"Transaction {tx_hash} amount too small: {amount}")
                return
            
            # Mark as processed
            self.processed_transactions[tx_hash] = DepositStatus.DETECTED
            
            # Prepare event data (NO database write)
            event_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "chain": self.chain,
                "user_id": addr_info["user_id"],
                "tx_hash": tx_hash,
                "from_address": "",
                "to_address": deposit_address,
                "amount": str(lamports_to_sol(amount)),
                "status": DepositStatus.DETECTED,
                "deposit_address": deposit_address,
                "confirmations": 0,
                "block_number": tx.get("slot"),
                "metadata": {
                    "current_balance": str(lamports_to_sol(current_balance))
                }
            }
            
            # Send Kafka event (Go API Gateway will handle database)
            self.kafka_producer.send_deposit_detected(event_data)
            
            logger.info(
                f"New deposit detected: {tx_hash} | "
                f"Amount: {lamports_to_sol(amount)} SOL | "
                f"Address: {deposit_address}"
            )
            
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
    
    def _monitor_pending_transactions(self):
        """Monitor and update status of pending transactions"""
        for tx_hash, status in list(self.processed_transactions.items()):
            try:
                if status in [DepositStatus.COMPLETED, DepositStatus.FAILED]:
                    continue
                
                self._update_transaction_status(tx_hash, status)
                
            except Exception as e:
                logger.error(f"Error monitoring transaction {tx_hash}: {e}")
    
    def _update_transaction_status(self, tx_hash: str, current_status: str):
        """Update status of pending transaction"""
        try:
            # Get confirmations
            confirmations = self.solana_client.get_transaction_confirmations(tx_hash)
            
            new_status = current_status
            
            if current_status == DepositStatus.DETECTED:
                if confirmations > 0:
                    new_status = DepositStatus.PENDING
                    self._send_status_event(tx_hash, new_status, confirmations)
            
            elif current_status == DepositStatus.PENDING:
                if confirmations >= Config.MIN_CONFIRMATIONS:
                    new_status = DepositStatus.CONFIRMED
                    self._send_status_event(tx_hash, new_status, confirmations)
                    
                    # Initiate sweep operation
                    self._initiate_sweep(tx_hash)
                else:
                    new_status = DepositStatus.CONFIRMING
            
            elif current_status == DepositStatus.CONFIRMING:
                if confirmations >= Config.MIN_CONFIRMATIONS:
                    new_status = DepositStatus.CONFIRMED
                    self._send_status_event(tx_hash, new_status, confirmations)
                    
                    # Initiate sweep operation
                    self._initiate_sweep(tx_hash)
            
            # Update in-memory status
            if new_status != current_status:
                self.processed_transactions[tx_hash] = new_status
                
        except Exception as e:
            logger.error(f"Error updating transaction status: {e}")
    
    def _initiate_sweep(self, tx_hash: str):
        """
        Initiate sweep operation to move funds to hot wallet
        Handles edge case where deposit address has insufficient fee
        """
        try:
            # Find transaction info
            deposit_address = None
            addr_info = None
            
            for addr, info in self.deposit_addresses.items():
                # Check if this address has the transaction
                balance = self.solana_client.get_balance(addr)
                if balance > Config.MIN_DEPOSIT_AMOUNT:
                    deposit_address = addr
                    addr_info = info
                    break
            
            if not deposit_address or not addr_info:
                logger.error(f"Could not find deposit address for tx: {tx_hash}")
                return
            
            # Get current balance
            current_balance = self.solana_client.get_balance(deposit_address)
            estimated_fee = self.solana_client.estimate_fee()
            fee_with_buffer = calculate_fee_with_buffer(estimated_fee)
            
            logger.info(
                f"Initiating sweep: {deposit_address} | "
                f"Balance: {lamports_to_sol(current_balance)} SOL | "
                f"Fee: {lamports_to_sol(fee_with_buffer)} SOL"
            )
            
            # Edge case: insufficient balance for fee
            if current_balance <= fee_with_buffer:
                logger.warning(
                    f"Insufficient balance for fee. "
                    f"Sending fee from hot wallet first."
                )
                self._handle_insufficient_fee_case(
                    deposit_address,
                    addr_info,
                    current_balance,
                    fee_with_buffer,
                    tx_hash
                )
                return
            
            # Normal case: sweep funds to hot wallet
            self._execute_sweep(deposit_address, addr_info, current_balance, tx_hash)
            
        except Exception as e:
            logger.error(f"Error initiating sweep: {e}")
            self.processed_transactions[tx_hash] = DepositStatus.FAILED
            self._send_failed_event(tx_hash, str(e))
    
    def _handle_insufficient_fee_case(
        self,
        deposit_address: str,
        addr_info: Dict[str, Any],
        current_balance: int,
        required_fee: int,
        tx_hash: str
    ):
        """Handle edge case where deposit address cannot pay transaction fee"""
        try:
            # Step 1: Send fee from hot wallet to deposit address
            logger.info(f"Sending fee to deposit address: {deposit_address}")
            
            fee_tx_signature = self.solana_client.send_transaction_with_retry(
                self.hot_wallet_keypair,
                deposit_address,
                required_fee * 2
            )
            
            if not fee_tx_signature:
                logger.error("Failed to send fee to deposit address")
                self.processed_transactions[tx_hash] = DepositStatus.INSUFFICIENT_FEE
                return
            
            # Wait for fee transaction confirmation
            confirmed = self.solana_client.wait_for_confirmation(
                fee_tx_signature,
                timeout=Config.TRANSACTION_TIMEOUT
            )
            
            if not confirmed:
                logger.error("Fee transaction not confirmed in time")
                return
            
            logger.info(f"Fee sent successfully: {fee_tx_signature}")
            
            # Step 2: Wait a bit for balance to update
            time.sleep(3)
            
            # Step 3: Now sweep all funds including original deposit
            updated_balance = self.solana_client.get_balance(deposit_address)
            self._execute_sweep(deposit_address, addr_info, updated_balance, tx_hash)
            
        except Exception as e:
            logger.error(f"Error handling insufficient fee case: {e}")
            self.processed_transactions[tx_hash] = DepositStatus.FAILED
            self._send_failed_event(tx_hash, str(e))
    
    def _execute_sweep(
        self,
        deposit_address: str,
        addr_info: Dict[str, Any],
        balance: int,
        tx_hash: str
    ):
        """Execute sweep transaction from deposit address to hot wallet"""
        try:
            # Create keypair from deposit address private key
            deposit_keypair = self.solana_client.keypair_from_private_key(
                addr_info["private_key"]
            )
            
            # Calculate amount to sweep (balance minus fee)
            estimated_fee = self.solana_client.estimate_fee()
            sweep_amount = balance - estimated_fee
            
            if sweep_amount <= 0:
                logger.error(f"Invalid sweep amount: {sweep_amount}")
                return
            
            # Update status to sweeping
            self.processed_transactions[tx_hash] = DepositStatus.SWEEPING
            self._send_sweeping_event(tx_hash, sweep_amount)
            
            # Send sweep transaction
            logger.info(
                f"Executing sweep: {lamports_to_sol(sweep_amount)} SOL "
                f"from {deposit_address} to hot wallet"
            )
            
            sweep_signature = self.solana_client.send_transaction_with_retry(
                deposit_keypair,
                self.hot_wallet_address,
                sweep_amount
            )
            
            if not sweep_signature:
                logger.error("Failed to execute sweep transaction")
                self.processed_transactions[tx_hash] = DepositStatus.FAILED
                self._send_failed_event(tx_hash, "Sweep transaction failed")
                return
            
            # Wait for confirmation
            confirmed = self.solana_client.wait_for_confirmation(
                sweep_signature,
                timeout=Config.TRANSACTION_TIMEOUT
            )
            
            if confirmed:
                # Update to completed
                self.processed_transactions[tx_hash] = DepositStatus.COMPLETED
                self._send_completed_event(tx_hash, sweep_signature, sweep_amount)
                
                logger.info(
                    f"Sweep completed: {sweep_signature} | "
                    f"Amount: {lamports_to_sol(sweep_amount)} SOL"
                )
            else:
                logger.warning(f"Sweep transaction not confirmed: {sweep_signature}")
                
        except Exception as e:
            logger.error(f"Error executing sweep: {e}")
            self.processed_transactions[tx_hash] = DepositStatus.FAILED
            self._send_failed_event(tx_hash, str(e))
    
    def _send_status_event(self, tx_hash: str, status: str, confirmations: int):
        """Send status update event to Kafka"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "tx_hash": tx_hash,
            "status": status,
            "confirmations": confirmations
        }
        
        if status == DepositStatus.PENDING:
            self.kafka_producer.send_deposit_pending(event_data)
        elif status == DepositStatus.CONFIRMING:
            self.kafka_producer.send_deposit_confirming(event_data)
        elif status == DepositStatus.CONFIRMED:
            self.kafka_producer.send_deposit_confirmed(event_data)
    
    def _send_sweeping_event(self, tx_hash: str, sweep_amount: int):
        """Send sweeping event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "tx_hash": tx_hash,
            "status": DepositStatus.SWEEPING,
            "amount": str(lamports_to_sol(sweep_amount))
        }
        self.kafka_producer.send_deposit_sweeping(event_data)
    
    def _send_completed_event(self, tx_hash: str, sweep_tx_hash: str, sweep_amount: int):
        """Send completed event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "tx_hash": tx_hash,
            "status": DepositStatus.COMPLETED,
            "amount": str(lamports_to_sol(sweep_amount)),
            "metadata": {
                "sweep_tx_hash": sweep_tx_hash
            }
        }
        self.kafka_producer.send_deposit_completed(event_data)
    
    def _send_failed_event(self, tx_hash: str, error_message: str):
        """Send failed event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "tx_hash": tx_hash,
            "status": DepositStatus.FAILED,
            "metadata": {
                "error": error_message
            }
        }
        self.kafka_producer.send_deposit_failed(event_data)
