"""
Checkout command - Switch branches or restore files.

Usage: mygit checkout <branch-name>
       mygit checkout <commit-hash>
"""

import click
import os
from colorama import Fore, Style

from core.repository import Repository
from core.index import Index
from core.objects import Commit, Tree, Blob


@click.command()
@click.argument('target')
def checkout_command(target):
    """Switch branches or restore working tree files."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        # Check if target is a branch
        target_commit = repo.get_branch_commit(target)
        is_branch = target_commit is not None
        
        if not is_branch:
            # Try as commit hash
            if repo.object_exists(target):
                target_commit = target
            else:
                click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Branch or commit '{target}' not found", err=True)
                raise click.Abort()
        
        # Check for uncommitted changes
        index = Index(repo)
        if not index.is_empty():
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} You have uncommitted changes", err=True)
            click.echo("  Please commit or stash them before switching branches")
            raise click.Abort()
        
        # Read target commit
        commit = repo.read_object(target_commit)
        if not isinstance(commit, Commit):
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Invalid commit object", err=True)
            raise click.Abort()
        
        # Update working directory from tree
        tree = repo.read_object(commit.tree_hash)
        if not isinstance(tree, Tree):
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Invalid tree object", err=True)
            raise click.Abort()
        
        _checkout_tree(repo, tree, repo.root_path)
        
        # Update HEAD
        if is_branch:
            repo.set_head(f"ref: refs/heads/{target}")
            click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Switched to branch {Fore.CYAN}{target}{Style.RESET_ALL}")
        else:
            repo.set_head(target_commit)
            click.echo(f"{Fore.YELLOW}Note:{Style.RESET_ALL} You are in 'detached HEAD' state at {target_commit[:7]}")
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()


def _checkout_tree(repo: Repository, tree: Tree, path: str, prefix: str = "") -> None:
    """Recursively checkout tree contents to working directory.
    
    Args:
        repo: Repository instance
        tree: Tree object to checkout
        path: Base path for checkout
        prefix: Path prefix for nested trees
    """
    from utils.fileops import write_file, ensure_dir
    
    for entry in tree.entries:
        entry_path = os.path.join(path, prefix, entry.name) if prefix else os.path.join(path, entry.name)
        
        if entry.mode == "040000":  # Directory
            ensure_dir(entry_path)
            subtree = repo.read_object(entry.hash)
            if isinstance(subtree, Tree):
                _checkout_tree(repo, subtree, path, os.path.join(prefix, entry.name) if prefix else entry.name)
        else:  # File
            blob = repo.read_object(entry.hash)
            if isinstance(blob, Blob):
                write_file(entry_path, blob.get_content(), binary=True)
                
                # Set permissions if executable
                if entry.mode == "100755":
                    os.chmod(entry_path, 0o755)
