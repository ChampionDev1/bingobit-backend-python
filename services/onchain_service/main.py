import grpc
from concurrent import futures
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from proto import onchain_pb2, onchain_pb2_grpc
from processors.deposit import DepositProcessor

class OnChainService(onchain_pb2_grpc.onChainSerivceServicer):
    def __init__(self):
        self.deposit_processor = DepositProcessor()

    def Deposit(self, request, context):
        print(f"[OnChain] Deposit Request Receive: chain={request.chain}, amount={request.amount}")

        result = self.deposit_processor.process(
            chain = request.chain,
            amount = request.amount
        )

        return onchain_pb2.DepositResponse(
            success = result['success'],
            message = result['message'],
            hot_wallet_balance = result['new_balance']
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers = 10))
    onchain_pb2_grpc.add_onChainSerivceServicer_to_server(
        OnChainService(), server
    )
    server.add_insecure_port('[::]:50051')
    print("OnChain Service running on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()