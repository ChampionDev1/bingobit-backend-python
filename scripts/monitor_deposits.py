"""
Real-time deposit monitoring dashboard
Shows active deposits and their status
"""
import sys
import os
import time
from datetime import datetime
from typing import List, Dict, Any

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from common import setup_logger, lamports_to_sol
from common.database import DatabaseManager
from services.onchain_service.blockchain import SolanaClient

logger = setup_logger(__name__)

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_timestamp(ts):
    """Format timestamp for display"""
    if not ts:
        return "N/A"
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def display_dashboard(
    addresses: List[Dict[str, Any]],
    transactions: List[Dict[str, Any]],
    client: SolanaClient
):
    """Display monitoring dashboard"""
    clear_screen()
    
    print("=" * 100)
    print(" " * 35 + "DEPOSIT MONITORING DASHBOARD")
    print("=" * 100)
    print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    # Deposit Addresses Section
    print("\n📍 DEPOSIT ADDRESSES")
    print("-" * 100)
    print(f"{'User ID':<15} {'Address':<45} {'Balance (SOL)':<15} {'Status':<10}")
    print("-" * 100)
    
    for addr in addresses[:10]:  # Show first 10
        balance = client.get_balance(addr['address'])
        balance_sol = lamports_to_sol(balance)
        status = "✓ Active" if addr['is_active'] else "✗ Inactive"
        
        print(f"{addr['user_id']:<15} {addr['address'][:42]:<45} "
              f"{balance_sol:>13.9f}  {status:<10}")
    
    if len(addresses) > 10:
        print(f"\n... and {len(addresses) - 10} more addresses")
    
    # Recent Transactions Section
    print("\n\n💰 RECENT DEPOSIT TRANSACTIONS")
    print("-" * 100)
    print(f"{'TX Hash':<20} {'User':<12} {'Amount':<12} {'Status':<15} {'Confirmations':<15} {'Time':<20}")
    print("-" * 100)
    
    if not transactions:
        print("No transactions found")
    else:
        for tx in transactions[:15]:  # Show last 15
            tx_hash_short = tx['tx_hash'][:16] + "..."
            amount = f"{float(tx['amount']):.4f} SOL"
            status = tx['status'].upper()
            confirmations = tx.get('confirmations', 0)
            timestamp = format_timestamp(tx.get('detected_at'))
            
            # Color code status
            status_display = status
            if status == 'COMPLETED':
                status_display = f"✓ {status}"
            elif status == 'FAILED':
                status_display = f"✗ {status}"
            elif status in ['SWEEPING', 'CONFIRMING']:
                status_display = f"⟳ {status}"
            
            print(f"{tx_hash_short:<20} {tx['user_id'][:10]:<12} {amount:<12} "
                  f"{status_display:<15} {confirmations:<15} {timestamp[:19]:<20}")
    
    # Statistics Section
    print("\n\n📊 STATISTICS")
    print("-" * 100)
    
    total_deposits = len(transactions)
    completed = sum(1 for tx in transactions if tx['status'] == 'completed')
    pending = sum(1 for tx in transactions if tx['status'] in ['detected', 'pending', 'confirming'])
    sweeping = sum(1 for tx in transactions if tx['status'] == 'sweeping')
    failed = sum(1 for tx in transactions if tx['status'] == 'failed')
    
    total_amount = sum(float(tx['amount']) for tx in transactions)
    
    print(f"Total Deposits: {total_deposits}")
    print(f"Completed: {completed} | Pending: {pending} | Sweeping: {sweeping} | Failed: {failed}")
    print(f"Total Volume: {total_amount:.4f} SOL")
    
    print("\n" + "=" * 100)
    print("Press Ctrl+C to exit | Refreshing every 5 seconds...")
    print("=" * 100)

def main():
    """Main monitoring loop"""
    print("\nStarting deposit monitor dashboard...")
    print("Connecting to database and blockchain...\n")
    
    db = DatabaseManager()
    client = SolanaClient()
    
    try:
        while True:
            try:
                # Fetch data
                addresses = db.get_all_deposit_addresses('solana')
                transactions = db.get_pending_transactions('solana')
                
                # Also get recent completed transactions
                with db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT *
                            FROM deposit_transactions
                            WHERE chain = 'solana'
                            ORDER BY detected_at DESC
                            LIMIT 50
                        """)
                        columns = [desc[0] for desc in cursor.description]
                        all_transactions = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Display dashboard
                display_dashboard(addresses, all_transactions, client)
                
                # Wait before refresh
                time.sleep(5)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\n\nShutting down monitor...")
        print("Goodbye! 👋\n")

if __name__ == '__main__':
    main()
