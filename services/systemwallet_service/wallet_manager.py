from decimal import Decimal
from typing import Dict
import redis
import json

class WalletManager:
    """ Manage All Chain's hot/cold/swap wallets """

    def __init__(self, redis_client = None):
        self.redis = redis_client

        self.wallets = {
            'solana': {
                'hot': Decimal('0'),
                'cold': Decimal('0'),
                'swap': Decimal('0')
            },
            'ethereum': {
                'hot': Decimal('0'),
                'cold': Decimal('0'),
                'swap': Decimal('0')
            },
            'bsc': {
                'hot': Decimal('0'),
                'cold': Decimal('0'),
                'swap': Decimal('0')
            }
        }

    def add_balance(self, chain: str, wallet_type: str, amount: str) -> str:
        chain = chain.lower()
        wallet_type = wallet_type.lower()

        if chain not in self.wallets:
            raise ValueError(f"Unknown chain: {chain}")
        if wallet_type not in self.wallets[chain]:
            raise ValueError(f"Unknown wallet type: {wallet_type}")

        self.wallets[chain][wallet_type] += Decimal(amount)

        return str(self.wallets[chain][wallet_type])

    def get_balance():
        pass

    def transfer():
        pass