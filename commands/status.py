"""
Status command - Show working tree status.

Usage: mygit status
"""

import click
import os
from colorama import Fore, Style
from typing import Set, Dict

from core.repository import Repository
from core.index import Index
from core.objects import Commit, Tree, TreeEntry
from utils.fileops import list_files_recursive, match_gitignore_pattern


@click.command()
def status_command():
    """Show the working tree status."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        # Get current branch
        current_branch = repo.get_current_branch()
        current_commit = repo.get_current_commit()
        
        # Header
        if current_branch:
            click.echo(f"On branch {Fore.CYAN}{current_branch}{Style.RESET_ALL}")
        else:
            click.echo(f"HEAD detached at {Fore.CYAN}{current_commit[:7] if current_commit else 'unknown'}{Style.RESET_ALL}")
        
        if current_commit is None:
            click.echo("\nNo commits yet")
        
        click.echo()
        
        # Load index
        index = Index(repo)
        
        # Get staged files
        staged_files = set(index.get_staged_files())
        
        # Get committed files from last commit
        committed_files: Dict[str, str] = {}
        if current_commit:
            commit = repo.read_object(current_commit)
            if isinstance(commit, Commit):
                tree = repo.read_object(commit.tree_hash)
                committed_files = _get_tree_files(repo, tree)
        
        # Get all working directory files
        ignore_patterns = repo.get_ignore_patterns()
        ignore_patterns.append('.mygit/')
        
        all_files = list_files_recursive(repo.root_path, exclude_dirs=['.mygit'])
        working_files = {
            f for f in all_files 
            if not any(match_gitignore_pattern(f, p) for p in ignore_patterns)
        }
        
        # Categorize files
        staged = []
        modified = []
        deleted = []
        untracked = []
        
        # Check staged files
        for filepath in staged_files:
            if filepath not in committed_files:
                staged.append(('new file', filepath))
            else:
                # Check if modified from last commit
                index_entry = index.get_entry(filepath)
                if index_entry and index_entry.hash != committed_files[filepath]:
                    staged.append(('modified', filepath))
        
        # Check working directory files
        for filepath in working_files:
            if filepath in staged_files:
                # Check if modified after staging
                full_path = os.path.join(repo.root_path, filepath)
                if os.path.exists(full_path):
                    from core.objects import Blob
                    current_blob = Blob.from_file(full_path)
                    current_hash = current_blob.compute_hash()
                    
                    index_entry = index.get_entry(filepath)
                    if index_entry and current_hash != index_entry.hash:
                        modified.append(filepath)
            elif filepath in committed_files:
                # Modified but not staged
                full_path = os.path.join(repo.root_path, filepath)
                from core.objects import Blob
                current_blob = Blob.from_file(full_path)
                current_hash = current_blob.compute_hash()
                
                if current_hash != committed_files[filepath]:
                    modified.append(filepath)
            else:
                # Untracked file
                untracked.append(filepath)
        
        # Check for deleted files
        for filepath in committed_files:
            full_path = os.path.join(repo.root_path, filepath)
            if not os.path.exists(full_path):
                if filepath in staged_files:
                    staged.append(('deleted', filepath))
                else:
                    deleted.append(filepath)
        
        # Display results
        if staged:
            click.echo(f"{Fore.GREEN}Changes to be committed:{Style.RESET_ALL}")
            click.echo(f"  (use \"mygit reset <file>...\" to unstage)")
            click.echo()
            for status, filepath in staged:
                color = Fore.GREEN
                click.echo(f"  {color}{status:12}{Style.RESET_ALL} {filepath}")
            click.echo()
        
        if modified or deleted:
            click.echo(f"{Fore.RED}Changes not staged for commit:{Style.RESET_ALL}")
            click.echo(f"  (use \"mygit add <file>...\" to update what will be committed)")
            click.echo()
            for filepath in modified:
                click.echo(f"  {Fore.RED}modified:    {Style.RESET_ALL} {filepath}")
            for filepath in deleted:
                click.echo(f"  {Fore.RED}deleted:     {Style.RESET_ALL} {filepath}")
            click.echo()
        
        if untracked:
            click.echo(f"{Fore.RED}Untracked files:{Style.RESET_ALL}")
            click.echo(f"  (use \"mygit add <file>...\" to include in what will be committed)")
            click.echo()
            for filepath in untracked[:10]:  # Show first 10
                click.echo(f"  {Fore.RED}{filepath}{Style.RESET_ALL}")
            if len(untracked) > 10:
                click.echo(f"  ... and {len(untracked) - 10} more")
            click.echo()
        
        if not staged and not modified and not deleted and not untracked:
            click.echo(f"{Fore.GREEN}Nothing to commit, working tree clean{Style.RESET_ALL}")
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()


def _get_tree_files(repo: Repository, tree: Tree, prefix: str = "") -> Dict[str, str]:
    """Recursively get all files from a tree.
    
    Args:
        repo: Repository instance
        tree: Tree object
        prefix: Path prefix for nested trees
        
    Returns:
        Dictionary of path -> blob hash
    """
    files = {}
    
    for entry in tree.entries:
        path = os.path.join(prefix, entry.name) if prefix else entry.name
        
        if entry.mode == "040000":  # Directory
            subtree = repo.read_object(entry.hash)
            if isinstance(subtree, Tree):
                files.update(_get_tree_files(repo, subtree, path))
        else:  # File
            files[path] = entry.hash
    
    return files
