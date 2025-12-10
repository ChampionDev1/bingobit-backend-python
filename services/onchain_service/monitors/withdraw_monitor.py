"""
Withdraw Monitor - Monitors withdrawal transaction confirmations
Tracks pending withdrawals and broadcasts status updates
"""
import time
import threading
from typing import Dict, Optional
from datetime import datetime

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from common import Config, setup_logger, lamports_to_sol
from common.kafka_producer import DepositEventProducer
from services.onchain_service.blockchain import SolanaClient

logger = setup_logger(__name__)

class WithdrawMonitor:
    """
    Monitor withdrawal transactions for confirmation
    
    Tracks pending withdrawals and broadcasts status updates via Kafka
    """
    
    def __init__(self, chain: str = "solana"):
        self.chain = chain.lower()
        self.solana_client = SolanaClient()
        self.kafka_producer = DepositEventProducer()
        
        self.running = False
        self.monitor_thread = None
        
        # Track pending withdrawals: tx_hash -> withdrawal_info
        self.pending_withdrawals: Dict[str, Dict] = {}
        
        logger.info(f"WithdrawMonitor initialized for chain: {self.chain}")
    
    def start(self):
        """Start monitoring service"""
        if self.running:
            logger.warning("Withdraw monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Withdraw monitor started")
    
    def stop(self):
        """Stop monitoring service"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("Withdraw monitor stopped")
    
    def add_withdrawal(
        self,
        tx_hash: str,
        user_id: str,
        to_address: str,
        amount: str
    ):
        """
        Add withdrawal to monitoring queue
        
        Args:
            tx_hash: Transaction hash
            user_id: User identifier
            to_address: Destination address
            amount: Withdrawal amount
        """
        self.pending_withdrawals[tx_hash] = {
            "user_id": user_id,
            "to_address": to_address,
            "amount": amount,
            "status": "pending",
            "confirmations": 0,
            "added_at": time.time()
        }
        logger.info(f"Added withdrawal to monitor: {tx_hash}")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_pending_withdrawals()
                time.sleep(Config.POLL_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"Error in withdraw monitor loop: {e}", exc_info=True)
                time.sleep(5)
    
    def _check_pending_withdrawals(self):
        """Check all pending withdrawals for confirmation updates"""
        for tx_hash in list(self.pending_withdrawals.keys()):
            try:
                withdrawal = self.pending_withdrawals[tx_hash]
                
                # Skip if already completed or failed
                if withdrawal["status"] in ["completed", "failed"]:
                    continue
                
                # Check confirmations
                confirmations = self.solana_client.get_transaction_confirmations(tx_hash)
                
                # Update status based on confirmations
                self._update_withdrawal_status(tx_hash, withdrawal, confirmations)
                
                # Remove if completed or too old (timeout)
                if withdrawal["status"] == "completed":
                    del self.pending_withdrawals[tx_hash]
                    logger.info(f"Removed completed withdrawal: {tx_hash}")
                
                elif time.time() - withdrawal["added_at"] > 300:  # 5 minutes timeout
                    logger.warning(f"Withdrawal timeout: {tx_hash}")
                    self._send_timeout_event(tx_hash, withdrawal)
                    del self.pending_withdrawals[tx_hash]
                
            except Exception as e:
                logger.error(f"Error checking withdrawal {tx_hash}: {e}")
    
    def _update_withdrawal_status(
        self,
        tx_hash: str,
        withdrawal: Dict,
        confirmations: int
    ):
        """Update withdrawal status based on confirmations"""
        old_confirmations = withdrawal["confirmations"]
        withdrawal["confirmations"] = confirmations
        
        # Status progression
        if withdrawal["status"] == "pending" and confirmations > 0:
            withdrawal["status"] = "confirming"
            self._send_confirming_event(tx_hash, withdrawal, confirmations)
        
        elif withdrawal["status"] == "confirming":
            # Send update if confirmations increased significantly
            if confirmations >= Config.MIN_CONFIRMATIONS:
                withdrawal["status"] = "completed"
                self._send_completed_event(tx_hash, withdrawal, confirmations)
            
            elif confirmations > old_confirmations and confirmations % 5 == 0:
                # Send progress update every 5 confirmations
                self._send_confirming_event(tx_hash, withdrawal, confirmations)
    
    def _send_confirming_event(
        self,
        tx_hash: str,
        withdrawal: Dict,
        confirmations: int
    ):
        """Send withdrawal confirming event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": withdrawal["user_id"],
            "to_address": withdrawal["to_address"],
            "amount": withdrawal["amount"],
            "tx_hash": tx_hash,
            "status": "confirming",
            "confirmations": confirmations
        }
        
        self.kafka_producer.send_event("withdraw.confirming", event_data)
        logger.info(f"Withdrawal confirming: {tx_hash} ({confirmations} confirmations)")
    
    def _send_completed_event(
        self,
        tx_hash: str,
        withdrawal: Dict,
        confirmations: int
    ):
        """Send withdrawal completed event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": withdrawal["user_id"],
            "to_address": withdrawal["to_address"],
            "amount": withdrawal["amount"],
            "tx_hash": tx_hash,
            "status": "completed",
            "confirmations": confirmations
        }
        
        self.kafka_producer.send_event("withdraw.completed", event_data)
        logger.info(f"Withdrawal completed: {tx_hash} ({confirmations} confirmations)")
    
    def _send_timeout_event(self, tx_hash: str, withdrawal: Dict):
        """Send withdrawal timeout event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "chain": self.chain,
            "user_id": withdrawal["user_id"],
            "to_address": withdrawal["to_address"],
            "amount": withdrawal["amount"],
            "tx_hash": tx_hash,
            "status": "timeout",
            "error": "Transaction confirmation timeout"
        }
        
        self.kafka_producer.send_event("withdraw.timeout", event_data)
        logger.warning(f"Withdrawal timeout: {tx_hash}")
