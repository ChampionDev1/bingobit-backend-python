"""
Solana blockchain client for transaction monitoring and execution
"""
import time
from typing import Optional, List, Dict, Any
from decimal import Decimal

try:
    from solana.rpc.api import Client
    from solana.rpc.commitment import Confirmed, Finalized
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.signature import Signature
    from solders.transaction import Transaction as SoldersTransaction
    from solders.system_program import transfer, TransferParams
    from solders.message import Message
    from solders.hash import Hash as Blockhash
    import base58
    SOLANA_AVAILABLE = True
except ImportError as e:
    SOLANA_AVAILABLE = False
    print(f"Warning: Solana libraries not available: {e}")
    print("Install with: pip install solana solders base58")

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from common import Config, setup_logger, lamports_to_sol, sol_to_lamports

logger = setup_logger(__name__)

class SolanaClient:
    """Solana blockchain client wrapper"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        if not SOLANA_AVAILABLE:
            raise ImportError(
                "Solana libraries not installed. "
                "Install with: pip install solana solders base58"
            )
        
        self.rpc_url = rpc_url or Config.SOLANA_RPC_URL
        self.client = Client(self.rpc_url)
        self.min_confirmations = Config.MIN_CONFIRMATIONS
        logger.info(f"Solana client initialized: {self.rpc_url}")
    
    def get_balance(self, address: str) -> int:
        """
        Get balance of address in lamports
        
        Args:
            address: Solana address
        
        Returns:
            Balance in lamports
        """
        try:
            pubkey = Pubkey.from_string(address)
            response = self.client.get_balance(pubkey, commitment=Confirmed)
            
            if response.value is not None:
                return response.value
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            return 0
    
    def get_transaction_history(
        self,
        address: str,
        limit: int = 10,
        before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for address
        
        Args:
            address: Solana address
            limit: Maximum number of transactions
            before: Signature to fetch transactions before
        
        Returns:
            List of transaction records
        """
        try:
            pubkey = Pubkey.from_string(address)
            
            response = self.client.get_signatures_for_address(
                pubkey,
                limit=limit,
                before=Signature.from_string(before) if before else None,
                commitment=Confirmed
            )
            
            if not response.value:
                return []
            
            transactions = []
            for sig_info in response.value:
                tx_detail = self._get_transaction_detail(str(sig_info.signature))
                if tx_detail:
                    transactions.append(tx_detail)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transaction history for {address}: {e}")
            return []
    
    def _get_transaction_detail(self, signature: str) -> Optional[Dict[str, Any]]:
        """Get detailed transaction information"""
        try:
            response = self.client.get_transaction(
                Signature.from_string(signature),
                commitment=Confirmed,
                max_supported_transaction_version=0
            )
            
            if not response.value:
                return None
            
            tx = response.value
            meta = tx.transaction.meta
            
            if not meta:
                return None
            
            # Extract transfer information
            pre_balances = meta.pre_balances
            post_balances = meta.post_balances
            
            # Calculate amount transferred (simplified)
            amount = 0
            if len(pre_balances) >= 2 and len(post_balances) >= 2:
                amount = abs(post_balances[1] - pre_balances[1])
            
            return {
                "signature": signature,
                "slot": tx.slot,
                "block_time": tx.block_time,
                "amount": amount,
                "fee": meta.fee,
                "status": "success" if meta.err is None else "failed",
                "confirmations": 0  # Will be calculated separately
            }
            
        except Exception as e:
            logger.error(f"Failed to get transaction detail for {signature}: {e}")
            return None
    
    def get_transaction_confirmations(self, signature: str) -> int:
        """
        Get number of confirmations for transaction
        
        Args:
            signature: Transaction signature
        
        Returns:
            Number of confirmations
        """
        try:
            response = self.client.get_transaction(
                Signature.from_string(signature),
                commitment=Confirmed
            )
            
            if not response.value:
                return 0
            
            tx_slot = response.value.slot
            current_slot_response = self.client.get_slot(commitment=Confirmed)
            current_slot = current_slot_response.value
            
            if current_slot and tx_slot:
                return max(0, current_slot - tx_slot)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get confirmations for {signature}: {e}")
            return 0
    
    def send_transaction_with_retry(
        self,
        from_keypair: Keypair,
        to_address: str,
        amount_lamports: int,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Send SOL transaction with retry logic
        
        Args:
            from_keypair: Sender's keypair
            to_address: Recipient address
            amount_lamports: Amount in lamports
            max_retries: Maximum retry attempts
        
        Returns:
            Transaction signature if successful, None otherwise
        """
        for attempt in range(max_retries):
            try:
                signature = self._send_transaction(
                    from_keypair,
                    to_address,
                    amount_lamports
                )
                
                if signature:
                    logger.info(
                        f"Transaction sent successfully: {signature} "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    return signature
                
            except Exception as e:
                logger.warning(
                    f"Transaction attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Failed to send transaction after {max_retries} attempts")
        return None
    
    def _send_transaction(
        self,
        from_keypair: Keypair,
        to_address: str,
        amount_lamports: int
    ) -> Optional[str]:
        """Internal method to send transaction"""
        try:
            to_pubkey = Pubkey.from_string(to_address)
            
            # Create transfer instruction
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=from_keypair.pubkey(),
                    to_pubkey=to_pubkey,
                    lamports=amount_lamports
                )
            )
            
            # Get recent blockhash
            recent_blockhash_resp = self.client.get_latest_blockhash(commitment=Confirmed)
            recent_blockhash = recent_blockhash_resp.value.blockhash
            
            # Create message and transaction
            message = Message.new_with_blockhash(
                [transfer_ix],
                from_keypair.pubkey(),
                recent_blockhash
            )
            transaction = SoldersTransaction([from_keypair], message, recent_blockhash)
            
            # Send transaction
            from solana.rpc.types import TxOpts
            response = self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            )
            
            if response.value:
                return str(response.value)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to send transaction: {e}")
            raise
    
    def wait_for_confirmation(
        self,
        signature: str,
        timeout: int = 60,
        required_confirmations: Optional[int] = None
    ) -> bool:
        """
        Wait for transaction confirmation
        
        Args:
            signature: Transaction signature
            timeout: Maximum wait time in seconds
            required_confirmations: Required number of confirmations
        
        Returns:
            True if confirmed, False otherwise
        """
        required = required_confirmations or self.min_confirmations
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                confirmations = self.get_transaction_confirmations(signature)
                
                if confirmations >= required:
                    logger.info(
                        f"Transaction {signature} confirmed "
                        f"with {confirmations} confirmations"
                    )
                    return True
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error checking confirmation: {e}")
                time.sleep(2)
        
        logger.warning(f"Transaction {signature} confirmation timeout")
        return False
    
    def estimate_fee(self) -> int:
        """
        Estimate transaction fee
        
        Returns:
            Estimated fee in lamports
        """
        # Solana has fixed fee structure, return base + priority fee
        return Config.SOLANA_BASE_FEE + Config.SOLANA_PRIORITY_FEE
    
    def keypair_from_private_key(self, private_key: str) -> Keypair:
        """
        Create keypair from private key string
        
        Args:
            private_key: Base58 encoded private key
        
        Returns:
            Keypair object
        """
        try:
            secret_bytes = base58.b58decode(private_key)
            return Keypair.from_bytes(secret_bytes)
        except Exception as e:
            logger.error(f"Failed to create keypair from private key: {e}")
            raise
