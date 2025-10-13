"""
Unit tests for Git objects (Blob, Tree, Commit).
"""

import pytest
from datetime import datetime

from core.objects import Blob, Tree, TreeEntry, Commit, GitObject


class TestBlob:
    """Test Blob object functionality."""
    
    def test_blob_creation(self):
        """Test creating a blob from content."""
        content = b"Hello, MyGit!"
        blob = Blob(content)
        
        assert blob.type == "blob"
        assert blob.get_content() == content
    
    def test_blob_serialization(self):
        """Test blob serialization format."""
        content = b"Test content"
        blob = Blob(content)
        serialized = blob.serialize()
        
        expected = b"blob 12\x00Test content"
        assert serialized == expected
    
    def test_blob_hash_consistency(self):
        """Test that same content produces same hash."""
        content = b"Same content"
        blob1 = Blob(content)
        blob2 = Blob(content)
        
        assert blob1.compute_hash() == blob2.compute_hash()
    
    def test_blob_hash_uniqueness(self):
        """Test that different content produces different hash."""
        blob1 = Blob(b"Content A")
        blob2 = Blob(b"Content B")
        
        assert blob1.compute_hash() != blob2.compute_hash()
    
    def test_blob_compression(self):
        """Test blob compression."""
        content = b"A" * 1000  # Repetitive content compresses well
        blob = Blob(content)
        
        compressed = blob.compress()
        assert len(compressed) < len(blob.serialize())
    
    def test_blob_decompression(self):
        """Test blob decompression round-trip."""
        content = b"Test decompression"
        blob = Blob(content)
        
        compressed = blob.compress()
        restored = GitObject.decompress(compressed)
        
        assert isinstance(restored, Blob)
        assert restored.get_content() == content


class TestTree:
    """Test Tree object functionality."""
    
    def test_tree_creation(self):
        """Test creating a tree with entries."""
        entries = [
            TreeEntry("100644", "file1.txt", "a" * 40),
            TreeEntry("100644", "file2.txt", "b" * 40),
        ]
        tree = Tree(entries)
        
        assert tree.type == "tree"
        assert len(tree.entries) == 2
    
    def test_tree_entry_sorting(self):
        """Test that tree entries are sorted by name."""
        entries = [
            TreeEntry("100644", "zebra.txt", "a" * 40),
            TreeEntry("100644", "apple.txt", "b" * 40),
        ]
        tree = Tree(entries)
        
        assert tree.entries[0].name == "apple.txt"
        assert tree.entries[1].name == "zebra.txt"
    
    def test_tree_find_entry(self):
        """Test finding entry by name."""
        entries = [
            TreeEntry("100644", "README.md", "a" * 40),
            TreeEntry("040000", "src", "b" * 40),
        ]
        tree = Tree(entries)
        
        entry = tree.find_entry("README.md")
        assert entry is not None
        assert entry.name == "README.md"
        
        assert tree.find_entry("nonexistent") is None
    
    def test_tree_serialization(self):
        """Test tree serialization format."""
        entries = [
            TreeEntry("100644", "test.txt", "a" * 40),
        ]
        tree = Tree(entries)
        
        serialized = tree.serialize()
        assert b"tree " in serialized
        assert b"100644 test.txt\x00" in serialized


class TestCommit:
    """Test Commit object functionality."""
    
    def test_commit_creation(self):
        """Test creating a commit."""
        commit = Commit(
            tree_hash="a" * 40,
            parent_hashes=["b" * 40],
            author="Test Author",
            email="test@example.com",
            message="Test commit",
            timestamp=datetime(2025, 10, 14, 10, 0, 0)
        )
        
        assert commit.type == "commit"
        assert commit.tree_hash == "a" * 40
        assert len(commit.parent_hashes) == 1
        assert commit.author == "Test Author"
    
    def test_commit_initial_no_parent(self):
        """Test initial commit without parent."""
        commit = Commit(
            tree_hash="a" * 40,
            parent_hashes=[],
            author="Test Author",
            email="test@example.com",
            message="Initial commit"
        )
        
        assert len(commit.parent_hashes) == 0
    
    def test_commit_get_summary(self):
        """Test getting commit summary (first line)."""
        commit = Commit(
            tree_hash="a" * 40,
            parent_hashes=[],
            author="Test",
            email="test@example.com",
            message="First line\nSecond line\nThird line"
        )
        
        assert commit.get_summary() == "First line"
    
    def test_commit_short_hash(self):
        """Test getting short hash."""
        commit = Commit(
            tree_hash="a" * 40,
            parent_hashes=[],
            author="Test",
            email="test@example.com",
            message="Test"
        )
        
        full_hash = commit.compute_hash()
        short = commit.get_short_hash(7)
        
        assert len(short) == 7
        assert full_hash.startswith(short)
    
    def test_commit_serialization(self):
        """Test commit serialization format."""
        commit = Commit(
            tree_hash="a" * 40,
            parent_hashes=["b" * 40],
            author="Test",
            email="test@example.com",
            message="Test commit",
            timestamp=datetime(2025, 10, 14, 10, 0, 0)
        )
        
        serialized = commit.serialize()
        content = serialized.split(b"\x00", 1)[1].decode()
        
        assert "tree " + "a" * 40 in content
        assert "parent " + "b" * 40 in content
        assert "author Test" in content
        assert "Test commit" in content


class TestObjectRoundTrip:
    """Test serialization/deserialization round-trips."""
    
    def test_blob_roundtrip(self):
        """Test blob serialize -> deserialize."""
        original = Blob(b"Round trip test")
        serialized = original.serialize()
        restored = GitObject.deserialize(serialized)
        
        assert isinstance(restored, Blob)
        assert restored.get_content() == original.get_content()
        assert restored.compute_hash() == original.compute_hash()
    
    def test_tree_roundtrip(self):
        """Test tree serialize -> deserialize."""
        entries = [
            TreeEntry("100644", "file.txt", "a" * 40),
            TreeEntry("040000", "dir", "b" * 40),
        ]
        original = Tree(entries)
        serialized = original.serialize()
        restored = GitObject.deserialize(serialized)
        
        assert isinstance(restored, Tree)
        assert len(restored.entries) == len(original.entries)
        assert restored.compute_hash() == original.compute_hash()
    
    def test_commit_roundtrip(self):
        """Test commit serialize -> deserialize."""
        original = Commit(
            tree_hash="a" * 40,
            parent_hashes=["b" * 40],
            author="Test",
            email="test@example.com",
            message="Round trip commit"
        )
        serialized = original.serialize()
        restored = GitObject.deserialize(serialized)
        
        assert isinstance(restored, Commit)
        assert restored.tree_hash == original.tree_hash
        assert restored.author == original.author
        assert restored.message == original.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
