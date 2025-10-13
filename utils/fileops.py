"""
File operation utilities.

Provides helper functions for file and directory operations.
"""

import os
import shutil
from typing import List, Optional, Union
from pathlib import Path


def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist.
    
    Args:
        path: Directory path to create
    """
    os.makedirs(path, exist_ok=True)


def read_file(filepath: str, binary: bool = False) -> Union[str, bytes]:
    """Read file content.
    
    Args:
        filepath: Path to file
        binary: If True, read in binary mode
        
    Returns:
        File content as string or bytes
    """
    mode = 'rb' if binary else 'r'
    encoding = None if binary else 'utf-8'
    
    with open(filepath, mode, encoding=encoding) as f:
        return f.read()


def write_file(filepath: str, content: Union[str, bytes], binary: bool = False) -> None:
    """Write content to file.
    
    Args:
        filepath: Path to file
        content: Content to write
        binary: If True, write in binary mode
    """
    # Ensure parent directory exists
    ensure_dir(os.path.dirname(filepath))
    
    mode = 'wb' if binary else 'w'
    encoding = None if binary else 'utf-8'
    
    with open(filepath, mode, encoding=encoding) as f:
        f.write(content)


def list_files_recursive(directory: str, exclude_dirs: Optional[List[str]] = None) -> List[str]:
    """List all files in directory recursively.
    
    Args:
        directory: Root directory to search
        exclude_dirs: List of directory names to exclude (e.g., ['.mygit', '.git'])
        
    Returns:
        List of file paths relative to directory
    """
    if exclude_dirs is None:
        exclude_dirs = []
    
    files = []
    for root, dirs, filenames in os.walk(directory):
        # Remove excluded directories from search
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, directory)
            files.append(rel_path)
    
    return files


def get_file_mode(filepath: str) -> str:
    """Get file mode for tree entry.
    
    Args:
        filepath: Path to file
        
    Returns:
        Mode string (e.g., '100644' for regular file, '100755' for executable)
    """
    stat = os.stat(filepath)
    
    # Check if executable
    is_executable = stat.st_mode & 0o111
    
    if os.path.isdir(filepath):
        return "040000"  # Directory
    elif is_executable:
        return "100755"  # Executable file
    else:
        return "100644"  # Regular file


def get_file_mtime(filepath: str) -> float:
    """Get file modification time.
    
    Args:
        filepath: Path to file
        
    Returns:
        Modification timestamp
    """
    return os.path.getmtime(filepath)


def is_binary_file(filepath: str) -> bool:
    """Check if file is binary.
    
    Args:
        filepath: Path to file
        
    Returns:
        True if file appears to be binary
    """
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(8192)
            if b'\x00' in chunk:
                return True
            return False
    except Exception:
        return True


def match_gitignore_pattern(filepath: str, pattern: str) -> bool:
    """Check if filepath matches a gitignore-style pattern.
    
    Args:
        filepath: File path to check
        pattern: Gitignore pattern (e.g., '*.pyc', 'node_modules/')
        
    Returns:
        True if filepath matches pattern
    """
    from fnmatch import fnmatch
    
    # Normalize paths
    filepath = filepath.replace(os.sep, '/')
    pattern = pattern.replace(os.sep, '/')
    
    # Directory pattern
    if pattern.endswith('/'):
        return filepath.startswith(pattern[:-1] + '/')
    
    # Wildcard pattern
    if '*' in pattern or '?' in pattern:
        return fnmatch(filepath, pattern)
    
    # Exact match
    return filepath == pattern or filepath.startswith(pattern + '/')


from typing import Union
