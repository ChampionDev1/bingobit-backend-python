"""
Test withdrawal flow on Solana devnet
Tests the complete withdrawal process
"""
import sys
import os
import grpc
import argparse

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from proto import onchain_pb2, onchain_pb2_grpc
from common import Config, setup_logger
from services.onchain_service.blockchain import SolanaClient
from dotenv import load_dotenv

load_dotenv()

logger = setup_logger(__name__)

def test_withdrawal(user_id: str, to_address: str, amount: float):
    """
    Test withdrawal flow
    
    Args:
        user_id: User identifier
        to_address: Destination address
        amount: Amount to withdraw in SOL
    """
    print("\n" + "="*80)
    print("SOLANA WITHDRAWAL FLOW TEST")
    print("="*80 + "\n")
    
    # Initialize clients
    client = SolanaClient()
    
    # Check hot wallet balance
    hot_wallet_address = Config.SOLANA_HOT_WALLET_ADDRESS
    if not hot_wallet_address:
        print("❌ Hot wallet not configured in .env")
        return
    
    print(f"Hot Wallet: {hot_wallet_address}")
    hot_balance = client.get_balance(hot_wallet_address)
    print(f"Hot Wallet Balance: {hot_balance / 1e9} SOL\n")
    
    # Check destination address balance (before)
    print(f"Destination Address: {to_address}")
    dest_balance_before = client.get_balance(to_address)
    print(f"Destination Balance (before): {dest_balance_before / 1e9} SOL\n")
    
    # Connect to OnChain Service
    print("Connecting to OnChain Service...")
    channel = grpc.insecure_channel('localhost:50051')
    stub = onchain_pb2_grpc.onChainSerivceStub(channel)
    
    # Send withdrawal request
    print(f"\nSending withdrawal request:")
    print(f"  User ID: {user_id}")
    print(f"  To Address: {to_address}")
    print(f"  Amount: {amount} SOL\n")
    
    try:
        response = stub.Withdraw(
            onchain_pb2.WithdrawRequest(
                chain="solana",
                user_id=user_id,
                to_address=to_address,
                amount=str(amount)
            )
        )
        
        print("="*80)
        print("WITHDRAWAL RESPONSE")
        print("="*80)
        print(f"Success: {response.success}")
        print(f"Message: {response.message}")
        print(f"TX Hash: {response.tx_hash}")
        print("="*80 + "\n")
        
        if response.success and response.tx_hash:
            print(f"✓ Withdrawal transaction sent!")
            print(f"\nExplorer: https://explorer.solana.com/tx/{response.tx_hash}?cluster=devnet")
            
            # Wait a bit for transaction to process
            print("\nWaiting for transaction to process...")
            import time
            time.sleep(10)
            
            # Check destination balance (after)
            dest_balance_after = client.get_balance(to_address)
            print(f"\nDestination Balance (after): {dest_balance_after / 1e9} SOL")
            print(f"Change: +{(dest_balance_after - dest_balance_before) / 1e9} SOL")
            
            # Check hot wallet balance (after)
            hot_balance_after = client.get_balance(hot_wallet_address)
            print(f"\nHot Wallet Balance (after): {hot_balance_after / 1e9} SOL")
            print(f"Change: {(hot_balance_after - hot_balance) / 1e9} SOL")
            
        else:
            print(f"✗ Withdrawal failed: {response.message}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        channel.close()

def main():
    parser = argparse.ArgumentParser(description='Test Solana withdrawal flow')
    parser.add_argument(
        '--user-id',
        type=str,
        default='test_user_1',
        help='User ID (default: test_user_1)'
    )
    parser.add_argument(
        '--to',
        type=str,
        required=True,
        help='Destination address (required)'
    )
    parser.add_argument(
        '--amount',
        type=float,
        default=0.01,
        help='Amount to withdraw in SOL (default: 0.01)'
    )
    
    args = parser.parse_args()
    
    test_withdrawal(args.user_id, args.to, args.amount)

if __name__ == '__main__':
    main()
