"""
Repository management for MyGit.

Handles .mygit directory structure, object storage, and repository operations.
"""

import os
import json
from typing import Optional, List, Dict
from pathlib import Path

from core.objects import GitObject, Blob, Tree, Commit
from utils.fileops import ensure_dir, read_file, write_file


class Repository:
    """Manages a MyGit repository.
    
    Handles:
    - Repository initialization
    - Object storage and retrieval
    - Reference management (branches, HEAD)
    - Configuration
    """
    
    def __init__(self, path: str = "."):
        """Initialize repository at given path.
        
        Args:
            path: Path to repository root (contains or will contain .mygit/)
        """
        self.root_path = os.path.abspath(path)
        self.git_dir = os.path.join(self.root_path, ".mygit")
        self.objects_dir = os.path.join(self.git_dir, "objects")
        self.refs_dir = os.path.join(self.git_dir, "refs")
        self.heads_dir = os.path.join(self.refs_dir, "heads")
        self.index_file = os.path.join(self.git_dir, "index")
        self.head_file = os.path.join(self.git_dir, "HEAD")
        self.config_file = os.path.join(self.git_dir, "config")
    
    def exists(self) -> bool:
        """Check if repository is initialized.
        
        Returns:
            True if .mygit directory exists
        """
        return os.path.exists(self.git_dir)
    
    def init(self, initial_branch: str = "main") -> None:
        """Initialize a new repository.
        
        Creates .mygit directory structure:
        - objects/: Object storage
        - refs/heads/: Branch references
        - HEAD: Current branch pointer
        - config: Repository configuration
        
        Args:
            initial_branch: Name of initial branch (default: 'main')
        """
        if self.exists():
            raise ValueError(f"Repository already exists at {self.root_path}")
        
        # Create directory structure
        ensure_dir(self.git_dir)
        ensure_dir(self.objects_dir)
        ensure_dir(self.heads_dir)
        
        # Initialize HEAD to point to main branch
        write_file(self.head_file, f"ref: refs/heads/{initial_branch}")
        
        # Create initial config
        config = {
            "user": {
                "name": os.environ.get("GIT_AUTHOR_NAME", "Your Name"),
                "email": os.environ.get("GIT_AUTHOR_EMAIL", "you@example.com")
            }
        }
        write_file(self.config_file, json.dumps(config, indent=2))
        
        # Create empty index
        write_file(self.index_file, json.dumps({}))
    
    def get_object_path(self, obj_hash: str) -> str:
        """Get filesystem path for an object.
        
        Uses Git's directory sharding: objects/XX/YYYYYYYY...
        
        Args:
            obj_hash: 40-character SHA-1 hash
            
        Returns:
            Full path to object file
        """
        return os.path.join(self.objects_dir, obj_hash[:2], obj_hash[2:])
    
    def write_object(self, obj: GitObject) -> str:
        """Write object to storage.
        
        Args:
            obj: GitObject to store
            
        Returns:
            SHA-1 hash of stored object
        """
        obj_hash = obj.compute_hash()
        obj_path = self.get_object_path(obj_hash)
        
        # Skip if object already exists (deduplication)
        if os.path.exists(obj_path):
            return obj_hash
        
        # Write compressed object
        write_file(obj_path, obj.compress(), binary=True)
        return obj_hash
    
    def read_object(self, obj_hash: str) -> GitObject:
        """Read object from storage.
        
        Args:
            obj_hash: SHA-1 hash of object
            
        Returns:
            Reconstructed GitObject
        """
        obj_path = self.get_object_path(obj_hash)
        
        if not os.path.exists(obj_path):
            raise ValueError(f"Object {obj_hash} not found")
        
        compressed_data = read_file(obj_path, binary=True)
        return GitObject.decompress(compressed_data)
    
    def object_exists(self, obj_hash: str) -> bool:
        """Check if object exists in storage.
        
        Args:
            obj_hash: SHA-1 hash of object
            
        Returns:
            True if object exists
        """
        return os.path.exists(self.get_object_path(obj_hash))
    
    def list_objects(self) -> List[str]:
        """List all object hashes in repository.
        
        Returns:
            List of SHA-1 hashes
        """
        objects = []
        if not os.path.exists(self.objects_dir):
            return objects
        
        for dir_name in os.listdir(self.objects_dir):
            dir_path = os.path.join(self.objects_dir, dir_name)
            if os.path.isdir(dir_path) and len(dir_name) == 2:
                for file_name in os.listdir(dir_path):
                    objects.append(dir_name + file_name)
        
        return objects
    
    def get_head(self) -> str:
        """Get current HEAD reference.
        
        Returns:
            Branch reference (e.g., 'refs/heads/main') or commit hash
        """
        if not os.path.exists(self.head_file):
            raise ValueError("HEAD file not found")
        
        return read_file(self.head_file).strip()
    
    def set_head(self, ref: str) -> None:
        """Set HEAD to a reference or commit.
        
        Args:
            ref: Branch reference or commit hash
        """
        write_file(self.head_file, ref)
    
    def get_branch_commit(self, branch_name: str) -> Optional[str]:
        """Get commit hash that a branch points to.
        
        Args:
            branch_name: Branch name (without refs/heads/)
            
        Returns:
            Commit hash or None if branch doesn't exist
        """
        branch_file = os.path.join(self.heads_dir, branch_name)
        if not os.path.exists(branch_file):
            return None
        
        return read_file(branch_file).strip()
    
    def set_branch_commit(self, branch_name: str, commit_hash: str) -> None:
        """Update branch to point to a commit.
        
        Args:
            branch_name: Branch name (without refs/heads/)
            commit_hash: Commit hash to point to
        """
        branch_file = os.path.join(self.heads_dir, branch_name)
        write_file(branch_file, commit_hash)
    
    def list_branches(self) -> List[str]:
        """List all branches.
        
        Returns:
            List of branch names
        """
        if not os.path.exists(self.heads_dir):
            return []
        
        return [f for f in os.listdir(self.heads_dir) if os.path.isfile(os.path.join(self.heads_dir, f))]
    
    def get_current_branch(self) -> Optional[str]:
        """Get current branch name.
        
        Returns:
            Branch name or None if in detached HEAD state
        """
        head = self.get_head()
        if head.startswith("ref: refs/heads/"):
            return head[16:]  # Remove 'ref: refs/heads/' prefix
        return None  # Detached HEAD
    
    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash.
        
        Returns:
            Commit hash or None if no commits yet
        """
        head = self.get_head()
        
        # If HEAD points to a branch
        if head.startswith("ref: refs/heads/"):
            branch_name = head[16:]
            return self.get_branch_commit(branch_name)
        else:
            # Detached HEAD - HEAD contains commit hash
            return head if self.object_exists(head) else None
    
    def get_config(self) -> Dict:
        """Get repository configuration.
        
        Returns:
            Configuration dictionary
        """
        if os.path.exists(self.config_file):
            return json.loads(read_file(self.config_file))
        return {}
    
    def update_config(self, updates: Dict) -> None:
        """Update repository configuration.
        
        Args:
            updates: Dictionary of configuration updates
        """
        config = self.get_config()
        config.update(updates)
        write_file(self.config_file, json.dumps(config, indent=2))
    
    def get_ignore_patterns(self) -> List[str]:
        """Get ignore patterns from .mygitignore.
        
        Returns:
            List of ignore patterns
        """
        ignore_file = os.path.join(self.root_path, ".mygitignore")
        if not os.path.exists(ignore_file):
            return []
        
        patterns = []
        for line in read_file(ignore_file).splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                patterns.append(line)
        
        return patterns
    
    @staticmethod
    def find_repo(path: str = ".") -> Optional['Repository']:
        """Find repository by searching up directory tree.
        
        Args:
            path: Starting path
            
        Returns:
            Repository instance or None if not found
        """
        current = os.path.abspath(path)
        
        while True:
            repo = Repository(current)
            if repo.exists():
                return repo
            
            parent = os.path.dirname(current)
            if parent == current:  # Reached root
                return None
            current = parent
    
    def __repr__(self) -> str:
        branch = self.get_current_branch()
        if branch:
            return f"<Repository at {self.root_path} on branch '{branch}'>"
        return f"<Repository at {self.root_path}>"
