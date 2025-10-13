"""
Stats command - Show repository statistics and performance metrics.

Usage: mygit stats
"""

import click
import os
import time
from colorama import Fore, Style
from tabulate import tabulate
from collections import Counter

from core.repository import Repository
from core.objects import GitObject, Blob, Tree, Commit


@click.command()
def stats_command():
    """Show repository statistics and performance metrics."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}MyGit Repository Statistics{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        # Repository info
        current_branch = repo.get_current_branch()
        current_commit = repo.get_current_commit()
        
        click.echo(f"{Fore.GREEN}Repository Information:{Style.RESET_ALL}")
        click.echo(f"  Location: {repo.root_path}")
        click.echo(f"  Current Branch: {Fore.CYAN}{current_branch or 'detached HEAD'}{Style.RESET_ALL}")
        if current_commit:
            click.echo(f"  HEAD Commit: {current_commit[:7]}")
        click.echo()
        
        # Object statistics
        click.echo(f"{Fore.GREEN}Object Storage:{Style.RESET_ALL}")
        
        object_hashes = repo.list_objects()
        object_types = Counter()
        total_size = 0
        compressed_size = 0
        
        for obj_hash in object_hashes:
            obj_path = repo.get_object_path(obj_hash)
            compressed_size += os.path.getsize(obj_path)
            
            try:
                obj = repo.read_object(obj_hash)
                object_types[obj.type] += 1
                total_size += len(obj.serialize())
            except Exception:
                pass
        
        click.echo(f"  Total Objects: {len(object_hashes)}")
        click.echo(f"  Blobs: {object_types.get('blob', 0)}")
        click.echo(f"  Trees: {object_types.get('tree', 0)}")
        click.echo(f"  Commits: {object_types.get('commit', 0)}")
        click.echo()
        
        # Storage efficiency
        click.echo(f"{Fore.GREEN}Storage Efficiency:{Style.RESET_ALL}")
        click.echo(f"  Uncompressed Size: {_format_size(total_size)}")
        click.echo(f"  Compressed Size: {_format_size(compressed_size)}")
        
        if total_size > 0:
            compression_ratio = (1 - compressed_size / total_size) * 100
            click.echo(f"  Compression Ratio: {Fore.CYAN}{compression_ratio:.1f}%{Style.RESET_ALL}")
        click.echo()
        
        # Branch information
        branches = repo.list_branches()
        click.echo(f"{Fore.GREEN}Branches:{Style.RESET_ALL}")
        click.echo(f"  Total: {len(branches)}")
        
        if branches:
            branch_data = []
            for branch in branches[:5]:  # Show first 5
                commit_hash = repo.get_branch_commit(branch)
                if commit_hash:
                    commit = repo.read_object(commit_hash)
                    if isinstance(commit, Commit):
                        marker = "*" if branch == current_branch else " "
                        branch_data.append([
                            marker,
                            branch,
                            commit_hash[:7],
                            commit.get_summary()[:40]
                        ])
            
            if branch_data:
                click.echo()
                click.echo(tabulate(
                    branch_data,
                    headers=["", "Branch", "Commit", "Message"],
                    tablefmt="simple"
                ))
        click.echo()
        
        # Commit statistics
        if current_commit:
            click.echo(f"{Fore.GREEN}Commit History:{Style.RESET_ALL}")
            
            commit_count = 0
            commit_hash = current_commit
            visited = set()
            authors = Counter()
            
            while commit_hash and commit_hash not in visited:
                visited.add(commit_hash)
                commit = repo.read_object(commit_hash)
                
                if isinstance(commit, Commit):
                    commit_count += 1
                    authors[commit.author] += 1
                    
                    if commit.parent_hashes:
                        commit_hash = commit.parent_hashes[0]
                    else:
                        commit_hash = None
                else:
                    break
            
            click.echo(f"  Total Commits: {commit_count}")
            click.echo(f"  Contributors: {len(authors)}")
            
            if authors:
                click.echo(f"\n  Top Contributors:")
                for author, count in authors.most_common(3):
                    click.echo(f"    {author}: {count} commits")
            click.echo()
        
        # Performance metrics
        click.echo(f"{Fore.GREEN}Performance Metrics:{Style.RESET_ALL}")
        
        # Test object read performance
        if object_hashes:
            test_hash = object_hashes[0]
            iterations = 10
            
            start_time = time.time()
            for _ in range(iterations):
                repo.read_object(test_hash)
            elapsed = (time.time() - start_time) / iterations * 1000
            
            click.echo(f"  Object Read Time: {elapsed:.2f}ms (avg)")
        
        # Test hash computation
        test_data = b"Hello, MyGit!" * 100
        iterations = 100
        
        start_time = time.time()
        for _ in range(iterations):
            import hashlib
            hashlib.sha1(test_data).hexdigest()
        elapsed = (time.time() - start_time) / iterations * 1000
        
        click.echo(f"  SHA-1 Hash Time: {elapsed:.3f}ms (avg)")
        click.echo()
        
        # File distribution
        if current_commit:
            commit = repo.read_object(current_commit)
            if isinstance(commit, Commit):
                files = _count_tree_files(repo, commit.tree_hash)
                click.echo(f"{Fore.GREEN}Working Tree:{Style.RESET_ALL}")
                click.echo(f"  Total Files: {files}")
                click.echo()
        
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()


def _format_size(bytes_size: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def _count_tree_files(repo: Repository, tree_hash: str) -> int:
    """Count files in a tree recursively."""
    from core.objects import Tree
    
    count = 0
    tree = repo.read_object(tree_hash)
    
    if not isinstance(tree, Tree):
        return 0
    
    for entry in tree.entries:
        if entry.mode == "040000":  # Directory
            count += _count_tree_files(repo, entry.hash)
        else:
            count += 1
    
    return count
