"""
Test deposit flow on Solana devnet
Simulates a user deposit and monitors the entire flow
"""
import sys
import os
import time
import argparse
from decimal import Decimal

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from common import Config, setup_logger, sol_to_lamports, lamports_to_sol
from common.database import DatabaseManager
from services.onchain_service.blockchain import SolanaClient

logger = setup_logger(__name__)

def get_test_deposit_address(db: DatabaseManager):
    """Get first test deposit address"""
    addresses = db.get_all_deposit_addresses('solana')
    if not addresses:
        logger.error("No deposit addresses found. Run setup_test_env.py first")
        return None
    return addresses[0]

def send_test_deposit(client: SolanaClient, to_address: str, amount_sol: float):
    """Send test deposit from hot wallet to deposit address"""
    logger.info(f"Sending {amount_sol} SOL to {to_address}")
    
    if not Config.SOLANA_HOT_WALLET_PRIVATE_KEY:
        logger.error("Hot wallet private key not configured")
        return None
    
    try:
        hot_wallet_keypair = client.keypair_from_private_key(
            Config.SOLANA_HOT_WALLET_PRIVATE_KEY
        )
        
        amount_lamports = sol_to_lamports(amount_sol)
        
        signature = client.send_transaction_with_retry(
            hot_wallet_keypair,
            to_address,
            amount_lamports
        )
        
        if signature:
            logger.info(f"Test deposit sent: {signature}")
            return signature
        else:
            logger.error("Failed to send test deposit")
            return None
            
    except Exception as e:
        logger.error(f"Error sending test deposit: {e}")
        return None

def monitor_transaction(client: SolanaClient, signature: str, timeout: int = 120):
    """Monitor transaction until completion"""
    logger.info(f"Monitoring transaction: {signature}")
    
    start_time = time.time()
    last_confirmations = 0
    
    while time.time() - start_time < timeout:
        try:
            confirmations = client.get_transaction_confirmations(signature)
            
            if confirmations != last_confirmations:
                logger.info(f"Confirmations: {confirmations}")
                last_confirmations = confirmations
            
            if confirmations >= Config.MIN_CONFIRMATIONS:
                logger.info(f"Transaction confirmed with {confirmations} confirmations")
                return True
            
            time.sleep(3)
            
        except Exception as e:
            logger.error(f"Error monitoring transaction: {e}")
            time.sleep(3)
    
    logger.warning("Transaction monitoring timeout")
    return False

def check_balances(client: SolanaClient, deposit_address: str, hot_wallet: str):
    """Check balances of deposit address and hot wallet"""
    deposit_balance = client.get_balance(deposit_address)
    hot_balance = client.get_balance(hot_wallet)
    
    print("\n" + "="*80)
    print("BALANCE CHECK")
    print("="*80)
    print(f"Deposit Address: {deposit_address}")
    print(f"  Balance: {lamports_to_sol(deposit_balance)} SOL ({deposit_balance} lamports)")
    print(f"\nHot Wallet: {hot_wallet}")
    print(f"  Balance: {lamports_to_sol(hot_balance)} SOL ({hot_balance} lamports)")
    print("="*80 + "\n")
    
    return deposit_balance, hot_balance

def main():
    parser = argparse.ArgumentParser(description='Test Solana deposit flow')
    parser.add_argument(
        '--amount',
        type=float,
        default=0.1,
        help='Amount of SOL to deposit (default: 0.1)'
    )
    parser.add_argument(
        '--address',
        type=str,
        help='Specific deposit address to test (optional)'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check balances without sending deposit'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("SOLANA DEPOSIT FLOW TEST")
    print("="*80 + "\n")
    
    # Initialize clients
    db = DatabaseManager()
    client = SolanaClient()
    
    # Get deposit address
    if args.address:
        deposit_address = args.address
        logger.info(f"Using specified address: {deposit_address}")
    else:
        addr_info = get_test_deposit_address(db)
        if not addr_info:
            return
        deposit_address = addr_info['address']
        logger.info(f"Using test address for user: {addr_info['user_id']}")
    
    hot_wallet = Config.SOLANA_HOT_WALLET_ADDRESS
    
    if not hot_wallet:
        logger.error("Hot wallet not configured")
        return
    
    # Check initial balances
    print("\nInitial Balances:")
    initial_deposit_balance, initial_hot_balance = check_balances(
        client,
        deposit_address,
        hot_wallet
    )
    
    if args.check_only:
        return
    
    # Send test deposit
    print(f"\nSending test deposit of {args.amount} SOL...")
    signature = send_test_deposit(client, deposit_address, args.amount)
    
    if not signature:
        logger.error("Failed to send test deposit")
        return
    
    print(f"\nTransaction sent: {signature}")
    print(f"Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
    
    # Monitor transaction
    print("\nWaiting for confirmation...")
    confirmed = monitor_transaction(client, signature)
    
    if not confirmed:
        logger.warning("Transaction not confirmed in time")
        return
    
    # Check final balances
    print("\nFinal Balances:")
    final_deposit_balance, final_hot_balance = check_balances(
        client,
        deposit_address,
        hot_wallet
    )
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Deposit sent: {args.amount} SOL")
    print(f"Transaction: {signature}")
    print(f"\nDeposit address balance change: "
          f"{lamports_to_sol(final_deposit_balance - initial_deposit_balance)} SOL")
    print(f"Hot wallet balance change: "
          f"{lamports_to_sol(final_hot_balance - initial_hot_balance)} SOL")
    print("\nNOTE: The deposit monitor should automatically sweep funds to hot wallet")
    print("      Check the onchain_service logs for sweep transaction details")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
