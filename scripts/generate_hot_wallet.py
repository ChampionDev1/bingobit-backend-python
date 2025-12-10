"""
Generate Hot Wallet for Solana Devnet
Creates a new keypair for hot wallet operations
"""
import sys
import os
from solders.keypair import Keypair
import base58

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from common import setup_logger
from services.onchain_service.blockchain import SolanaClient

logger = setup_logger(__name__)

def generate_hot_wallet():
    """Generate new hot wallet keypair"""
    print("\n" + "="*80)
    print("SOLANA HOT WALLET GENERATOR (DEVNET)")
    print("="*80)
    
    # Generate new keypair
    keypair = Keypair()
    address = str(keypair.pubkey())
    private_key = base58.b58encode(bytes(keypair)).decode('utf-8')
    
    print(f"\n🔑 NEW HOT WALLET GENERATED:")
    print(f"Address: {address}")
    print(f"Private Key: {private_key}")
    
    print(f"\n📝 ADD TO YOUR .env FILE:")
    print(f"SOLANA_HOT_WALLET_ADDRESS={address}")
    print(f"SOLANA_HOT_WALLET_PRIVATE_KEY={private_key}")
    
    # Test the wallet
    try:
        client = SolanaClient()
        balance = client.get_balance(address)
        print(f"\n💰 CURRENT BALANCE:")
        print(f"Balance: {balance / 1e9} SOL ({balance} lamports)")
        
        if balance == 0:
            print(f"\n💡 TO GET DEVNET SOL:")
            print(f"1. Visit: https://faucet.solana.com/")
            print(f"2. Enter address: {address}")
            print(f"3. Click 'Request 2 SOL'")
            print(f"\nOr use Solana CLI:")
            print(f"solana airdrop 2 {address} --url devnet")
        
    except Exception as e:
        print(f"\n⚠️ Could not check balance: {e}")
        print("This is normal if Solana client is not configured yet")
    
    print("\n" + "="*80)
    print("⚠️  SECURITY WARNING:")
    print("- This is for DEVNET testing only!")
    print("- Never use this wallet on MAINNET!")
    print("- Keep the private key secure!")
    print("- Add the keys to .env file and restart services")
    print("="*80 + "\n")
    
    return address, private_key

def check_existing_wallet():
    """Check if hot wallet is already configured"""
    from dotenv import load_dotenv
    load_dotenv()
    
    address = os.getenv('SOLANA_HOT_WALLET_ADDRESS')
    private_key = os.getenv('SOLANA_HOT_WALLET_PRIVATE_KEY')
    
    if address and private_key:
        print("\n" + "="*80)
        print("EXISTING HOT WALLET FOUND")
        print("="*80)
        print(f"Address: {address}")
        print(f"Private Key: {private_key[:20]}...")
        
        try:
            client = SolanaClient()
            balance = client.get_balance(address)
            print(f"\nCurrent Balance: {balance / 1e9} SOL")
            
            if balance == 0:
                print(f"\n💡 TO GET DEVNET SOL:")
                print(f"Visit: https://faucet.solana.com/")
                print(f"Address: {address}")
            
        except Exception as e:
            print(f"Could not check balance: {e}")
        
        print("="*80 + "\n")
        return True
    
    return False

def fund_wallet_instructions(address: str):
    """Show instructions for funding the wallet"""
    print(f"\n" + "="*80)
    print("HOW TO FUND YOUR HOT WALLET")
    print("="*80)
    
    print(f"\n🌐 METHOD 1: Web Faucet (Recommended)")
    print(f"1. Visit: https://faucet.solana.com/")
    print(f"2. Enter your address: {address}")
    print(f"3. Click 'Request 2 SOL'")
    print(f"4. Wait for confirmation")
    
    print(f"\n💻 METHOD 2: Solana CLI")
    print(f"solana airdrop 2 {address} --url devnet")
    
    print(f"\n📱 METHOD 3: Phantom Wallet")
    print(f"1. Install Phantom wallet extension")
    print(f"2. Switch to 'Devnet' network")
    print(f"3. Go to Settings → Developer Settings")
    print(f"4. Click 'Airdrop' and request SOL")
    print(f"5. Send SOL to: {address}")
    
    print(f"\n✅ VERIFY FUNDING:")
    print(f"python -c \"")
    print(f"from services.onchain_service.blockchain import SolanaClient")
    print(f"client = SolanaClient()")
    print(f"balance = client.get_balance('{address}')")
    print(f"print(f'Balance: {{balance / 1e9}} SOL')")
    print(f"\"")
    
    print("="*80 + "\n")

def main():
    """Main function"""
    print("Checking for existing hot wallet...")
    
    if check_existing_wallet():
        choice = input("Hot wallet already exists. Generate new one? (y/N): ").lower()
        if choice != 'y':
            print("Using existing hot wallet.")
            return
    
    print("Generating new hot wallet...")
    address, private_key = generate_hot_wallet()
    
    # Show funding instructions
    fund_wallet_instructions(address)
    
    # Offer to update .env file
    update_env = input("Update .env file automatically? (Y/n): ").lower()
    if update_env != 'n':
        update_env_file(address, private_key)

def update_env_file(address: str, private_key: str):
    """Update .env file with hot wallet info"""
    try:
        env_path = '.env'
        
        # Read existing .env
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
        
        # Remove existing hot wallet lines
        lines = [line for line in lines if not line.startswith('SOLANA_HOT_WALLET_')]
        
        # Add new hot wallet lines
        lines.append(f"\n# Hot Wallet Configuration\n")
        lines.append(f"SOLANA_HOT_WALLET_ADDRESS={address}\n")
        lines.append(f"SOLANA_HOT_WALLET_PRIVATE_KEY={private_key}\n")
        
        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        print(f"\n✅ Updated {env_path} with hot wallet configuration")
        print("🔄 Please restart your services to use the new wallet")
        
    except Exception as e:
        print(f"\n❌ Failed to update .env file: {e}")
        print("Please add the wallet configuration manually")

if __name__ == '__main__':
    main()