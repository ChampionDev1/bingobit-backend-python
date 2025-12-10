"""
Generate test destination address for withdrawal testing
"""
from solders.keypair import Keypair
import base58

def main():
    print("🎯 Generating test destination address...")
    
    # Generate test keypair
    keypair = Keypair()
    address = str(keypair.pubkey())
    private_key = base58.b58encode(bytes(keypair)).decode('utf-8')
    
    print(f"\n📋 TEST DESTINATION ADDRESS:")
    print(f"Address: {address}")
    print(f"Private Key: {private_key}")
    
    print(f"\n🔍 Explorer Link:")
    print(f"https://explorer.solana.com/address/{address}?cluster=devnet")
    
    print(f"\n💡 Use this address for withdrawal testing:")
    print(f"python scripts/test_withdraw_flow.py --user-id test_user --to {address} --amount 0.01")
    
    return address, private_key

if __name__ == '__main__':
    main()