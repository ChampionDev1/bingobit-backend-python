import grpc
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from proto import onchain_pb2, onchain_pb2_grpc

def test_deposit():
    # Connect to OnChain Service
    channel = grpc.insecure_channel('localhost:50051')
    stub = onchain_pb2_grpc.onChainSerivceStub(channel)
    
    # Deposit Request
    request = onchain_pb2.DepositRequest(
        chain="solana",
        amount="100"
    )
    
    print("Sending deposit request...")
    response = stub.Deposit(request)
    
    print(f"Success: {response.success}")
    print(f"Message: {response.message}")
    print(f"Hot Wallet Balance: {response.hot_wallet_balance}")

if __name__ == '__main__':
    test_deposit()
