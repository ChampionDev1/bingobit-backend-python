"""
System Wallet Manager - Queries blockchain for actual wallet balances
Does NOT manage database - only reads from blockchain and broadcasts events
"""
from decimal import Decimal
from typing import Dict, Optional
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from common.logger import setup_logger
from common.config import Config

logger = setup_logger(__name__)

class WalletManager:
    """
    Manage system wallet balance queries from blockchain
    
    IMPORTANT: This service does NOT write to database
    - Reads actual balance from blockchain
    - Returns balance information
    - Go API Gateway handles all database operations
    """

    def __init__(self):
        # Import blockchain clients here to avoid circular imports
        from services.onchain_service.blockchain import SolanaClient
        
        self.solana_client = None
        try:
            self.solana_client = SolanaClient()
            logger.info("WalletManager initialized with blockchain clients")
        except Exception as e:
            logger.warning(f"Failed to initialize blockchain clients: {e}")
            logger.warning("Wallet balance queries will not be available")

    def get_blockchain_balance(self, chain: str, address: str) -> str:
        """
        Get actual balance from blockchain
        
        Args:
            chain: Blockchain name (solana, ethereum, bsc)
            address: Wallet address
        
        Returns:
            Balance as string (in native token units, e.g., SOL)
        """
        chain = chain.lower()
        
        try:
            if chain == 'solana':
                if not self.solana_client:
                    raise ValueError("Solana client not available")
                
                balance_lamports = self.solana_client.get_balance(address)
                from common.utils import lamports_to_sol
                balance_sol = lamports_to_sol(balance_lamports)
                
                logger.info(f"Blockchain balance for {address}: {balance_sol} SOL")
                return str(balance_sol)
                
            elif chain == 'ethereum':
                # TODO: Implement Ethereum balance query
                logger.warning("Ethereum balance query not implemented yet")
                return "0"
                
            elif chain == 'bsc':
                # TODO: Implement BSC balance query
                logger.warning("BSC balance query not implemented yet")
                return "0"
                
            else:
                raise ValueError(f"Unknown chain: {chain}")
                
        except Exception as e:
            logger.error(f"Failed to get blockchain balance: {e}")
            raise

    def get_wallet_info(self, chain: str, wallet_type: str) -> Dict[str, str]:
        """
        Get wallet information including blockchain balance
        
        Args:
            chain: Blockchain name
            wallet_type: Wallet type (hot, cold, swap)
        
        Returns:
            Dictionary with wallet info and balance
        """
        chain = chain.lower()
        wallet_type = wallet_type.lower()
        
        # Get wallet address from config
        wallet_address = self._get_wallet_address(chain, wallet_type)
        
        if not wallet_address:
            logger.warning(f"No address configured for {chain}/{wallet_type}")
            return {
                "chain": chain,
                "wallet_type": wallet_type,
                "address": "",
                "balance": "0"
            }
        
        # Get actual balance from blockchain
        try:
            balance = self.get_blockchain_balance(chain, wallet_address)
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            balance = "0"
        
        return {
            "chain": chain,
            "wallet_type": wallet_type,
            "address": wallet_address,
            "balance": balance
        }
    
    def _get_wallet_address(self, chain: str, wallet_type: str) -> Optional[str]:
        """
        Get wallet address from configuration
        
        Args:
            chain: Blockchain name
            wallet_type: Wallet type
        
        Returns:
            Wallet address or None
        """
        if chain == 'solana' and wallet_type == 'hot':
            return Config.SOLANA_HOT_WALLET_ADDRESS
        
        # TODO: Add other wallet addresses from config
        # elif chain == 'solana' and wallet_type == 'cold':
        #     return Config.SOLANA_COLD_WALLET_ADDRESS
        
        return None