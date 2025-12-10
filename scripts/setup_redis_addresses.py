"""
Setup test deposit addresses in Redis
Generates test addresses and stores them in Redis
"""
import sys
import os
from solders.keypair import Keypair
import base58

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from common import RedisClient, setup_logger

logger = setup_logger(__name__)

def generate_test_deposit_addresses(count: int = 5):
    """Generate test deposit addresses for devnet"""
    logger.info(f"Generating {count} test deposit addresses...")
    
    redis_client = RedisClient()
    addresses = []
    
    try:
        for i in range(count):
            # Generate new keypair
            keypair = Keypair()
            address = str(keypair.pubkey())
            private_key = base58.b58encode(bytes(keypair)).decode('utf-8')
            user_id = f"test_user_{i+1}"
            
            # Create address data
            addr_data = {
                "id": f"addr_{i+1}",
                "user_id": user_id,
                "address": address,
                "private_key": private_key,
                "chain": "solana",
                "is_active": True
            }
            
            addresses.append(addr_data)
            logger.info(f"Created deposit address {i+1}: {address}")
        
        # Save all addresses to Redis
        redis_client.set_deposit_addresses("solana", addresses)
        logger.info(f"Successfully saved {len(addresses)} deposit addresses to Redis")
        
        # Print addresses for testing
        print("\n" + "="*80)
        print("TEST DEPOSIT ADDRESSES (Solana Devnet) - Stored in Redis")
        print("="*80)
        for addr in addresses:
            print(f"\nUser ID: {addr['user_id']}")
            print(f"Address: {addr['address']}")
            print(f"Private Key: {addr['private_key'][:20]}...")
        print("\n" + "="*80)
        print("\nYou can request devnet SOL from: https://faucet.solana.com/")
        print("="*80 + "\n")
        
        return addresses
        
    except Exception as e:
        logger.error(f"Failed to generate addresses: {e}")
        return []
    finally:
        redis_client.close()

def setup_hot_wallet():
    """Setup or display hot wallet configuration"""
    from common import Config
    
    logger.info("Hot wallet configuration...")
    
    if not Config.SOLANA_HOT_WALLET_ADDRESS:
        logger.warning("Hot wallet not configured!")
        print("\n" + "="*80)
        print("HOT WALLET SETUP REQUIRED")
        print("="*80)
        print("\nGenerate a hot wallet keypair and set these environment variables:")
        print("  SOLANA_HOT_WALLET_ADDRESS=<your_hot_wallet_address>")
        print("  SOLANA_HOT_WALLET_PRIVATE_KEY=<your_hot_wallet_private_key>")
        print("\nOr generate one now:")
        
        keypair = Keypair()
        address = str(keypair.pubkey())
        private_key = base58.b58encode(bytes(keypair)).decode('utf-8')
        
        print(f"\nGenerated Hot Wallet:")
        print(f"  Address: {address}")
        print(f"  Private Key: {private_key}")
        print("\nIMPORTANT: Save these credentials securely!")
        print("Add them to your .env file:")
        print(f"  SOLANA_HOT_WALLET_ADDRESS={address}")
        print(f"  SOLANA_HOT_WALLET_PRIVATE_KEY={private_key}")
        print("="*80 + "\n")
    else:
        print("\n" + "="*80)
        print("HOT WALLET CONFIGURED")
        print("="*80)
        print(f"Address: {Config.SOLANA_HOT_WALLET_ADDRESS}")
        print("="*80 + "\n")

def main():
    """Main setup function"""
    print("\n" + "="*80)
    print("SOLANA DEPOSIT SYSTEM - REDIS SETUP")
    print("="*80 + "\n")
    
    # Setup hot wallet
    setup_hot_wallet()
    
    # Generate test addresses
    generate_test_deposit_addresses(5)
    
    print("\nSetup complete! You can now:")
    print("1. Fund the hot wallet with devnet SOL")
    print("2. Send test deposits to the generated addresses")
    print("3. Start the onchain service to monitor deposits")
    print("\nStart service with: python services/onchain_service/main.py\n")

if __name__ == '__main__':
    main()
