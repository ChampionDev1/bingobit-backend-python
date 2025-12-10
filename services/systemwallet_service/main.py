"""
SystemWallet Service - Manages system wallet balances
Handles hot/cold/swap wallet operations with database persistence
"""
import grpc
from concurrent import futures
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from proto import systemwallet_pb2, systemwallet_pb2_grpc
from wallet_manager import WalletManager
from common.logger import setup_logger

logger = setup_logger(__name__)

class SystemWalletService(systemwallet_pb2_grpc.SystemWalletServiceServicer):
    """SystemWallet gRPC service implementation"""
    
    def __init__(self):
        self.wallet_manager = WalletManager()
        logger.info("SystemWalletService initialized")

    def AddBalance(self, request, context):
        """
        DEPRECATED: This method is not used in the new architecture
        
        Python service does NOT update database
        - Go API Gateway handles all database operations
        - This service only queries blockchain for actual balances
        
        Returns current blockchain balance instead
        """
        logger.warning(
            f"AddBalance called (deprecated): chain={request.chain}, "
            f"wallet_type={request.wallet_type}, amount={request.amount}"
        )
        logger.info("Returning actual blockchain balance instead")
        
        try:
            wallet_info = self.wallet_manager.get_wallet_info(
                chain=request.chain,
                wallet_type=request.wallet_type
            )
            
            return systemwallet_pb2.AddBalanceResponse(
                success=True,
                message="Returning blockchain balance (DB managed by Go API Gateway)",
                new_balance=wallet_info["balance"]
            )
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return systemwallet_pb2.AddBalanceResponse(
                success=False,
                message=str(e),
                new_balance="0"
            )

    def GetBalance(self, request, context):
        """
        Get actual wallet balance from blockchain
        
        This queries the blockchain directly for the real balance
        NOT from database (Go API Gateway manages database)
        """
        logger.info(
            f"GetBalance request: chain={request.chain}, "
            f"wallet_type={request.wallet_type}"
        )
        
        try:
            wallet_info = self.wallet_manager.get_wallet_info(
                chain=request.chain,
                wallet_type=request.wallet_type
            )
            
            logger.info(
                f"Blockchain balance: {wallet_info['balance']} "
                f"for {wallet_info['address']}"
            )
            
            return systemwallet_pb2.GetBalanceResponse(
                balance=wallet_info["balance"]
            )
        except Exception as e:
            logger.error(f"GetBalance failed: {e}")
            return systemwallet_pb2.GetBalanceResponse(
                balance="0"
            )
    
    def TransferBetweenWallets(self, request, context):
        """
        DEPRECATED: Blockchain transfers should be handled by OnChain service
        
        This service only queries balances
        Actual blockchain transactions are handled by OnChain service
        Database updates are handled by Go API Gateway
        """
        logger.warning(
            f"TransferBetweenWallets called (deprecated): chain={request.chain}, "
            f"from={request.from_wallet_type} -> to={request.to_wallet_type}, "
            f"amount={request.amount}"
        )
        
        return systemwallet_pb2.TransferResponse(
            success=False,
            message="Use OnChain service for blockchain transfers. "
                    "SystemWallet service only queries balances."
        )

def serve():
    """Start gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    systemwallet_pb2_grpc.add_SystemWalletServiceServicer_to_server(
        SystemWalletService(), server
    )
    server.add_insecure_port('[::]:50052')
    
    logger.info("SystemWallet Service running on port 50052")
    print("SystemWallet Service running on port 50052")
    print("Press Ctrl+C to stop")
    
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()