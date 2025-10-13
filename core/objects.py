"""
Git object models: Blob, Tree, and Commit.

This module implements the three fundamental Git object types using OOP principles:
- Blob: Stores file content
- Tree: Represents directory structure
- Commit: Captures repository snapshot with metadata
"""

import hashlib
import zlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


class GitObject:
    """Base class for all Git objects (Blob, Tree, Commit).
    
    Implements content-addressable storage using SHA-1 hashing.
    All objects are immutable once created.
    """
    
    def __init__(self, data: bytes = b""):
        """Initialize a Git object with raw data.
        
        Args:
            data: Raw byte content of the object
        """
        self._data = data
        self._hash: Optional[str] = None
    
    @property
    def type(self) -> str:
        """Return the type of Git object."""
        raise NotImplementedError("Subclasses must implement type property")
    
    @property
    def data(self) -> bytes:
        """Return the raw data content."""
        return self._data
    
    def serialize(self) -> bytes:
        """Serialize object to bytes for storage.
        
        Format: <type> <size>\0<content>
        
        Returns:
            Serialized object data ready for hashing and storage
        """
        content = self._serialize_content()
        header = f"{self.type} {len(content)}".encode()
        return header + b"\x00" + content
    
    def _serialize_content(self) -> bytes:
        """Serialize the content-specific data. Override in subclasses."""
        return self._data
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'GitObject':
        """Deserialize object from stored bytes.
        
        Args:
            data: Raw bytes from storage
            
        Returns:
            Reconstructed GitObject instance
        """
        # Split header and content
        null_idx = data.index(b"\x00")
        header = data[:null_idx].decode()
        content = data[null_idx + 1:]
        
        # Parse header
        obj_type, size = header.split(" ")
        
        # Create appropriate object type
        if obj_type == "blob":
            return Blob.from_content(content)
        elif obj_type == "tree":
            return Tree.deserialize_content(content)
        elif obj_type == "commit":
            return Commit.deserialize_content(content)
        else:
            raise ValueError(f"Unknown object type: {obj_type}")
    
    def compute_hash(self) -> str:
        """Compute SHA-1 hash of serialized object.
        
        Returns:
            40-character hexadecimal SHA-1 hash
        """
        if self._hash is None:
            serialized = self.serialize()
            self._hash = hashlib.sha1(serialized).hexdigest()
        return self._hash
    
    def compress(self) -> bytes:
        """Compress serialized object using zlib.
        
        Returns:
            Compressed bytes ready for file storage
        """
        return zlib.compress(self.serialize())
    
    @classmethod
    def decompress(cls, compressed_data: bytes) -> 'GitObject':
        """Decompress and deserialize object from storage.
        
        Args:
            compressed_data: Compressed bytes from file
            
        Returns:
            Reconstructed GitObject instance
        """
        data = zlib.decompress(compressed_data)
        return cls.deserialize(data)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.compute_hash()[:7]}>"


class Blob(GitObject):
    """Blob object stores file content.
    
    A blob is the simplest Git object - it just stores raw file content
    without any metadata (filename, permissions, etc.). The same content
    always produces the same blob, enabling deduplication.
    """
    
    def __init__(self, content: bytes):
        """Create a blob from file content.
        
        Args:
            content: Raw file content as bytes
        """
        super().__init__(content)
    
    @property
    def type(self) -> str:
        return "blob"
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Blob':
        """Create a blob from a file on disk.
        
        Args:
            filepath: Path to file to read
            
        Returns:
            New Blob object containing file content
        """
        with open(filepath, 'rb') as f:
            content = f.read()
        return cls(content)
    
    @classmethod
    def from_content(cls, content: bytes) -> 'Blob':
        """Create a blob from raw content.
        
        Args:
            content: Raw byte content
            
        Returns:
            New Blob object
        """
        return cls(content)
    
    def get_content(self) -> bytes:
        """Get the file content stored in this blob.
        
        Returns:
            Raw file content
        """
        return self._data


@dataclass
class TreeEntry:
    """Represents a single entry in a Tree object.
    
    Attributes:
        mode: File mode (e.g., '100644' for regular file, '040000' for directory)
        name: Filename or directory name
        hash: SHA-1 hash of the blob or tree object
    """
    mode: str
    name: str
    hash: str
    
    def __lt__(self, other: 'TreeEntry') -> bool:
        """Sort tree entries for consistent hashing."""
        return self.name < other.name


