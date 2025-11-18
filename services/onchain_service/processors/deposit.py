import grpc
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from proto import systemwallet_pb2, systemwallet_pb2_grpc

class DepositProcessor:
    def __init__(self, systemwallet_service_url = "localhost:50052"):
        # Connect with SystemWallet Service
        self.channel = grpc.insecure_channel(systemwallet_service_url)
        self.systemwallet_stub = systemwallet_pb2_grpc.SystemWalletServiceStub(self.channel)
    
    def process(self, chain: str, amount: str) -> dict:
        # main.py's Deposit() function calls this function
        print(f"[DepositProcessor] Processing Start: chain={chain}, amount={amount}")

        try:
            # Send hot wallet's amount increase request to SystemWallet Service
            print(f"[DepositProcessor] SystemWallet Service Calling...")

            response = self.systemwallet_stub.AddBalance(
                systemwallet_pb2.AddBalanceRequest(
                    chain = chain,
                    wallet_type = "hot",
                    amount = amount
                )
            )

            print(f"[DepositProcessor] SystemWallet Response: success = {response.success}, message = {response.message}, balance = {response.new_balance}")

            if not response.success:
                return {
                    "success": False,
                    "message": response.message,
                    "new_balance": "0"
                }

            return {
                "success": True,
                "message": response.message,
                "new_balance": response.new_balance
            }

        except Exception as e:
            print(f"[DepositProcess] Error Occured: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to process deposit: {str(e)}",
                "new_balance": "0"
            }