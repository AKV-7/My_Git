"""
SHA-1 hashing utilities for content-addressable storage.

Provides helper functions for hashing file content and objects.
"""

import hashlib
from typing import Union


def hash_object(data: bytes) -> str:
    """Compute SHA-1 hash of data.
    
    Args:
        data: Bytes to hash
        
    Returns:
        40-character hexadecimal SHA-1 hash
    """
    return hashlib.sha1(data).hexdigest()


def hash_file(filepath: str) -> str:
    """Compute SHA-1 hash of file content.
    
    Args:
        filepath: Path to file
        
    Returns:
        SHA-1 hash of file content
    """
    with open(filepath, 'rb') as f:
        return hash_object(f.read())


def short_hash(full_hash: str, length: int = 7) -> str:
    """Get abbreviated hash.
    
    Args:
        full_hash: Full 40-character hash
        length: Number of characters to return
        
    Returns:
        Shortened hash
    """
    return full_hash[:length]


def expand_short_hash(short_hash: str, available_hashes: list) -> Union[str, None]:
    """Expand abbreviated hash to full hash.
    
    Args:
        short_hash: Abbreviated hash (minimum 4 characters)
        available_hashes: List of full hashes to search
        
    Returns:
        Full hash if unique match found, None otherwise
    """
    matches = [h for h in available_hashes if h.startswith(short_hash)]
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        return None
    else:
        # Ambiguous - multiple matches
        raise ValueError(f"Ambiguous hash '{short_hash}' matches {len(matches)} objects")