class Tree(GitObject):
    """Tree object represents a directory structure.
    
    A tree contains entries (files and subdirectories), each with:
    - mode: File permissions
    - name: Filename/directory name  
    - hash: SHA-1 of the blob/tree
    
    Trees form a Merkle tree structure where each node's hash depends
    on its children, enabling efficient change detection.
    """
    
    def __init__(self, entries: List[TreeEntry]):
        """Create a tree from a list of entries.
        
        Args:
            entries: List of TreeEntry objects
        """
        super().__init__()
        self._entries = sorted(entries)  # Sort for consistent hashing
    
    @property
    def type(self) -> str:
        return "tree"
    
    @property
    def entries(self) -> List[TreeEntry]:
        """Get all entries in this tree."""
        return self._entries.copy()
    
    def _serialize_content(self) -> bytes:
        """Serialize tree entries to bytes.
        
        Format: <mode> <name>\0<20-byte-hash>...
        """
        result = b""
        for entry in self._entries:
            # Convert mode and name to bytes
            entry_header = f"{entry.mode} {entry.name}".encode()
            # Convert hex hash to binary (20 bytes)
            hash_bytes = bytes.fromhex(entry.hash)
            result += entry_header + b"\x00" + hash_bytes
        return result
    
    @classmethod
    def deserialize_content(cls, content: bytes) -> 'Tree':
        """Deserialize tree from stored bytes.
        
        Args:
            content: Raw tree content (after header)
            
        Returns:
            Reconstructed Tree object
        """
        entries = []
        i = 0
        while i < len(content):
            # Find the null byte after mode and name
            null_idx = content.index(b"\x00", i)
            entry_header = content[i:null_idx].decode()
            
            # Parse mode and name
            mode, name = entry_header.split(" ", 1)
            
            # Extract 20-byte hash
            hash_bytes = content[null_idx + 1:null_idx + 21]
            hash_hex = hash_bytes.hex()
            
            entries.append(TreeEntry(mode, name, hash_hex))
            i = null_idx + 21
        
        return cls(entries)
    
    def find_entry(self, name: str) -> Optional[TreeEntry]:
        """Find an entry by name.
        
        Args:
            name: Filename or directory name
            
        Returns:
            TreeEntry if found, None otherwise
        """
        for entry in self._entries:
            if entry.name == name:
                return entry
        return None
    
    def __repr__(self) -> str:
        return f"<Tree {self.compute_hash()[:7]} with {len(self._entries)} entries>"


class Commit(GitObject):
    """Commit object captures a repository snapshot with metadata.
    
    A commit contains:
    - tree: SHA-1 of the root tree object
    - parent(s): SHA-1 of parent commit(s) (empty for initial commit)
    - author: Name and email of author
    - timestamp: When the commit was created
    - message: Commit message describing changes
    
    Commits form a directed acyclic graph (DAG) representing history.
    """
    
    def __init__(
        self,
        tree_hash: str,
        parent_hashes: List[str],
        author: str,
        email: str,
        message: str,
        timestamp: Optional[datetime] = None
    ):
        """Create a commit object.
        
        Args:
            tree_hash: SHA-1 hash of root tree
            parent_hashes: List of parent commit hashes (empty for initial commit)
            author: Author name
            email: Author email
            message: Commit message
            timestamp: Commit timestamp (defaults to now)
        """
        super().__init__()
        self.tree_hash = tree_hash
        self.parent_hashes = parent_hashes
        self.author = author
        self.email = email
        self.message = message
        self.timestamp = timestamp or datetime.now()
    
    @property
    def type(self) -> str:
        return "commit"
    
    def _serialize_content(self) -> bytes:
        """Serialize commit to bytes.
        
        Format:
        tree <hash>
        parent <hash>
        parent <hash>
        ...
        author <name> <email> <timestamp>
        
        <message>
        """
        lines = [f"tree {self.tree_hash}"]
        
        # Add parent commits
        for parent in self.parent_hashes:
            lines.append(f"parent {parent}")
        
        # Add author with timestamp
        timestamp_str = str(int(self.timestamp.timestamp()))
        lines.append(f"author {self.author} <{self.email}> {timestamp_str}")
        
        # Add empty line before message
        lines.append("")
        lines.append(self.message)
        
        return "\n".join(lines).encode()
    
    @classmethod
    def deserialize_content(cls, content: bytes) -> 'Commit':
        """Deserialize commit from stored bytes.
        
        Args:
            content: Raw commit content (after header)
            
        Returns:
            Reconstructed Commit object
        """
        text = content.decode()
        lines = text.split("\n")
        
        tree_hash = None
        parent_hashes = []
        author = None
        email = None
        timestamp = None
        message_lines = []
        
        i = 0
        # Parse header lines
        while i < len(lines) and lines[i]:
            line = lines[i]
            if line.startswith("tree "):
                tree_hash = line[5:]
            elif line.startswith("parent "):
                parent_hashes.append(line[7:])
            elif line.startswith("author "):
                # Parse: author Name <email> timestamp
                parts = line[7:].split()
                timestamp = datetime.fromtimestamp(int(parts[-1]))
                email_start = line.index("<") + 1
                email_end = line.index(">")
                email = line[email_start:email_end]
                author = line[7:email_start - 2]
            i += 1
        
        # Remaining lines are the message
        message = "\n".join(lines[i + 1:])
        
        return cls(tree_hash, parent_hashes, author, email, message, timestamp)
    
    def get_short_hash(self, length: int = 7) -> str:
        """Get abbreviated commit hash.
        
        Args:
            length: Number of characters to return
            
        Returns:
            Shortened hash string
        """
        return self.compute_hash()[:length]
    
    def get_summary(self) -> str:
        """Get first line of commit message.
        
        Returns:
            First line of commit message
        """
        return self.message.split("\n")[0]
    
    def __repr__(self) -> str:
        return f"<Commit {self.compute_hash()[:7]} '{self.get_summary()[:30]}...'>"
