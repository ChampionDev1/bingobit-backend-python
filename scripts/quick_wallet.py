"""
Quick Hot Wallet Generator
Simple script to generate Solana devnet wallet
"""
from solders.keypair import Keypair
import base58

def main():
    print("🔑 Generating Solana Devnet Hot Wallet...")
    
    # Generate keypair
    keypair = Keypair()
    address = str(keypair.pubkey())
    private_key = base58.b58encode(bytes(keypair)).decode('utf-8')
    
    print(f"\n📋 COPY THESE TO YOUR .env FILE:")
    print(f"SOLANA_HOT_WALLET_ADDRESS={address}")
    print(f"SOLANA_HOT_WALLET_PRIVATE_KEY={private_key}")
    
    print(f"\n💰 GET DEVNET SOL:")
    print(f"https://faucet.solana.com/")
    print(f"Address: {address}")
    
    print(f"\n🔍 CHECK BALANCE:")
    print(f"https://explorer.solana.com/address/{address}?cluster=devnet")

if __name__ == '__main__':
    main()