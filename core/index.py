"""
Index (staging area) management for MyGit.

The index stores information about files that will be included in the next commit.
"""

import os
import json
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict

from core.objects import Blob, Tree, TreeEntry
from core.repository import Repository
from utils.fileops import get_file_mode, get_file_mtime, list_files_recursive, match_gitignore_pattern


@dataclass
class IndexEntry:
    """Represents a single file in the staging area.
    
    Attributes:
        path: File path relative to repository root
        mode: File mode (permissions)
        hash: SHA-1 hash of blob object
        size: File size in bytes
        mtime: File modification time
    """
    path: str
    mode: str
    hash: str
    size: int
    mtime: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'IndexEntry':
        """Create IndexEntry from dictionary."""
        return cls(**data)


class Index:
    """Manages the staging area (index) for a repository.
    
    The index tracks which files are staged for the next commit.
    """
    
    def __init__(self, repo: Repository):
        """Initialize index for repository.
        
        Args:
            repo: Repository instance
        """
        self.repo = repo
        self._entries: Dict[str, IndexEntry] = {}
        self._load()
    
    def _load(self) -> None:
        """Load index from disk."""
        if os.path.exists(self.repo.index_file):
            data = json.loads(open(self.repo.index_file).read())
            self._entries = {
                path: IndexEntry.from_dict(entry_data)
                for path, entry_data in data.items()
            }
    
    def _save(self) -> None:
        """Save index to disk."""
        data = {
            path: entry.to_dict()
            for path, entry in self._entries.items()
        }
        with open(self.repo.index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_file(self, filepath: str) -> str:
        """Add a file to the staging area.
        
        Creates a blob object and updates the index.
        
        Args:
            filepath: Path to file (relative to repo root)
            
        Returns:
            SHA-1 hash of created blob
        """
        full_path = os.path.join(self.repo.root_path, filepath)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if os.path.isdir(full_path):
            raise IsADirectoryError(f"Cannot add directory directly: {filepath}")
        
        # Create blob from file
        blob = Blob.from_file(full_path)
        blob_hash = self.repo.write_object(blob)
        
        # Add to index
        entry = IndexEntry(
            path=filepath,
            mode=get_file_mode(full_path),
            hash=blob_hash,
            size=os.path.getsize(full_path),
            mtime=get_file_mtime(full_path)
        )
        
        self._entries[filepath] = entry
        self._save()
        
        return blob_hash
    
    def add_files(self, patterns: List[str]) -> List[str]:
        """Add multiple files matching patterns.
        
        Args:
            patterns: List of file patterns (e.g., ['*.py', 'src/'])
            
        Returns:
            List of added file paths
        """
        added_files = []
        
        # Get ignore patterns
        ignore_patterns = self.repo.get_ignore_patterns()
        # Always ignore .mygit directory
        ignore_patterns.append('.mygit/')
        
        for pattern in patterns:
            if pattern == ".":
                # Add all files in repository
                all_files = list_files_recursive(self.repo.root_path, exclude_dirs=['.mygit'])
                for filepath in all_files:
                    # Check ignore patterns
                    if not any(match_gitignore_pattern(filepath, p) for p in ignore_patterns):
                        try:
                            self.add_file(filepath)
                            added_files.append(filepath)
                        except Exception:
                            pass  # Skip files that can't be added
            else:
                # Add specific file or directory
                full_path = os.path.join(self.repo.root_path, pattern)
                
                if os.path.isfile(full_path):
                    if not any(match_gitignore_pattern(pattern, p) for p in ignore_patterns):
                        self.add_file(pattern)
                        added_files.append(pattern)
                elif os.path.isdir(full_path):
                    # Add all files in directory
                    dir_files = list_files_recursive(full_path)
                    for file in dir_files:
                        rel_path = os.path.relpath(os.path.join(full_path, file), self.repo.root_path)
                        if not any(match_gitignore_pattern(rel_path, p) for p in ignore_patterns):
                            try:
                                self.add_file(rel_path)
                                added_files.append(rel_path)
                            except Exception:
                                pass
        
        return added_files
    
    def remove_file(self, filepath: str) -> None:
        """Remove a file from the staging area.
        
        Args:
            filepath: Path to file (relative to repo root)
        """
        if filepath in self._entries:
            del self._entries[filepath]
            self._save()
    
    def clear(self) -> None:
        """Clear all entries from the staging area."""
        self._entries = {}
        self._save()
    
    def get_entry(self, filepath: str) -> Optional[IndexEntry]:
        """Get index entry for a file.
        
        Args:
            filepath: File path
            
        Returns:
            IndexEntry or None if not staged
        """
        return self._entries.get(filepath)
    
    def get_all_entries(self) -> Dict[str, IndexEntry]:
        """Get all staged entries.
        
        Returns:
            Dictionary of path -> IndexEntry
        """
        return self._entries.copy()
    
    def is_empty(self) -> bool:
        """Check if staging area is empty.
        
        Returns:
            True if no files are staged
        """
        return len(self._entries) == 0
    
    def create_tree(self) -> Tree:
        """Create a tree object from staged files.
        
        Builds a tree structure representing the current staging area.
        
        Returns:
            Root Tree object
        """
        if self.is_empty():
            raise ValueError("Cannot create tree from empty index")
        
        # Build nested directory structure
        tree_contents: Dict[str, Dict] = {}
        
        for path, entry in self._entries.items():
            parts = path.split(os.sep)
            current = tree_contents
            
            # Navigate/create nested structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add file entry
            current[parts[-1]] = entry
        
        # Recursively create tree objects
        def build_tree(contents: Dict) -> Tree:
            entries = []
            
            for name, value in sorted(contents.items()):
                if isinstance(value, IndexEntry):
                    # File entry
                    entries.append(TreeEntry(
                        mode=value.mode,
                        name=name,
                        hash=value.hash
                    ))
                else:
                    # Directory - recursively build subtree
                    subtree = build_tree(value)
                    subtree_hash = self.repo.write_object(subtree)
                    entries.append(TreeEntry(
                        mode="040000",
                        name=name,
                        hash=subtree_hash
                    ))
            
            return Tree(entries)
        
        return build_tree(tree_contents)
    
    def get_staged_files(self) -> List[str]:
        """Get list of staged file paths.
        
        Returns:
            List of file paths
        """
        return sorted(self._entries.keys())
    
    def __len__(self) -> int:
        """Return number of staged files."""
        return len(self._entries)
    
    def __contains__(self, filepath: str) -> bool:
        """Check if file is staged."""
        return filepath in self._entries
    
    def __repr__(self) -> str:
        return f"<Index with {len(self._entries)} staged files>"
