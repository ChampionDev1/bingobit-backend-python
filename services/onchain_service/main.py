"""
OnChain Service - Main gRPC service for blockchain operations
Handles withdrawals, buy/sell operations, and manages deposit monitoring

IMPORTANT:
- Deposit is AUTOMATIC (monitored by DepositMonitor)
- Deposit is NOT an RPC call
- Only Withdraw, Buy, Sell are RPC operations
"""
import grpc
from concurrent import futures
import sys
import os
import signal

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from proto import onchain_pb2, onchain_pb2_grpc
from monitors.deposit_monitor import DepositMonitor
from monitors.withdraw_monitor import WithdrawMonitor
from processors.withdraw import WithdrawProcessor
from common import setup_logger

logger = setup_logger(__name__)

class OnChainService(onchain_pb2_grpc.onChainSerivceServicer):
    """
    OnChain gRPC service implementation
    
    RPC Services:
    - Withdraw: User-initiated withdrawal
    - Buy: User buys crypto
    - Sell: User sells crypto
    
    Background Monitors:
    - DepositMonitor: Automatic deposit detection and processing
    - WithdrawMonitor: Withdrawal confirmation monitoring
    """
    
    def __init__(self):
        self.deposit_monitor = None
        self.withdraw_monitor = None
        self.withdraw_processor = WithdrawProcessor()
        logger.info("OnChainService initialized")
    
    def Withdraw(self, request, context):
        """
        Handle withdrawal RPC call
        User requests to withdraw funds from hot wallet to external address
        
        Flow:
        1. Validate request
        2. Execute transaction
        3. Add to withdraw monitor
        4. Return tx_hash
        """
        logger.info(
            f"Withdraw request: chain={request.chain}, "
            f"user={request.user_id}, to={request.to_address}, "
            f"amount={request.amount}"
        )
        
        try:
            # Process withdrawal
            result = self.withdraw_processor.process_withdrawal(
                user_id=request.user_id,
                to_address=request.to_address,
                amount=request.amount
            )
            
            # If successful, add to monitor for confirmation tracking
            if result["success"] and result["tx_hash"]:
                if self.withdraw_monitor:
                    self.withdraw_monitor.add_withdrawal(
                        tx_hash=result["tx_hash"],
                        user_id=request.user_id,
                        to_address=request.to_address,
                        amount=request.amount
                    )
            
            return onchain_pb2.WithdrawResponse(
                success=result["success"],
                message=result["message"],
                tx_hash=result["tx_hash"]
            )
            
        except Exception as e:
            logger.error(f"Withdraw error: {e}", exc_info=True)
            return onchain_pb2.WithdrawResponse(
                success=False,
                message=f"Withdrawal failed: {str(e)}",
                tx_hash=""
            )
    
    def Buy(self, request, context):
        """Handle buy RPC call"""
        logger.info(
            f"Buy request: chain={request.chain}, "
            f"user={request.user_id}, token={request.token}, "
            f"amount={request.amount}"
        )
        
        logger.warning("Buy not implemented yet")
        return onchain_pb2.BuyResponse(
            success=False,
            message="Buy not implemented yet",
            tx_hash=""
        )
    
    def Sell(self, request, context):
        """Handle sell RPC call"""
        logger.info(
            f"Sell request: chain={request.chain}, "
            f"user={request.user_id}, token={request.token}, "
            f"amount={request.amount}"
        )
        
        logger.warning("Sell not implemented yet")
        return onchain_pb2.SellResponse(
            success=False,
            message="Sell not implemented yet",
            tx_hash=""
        )
    
    def start_monitors(self):
        """Start all monitoring services"""
        # Start deposit monitor
        self.deposit_monitor = DepositMonitor(chain="solana")
        self.deposit_monitor.start()
        logger.info("Deposit monitor started")
        
        # Start withdraw monitor
        self.withdraw_monitor = WithdrawMonitor(chain="solana")
        self.withdraw_monitor.start()
        logger.info("Withdraw monitor started")
    
    def stop_monitors(self):
        """Stop all monitoring services"""
        if self.deposit_monitor:
            self.deposit_monitor.stop()
            logger.info("Deposit monitor stopped")
        
        if self.withdraw_monitor:
            self.withdraw_monitor.stop()
            logger.info("Withdraw monitor stopped")

def serve():
    """Start gRPC server and all monitors"""
    service = OnChainService()
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    onchain_pb2_grpc.add_onChainSerivceServicer_to_server(service, server)
    server.add_insecure_port('localhost:50051')
    
    # Start all monitors
    service.start_monitors()
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Shutting down gracefully...")
        service.stop_monitors()
        server.stop(grace=5)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("OnChain Service running on port 50051")
    logger.info("Services: Withdraw, Buy, Sell")
    logger.info("Monitors: Deposit, Withdraw")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()