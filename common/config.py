"""
Central configuration for all services
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Global configuration constants"""
    
    # Service URLs
    SYSTEMWALLET_SERVICE_URL = os.getenv("SYSTEMWALLET_SERVICE_URL", "localhost:50052")
    ONCHAIN_SERVICE_URL = os.getenv("ONCHAIN_SERVICE_URL", "localhost:50051")
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_DEPOSIT_TOPIC = "deposit.events"
    KAFKA_PRODUCER_CONFIG = {
        "acks": "all",
        "retries": 3,
        "max_in_flight_requests_per_connection": 1
    }
    
    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "crypto_platform")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    
    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    
    # Solana Configuration
    SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    SOLANA_WS_URL = os.getenv("SOLANA_WS_URL", "wss://api.devnet.solana.com")
    SOLANA_NETWORK = os.getenv("SOLANA_NETWORK", "devnet")
    
    # Hot Wallet Configuration (stored securely in production)
    SOLANA_HOT_WALLET_PRIVATE_KEY = os.getenv("SOLANA_HOT_WALLET_PRIVATE_KEY", "")
    SOLANA_HOT_WALLET_ADDRESS = os.getenv("SOLANA_HOT_WALLET_ADDRESS", "")
    
    # Transaction Configuration
    MIN_CONFIRMATIONS = int(os.getenv("MIN_CONFIRMATIONS", "15"))
    TRANSACTION_TIMEOUT = int(os.getenv("TRANSACTION_TIMEOUT", "60"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    # Fee Configuration (in lamports)
    SOLANA_BASE_FEE = int(os.getenv("SOLANA_BASE_FEE", "5000"))
    SOLANA_PRIORITY_FEE = int(os.getenv("SOLANA_PRIORITY_FEE", "10000"))
    SOLANA_RENT_EXEMPT_MINIMUM = int(os.getenv("SOLANA_RENT_EXEMPT_MINIMUM", "890880"))
    
    # Monitoring Configuration
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
    
    # Minimum amounts (in lamports for Solana)
    MIN_DEPOSIT_AMOUNT = int(os.getenv("MIN_DEPOSIT_AMOUNT", "10000000"))  # 0.01 SOL
    DUST_THRESHOLD = int(os.getenv("DUST_THRESHOLD", "5000"))  # 0.000005 SOL

class ChainConfig:
    """Chain-specific configurations"""
    
    CHAINS = {
        "solana": {
            "chain_id": "solana",
            "decimals": 9,
            "native_token": "SOL",
            "explorer_url": "https://explorer.solana.com",
            "min_confirmations": 15
        },
        "ethereum": {
            "chain_id": "ethereum",
            "decimals": 18,
            "native_token": "ETH",
            "explorer_url": "https://etherscan.io",
            "min_confirmations": 12
        },
        "bsc": {
            "chain_id": "bsc",
            "decimals": 18,
            "native_token": "BNB",
            "explorer_url": "https://bscscan.com",
            "min_confirmations": 15
        }
    }
    
    @classmethod
    def get_chain_config(cls, chain: str) -> Dict[str, Any]:
        """Get configuration for specific chain"""
        chain_lower = chain.lower()
        if chain_lower not in cls.CHAINS:
            raise ValueError(f"Unsupported chain: {chain}")
        return cls.CHAINS[chain_lower]

class DepositStatus:
    """Deposit transaction status constants"""
    DETECTED = "detected"
    PENDING = "pending"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    SWEEPING = "sweeping"
    SWEPT = "swept"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_FEE = "insufficient_fee"
