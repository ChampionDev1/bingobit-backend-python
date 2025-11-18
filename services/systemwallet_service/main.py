import grpc
from concurrent import futures
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from proto import systemwallet_pb2, systemwallet_pb2_grpc
from wallet_manager import WalletManager

class SystemWalletService(systemwallet_pb2_grpc.SystemWalletServiceServicer):
    def __init__(self):
        self.wallet_manager = WalletManager()

    def AddBalance(self, request, context):
        try:
            new_balance = self.wallet_manager.add_balance(
                chain = request.chain,
                wallet_type = request.wallet_type,
                amount = request.amount
            )

            return systemwallet_pb2.AddBalanceResponse(
                success = True,
                message = "Balance added successfully",
                new_balance = new_balance
            )
        except Exception as e:
            return systemwallet_pb2.AddBalanceResponse(
                success = False,
                message = str(e),
                new_balance = "0"
            )

    def GetBalance():
        pass
    
    def TransferBetweenWallets():
        pass

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers = 10))
    systemwallet_pb2_grpc.add_SystemWalletServiceServicer_to_server(
        SystemWalletService(), server
    )
    server.add_insecure_port('[::]:50052')
    print("SystemWallet Service running on port 50052")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()