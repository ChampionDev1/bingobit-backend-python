"""
Check Solana wallet balance
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from services.onchain_service.blockchain import SolanaClient
from common.config import Config

def check_balance(address):
    """Check balance for given address"""
    try:
        client = SolanaClient()
        balance = client.get_balance(address)
        sol_balance = balance / 1e9
        
        print(f"Address: {address}")
        print(f"Balance: {sol_balance} SOL ({balance} lamports)")
        print(f"Explorer: https://explorer.solana.com/address/{address}?cluster=devnet")
        
        return sol_balance
    except Exception as e:
        print(f"Error checking balance: {e}")
        return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_balance.py <address>")
        print("\nOr check hot wallet balance:")
        print("python scripts/check_balance.py hot")
        return
    
    address = sys.argv[1]
    
    if address.lower() == 'hot':
        # Check hot wallet balance
        hot_wallet_address = Config.SOLANA_HOT_WALLET_ADDRESS
        if not hot_wallet_address:
            print("❌ Hot wallet address not configured in .env")
            return
        
        print("🔥 HOT WALLET BALANCE:")
        check_balance(hot_wallet_address)
    else:
        # Check specific address balance
        print("💰 WALLET BALANCE:")
        check_balance(address)

if __name__ == '__main__':
    main()