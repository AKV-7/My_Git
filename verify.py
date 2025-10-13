"""
Quick verification script to test MyGit installation.

Run this to verify that all core components are working.
"""

import sys


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from core.objects import Blob, Tree, Commit
        from core.repository import Repository
        from core.index import Index
        from utils.hash import hash_object
        from utils.fileops import ensure_dir
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_blob_creation():
    """Test blob object creation."""
    print("\nTesting Blob creation...")
    
    try:
        from core.objects import Blob
        
        content = b"Hello, MyGit!"
        blob = Blob(content)
        
        assert blob.type == "blob"
        assert blob.get_content() == content
        assert len(blob.compute_hash()) == 40  # SHA-1 hash length
        
        print(f"✅ Blob created with hash: {blob.compute_hash()[:7]}")
        return True
    except Exception as e:
        print(f"❌ Blob test failed: {e}")
        return False


def test_tree_creation():
    """Test tree object creation."""
    print("\nTesting Tree creation...")
    
    try:
        from core.objects import Tree, TreeEntry
        
        entries = [
            TreeEntry("100644", "file1.txt", "a" * 40),
            TreeEntry("100644", "file2.txt", "b" * 40),
        ]
        tree = Tree(entries)
        
        assert tree.type == "tree"
        assert len(tree.entries) == 2
        
        print(f"✅ Tree created with hash: {tree.compute_hash()[:7]}")
        return True
    except Exception as e:
        print(f"❌ Tree test failed: {e}")
        return False


def test_commit_creation():
    """Test commit object creation."""
    print("\nTesting Commit creation...")
    
    try:
        from core.objects import Commit
        from datetime import datetime
        
        commit = Commit(
            tree_hash="a" * 40,
            parent_hashes=[],
            author="Test User",
            email="test@example.com",
            message="Test commit",
            timestamp=datetime.now()
        )
        
        assert commit.type == "commit"
        assert commit.author == "Test User"
        
        print(f"✅ Commit created with hash: {commit.compute_hash()[:7]}")
        return True
    except Exception as e:
        print(f"❌ Commit test failed: {e}")
        return False


def test_hash_consistency():
    """Test that hashing is consistent."""
    print("\nTesting hash consistency...")
    
    try:
        from core.objects import Blob
        
        content = b"Same content"
        blob1 = Blob(content)
        blob2 = Blob(content)
        
        hash1 = blob1.compute_hash()
        hash2 = blob2.compute_hash()
        
        assert hash1 == hash2, "Same content should produce same hash"
        
        print(f"✅ Hash consistency verified: {hash1[:7]}")
        return True
    except Exception as e:
        print(f"❌ Hash consistency test failed: {e}")
        return False


def test_compression():
    """Test compression/decompression."""
    print("\nTesting compression...")
    
    try:
        from core.objects import Blob, GitObject
        
        content = b"A" * 1000  # Repetitive content
        blob = Blob(content)
        
        compressed = blob.compress()
        restored = GitObject.decompress(compressed)
        
        assert isinstance(restored, Blob)
        assert restored.get_content() == content
        
        ratio = (1 - len(compressed) / len(blob.serialize())) * 100
        print(f"✅ Compression works: {ratio:.1f}% compression ratio")
        return True
    except Exception as e:
        print(f"❌ Compression test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("MyGit Installation Verification")
    print("="*60)
    
    tests = [
        test_imports,
        test_blob_creation,
        test_tree_creation,
        test_commit_creation,
        test_hash_consistency,
        test_compression,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)
    
    if all(results):
        print("\n🎉 All tests passed! MyGit is ready to use.")
        print("\nNext steps:")
        print("  1. Run: python demo.py")
        print("  2. Or try: mygit init")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("  1. Make sure you're in the project root directory")
        print("  2. Run: pip install -r requirements.txt")
        print("  3. Run: pip install -e .")
        return 1


if __name__ == "__main__":
    sys.exit(main())
