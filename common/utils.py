"""
Common utility functions
"""
from decimal import Decimal
from typing import Optional

def lamports_to_sol(lamports: int) -> Decimal:
    """
    Convert lamports to SOL
    
    Args:
        lamports: Amount in lamports
    
    Returns:
        Amount in SOL as Decimal
    """
    return Decimal(lamports) / Decimal(10**9)

def sol_to_lamports(sol: float) -> int:
    """
    Convert SOL to lamports
    
    Args:
        sol: Amount in SOL
    
    Returns:
        Amount in lamports
    """
    return int(Decimal(str(sol)) * Decimal(10**9))

def format_address(address: str, prefix: int = 4, suffix: int = 4) -> str:
    """
    Format blockchain address for display
    
    Args:
        address: Full blockchain address
        prefix: Number of characters to show at start
        suffix: Number of characters to show at end
    
    Returns:
        Formatted address (e.g., "AbCd...XyZ1")
    """
    if len(address) <= prefix + suffix:
        return address
    return f"{address[:prefix]}...{address[-suffix:]}"

def validate_solana_address(address: str) -> bool:
    """
    Basic validation for Solana address format
    
    Args:
        address: Solana address to validate
    
    Returns:
        True if valid format, False otherwise
    """
    if not address or len(address) < 32 or len(address) > 44:
        return False
    
    # Base58 character set
    base58_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
    return all(c in base58_chars for c in address)

def calculate_fee_with_buffer(base_fee: int, buffer_percent: float = 20.0) -> int:
    """
    Calculate fee with safety buffer
    
    Args:
        base_fee: Base fee amount
        buffer_percent: Buffer percentage to add
    
    Returns:
        Fee with buffer applied
    """
    return int(base_fee * (1 + buffer_percent / 100))
