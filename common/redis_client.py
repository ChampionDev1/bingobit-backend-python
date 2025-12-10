"""
Redis client for deposit address management
All deposit addresses are stored and retrieved from Redis
"""
import redis
import json
from typing import List, Dict, Any, Optional
from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class RedisClient:
    """Redis client wrapper for deposit address operations"""
    
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"Redis connected: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def get_all_deposit_addresses(self, chain: str) -> List[Dict[str, Any]]:
        """
        Get all deposit addresses for a specific chain from Redis
        
        Redis Key Format: deposit_addresses:{chain}
        Value Format: JSON array of address objects
        
        Args:
            chain: Blockchain name (e.g., 'solana')
        
        Returns:
            List of deposit address records
        """
        try:
            key = f"deposit_addresses:{chain}"
            data = self.client.get(key)
            
            if not data:
                logger.warning(f"No deposit addresses found in Redis for chain: {chain}")
                return []
            
            addresses = json.loads(data)
            logger.info(f"Retrieved {len(addresses)} deposit addresses for {chain}")
            return addresses
            
        except Exception as e:
            logger.error(f"Failed to get deposit addresses from Redis: {e}")
            return []
    
    def add_deposit_address(self, chain: str, address_data: Dict[str, Any]) -> bool:
        """
        Add a new deposit address to Redis
        
        Args:
            chain: Blockchain name
            address_data: Address information dict
        
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"deposit_addresses:{chain}"
            
            # Get existing addresses
            existing = self.get_all_deposit_addresses(chain)
            
            # Check if address already exists
            for addr in existing:
                if addr.get('address') == address_data.get('address'):
                    logger.warning(f"Address already exists: {address_data.get('address')}")
                    return False
            
            # Add new address
            existing.append(address_data)
            
            # Save back to Redis
            self.client.set(key, json.dumps(existing))
            logger.info(f"Added deposit address: {address_data.get('address')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add deposit address to Redis: {e}")
            return False
    
    def update_last_checked(self, chain: str, address: str):
        """
        Update last checked timestamp for an address
        
        Note: This is optional - can be used for monitoring
        """
        try:
            key = f"deposit_address_last_checked:{chain}:{address}"
            import time
            self.client.set(key, int(time.time()))
        except Exception as e:
            logger.error(f"Failed to update last checked: {e}")
    
    def get_deposit_address_by_address(self, chain: str, address: str) -> Optional[Dict[str, Any]]:
        """
        Get specific deposit address info
        
        Args:
            chain: Blockchain name
            address: Deposit address
        
        Returns:
            Address info dict or None
        """
        try:
            addresses = self.get_all_deposit_addresses(chain)
            for addr in addresses:
                if addr.get('address') == address:
                    return addr
            return None
        except Exception as e:
            logger.error(f"Failed to get deposit address: {e}")
            return None
    
    def set_deposit_addresses(self, chain: str, addresses: List[Dict[str, Any]]) -> bool:
        """
        Set all deposit addresses for a chain (overwrites existing)
        
        Args:
            chain: Blockchain name
            addresses: List of address dicts
        
        Returns:
            True if successful
        """
        try:
            key = f"deposit_addresses:{chain}"
            self.client.set(key, json.dumps(addresses))
            logger.info(f"Set {len(addresses)} deposit addresses for {chain}")
            return True
        except Exception as e:
            logger.error(f"Failed to set deposit addresses: {e}")
            return False
    
    def close(self):
        """Close Redis connection"""
        try:
            self.client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
