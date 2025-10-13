"""
Merge command - Join two or more development histories together.

Usage: mygit merge <branch-name>
       mygit merge <branch-name> --interactive
"""

import click
import os
from colorama import Fore, Style
from typing import Dict, List, Tuple, Optional

from core.repository import Repository
from core.index import Index
from core.objects import Commit, Tree, Blob
from utils.fileops import write_file, read_file


@click.command()
@click.argument('branch_name')
@click.option('--interactive', '-i', is_flag=True, help='Interactive conflict resolution')
def merge_command(branch_name, interactive):
    """Merge a branch into the current branch."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        # Get current branch and commit
        current_branch = repo.get_current_branch()
        if current_branch is None:
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Cannot merge in detached HEAD state", err=True)
            raise click.Abort()
        
        current_commit_hash = repo.get_current_commit()
        if current_commit_hash is None:
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} No commits yet", err=True)
            raise click.Abort()
        
        # Get target branch commit
        target_commit_hash = repo.get_branch_commit(branch_name)
        if target_commit_hash is None:
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Branch '{branch_name}' not found", err=True)
            raise click.Abort()
        
        if current_commit_hash == target_commit_hash:
            click.echo(f"{Fore.GREEN}Already up to date.{Style.RESET_ALL}")
            return
        
        # Check for uncommitted changes
        index = Index(repo)
        if not index.is_empty():
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} You have uncommitted changes", err=True)
            raise click.Abort()
        
        # Read commits
        current_commit = repo.read_object(current_commit_hash)
        target_commit = repo.read_object(target_commit_hash)
        
        # Check for fast-forward merge
        if _is_ancestor(repo, target_commit_hash, current_commit_hash):
            click.echo(f"{Fore.GREEN}Already up to date.{Style.RESET_ALL}")
            return
        
        if _is_ancestor(repo, current_commit_hash, target_commit_hash):
            # Fast-forward merge
            click.echo(f"{Fore.GREEN}Fast-forward merge{Style.RESET_ALL}")
            repo.set_branch_commit(current_branch, target_commit_hash)
            
            # Update working directory
            _update_working_dir(repo, target_commit)
            
            click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Merged {Fore.CYAN}{branch_name}{Style.RESET_ALL} into {Fore.CYAN}{current_branch}{Style.RESET_ALL}")
            return
        
        # Three-way merge needed
        click.echo(f"{Fore.YELLOW}Performing three-way merge...{Style.RESET_ALL}")
        
        # Find common ancestor
        ancestor_hash = _find_common_ancestor(repo, current_commit_hash, target_commit_hash)
        if ancestor_hash is None:
            click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} No common ancestor found", err=True)
            raise click.Abort()
        
        ancestor_commit = repo.read_object(ancestor_hash)
        
        # Get file trees
        current_files = _get_tree_files(repo, current_commit.tree_hash)
        target_files = _get_tree_files(repo, target_commit.tree_hash)
        ancestor_files = _get_tree_files(repo, ancestor_commit.tree_hash)
        
        # Perform merge
        conflicts = _merge_files(repo, current_files, target_files, ancestor_files, interactive)
        
        if conflicts:
            click.echo(f"\n{Fore.RED}Merge conflicts detected in {len(conflicts)} file(s):{Style.RESET_ALL}")
            for filepath in conflicts:
                click.echo(f"  {Fore.RED}✗{Style.RESET_ALL} {filepath}")
            click.echo(f"\n{Fore.YELLOW}Resolve conflicts and run 'mygit commit'{Style.RESET_ALL}")
        else:
            # Auto-commit merge
            from datetime import datetime
            config = repo.get_config()
            
            merge_commit = Commit(
                tree_hash=_create_tree_from_working_dir(repo),
                parent_hashes=[current_commit_hash, target_commit_hash],
                author=config.get('user', {}).get('name', 'Unknown'),
                email=config.get('user', {}).get('email', 'unknown@example.com'),
                message=f"Merge branch '{branch_name}' into {current_branch}",
                timestamp=datetime.now()
            )
            
            commit_hash = repo.write_object(merge_commit)
            repo.set_branch_commit(current_branch, commit_hash)
            
            click.echo(f"\n{Fore.GREEN}✓{Style.RESET_ALL} Merged {Fore.CYAN}{branch_name}{Style.RESET_ALL} into {Fore.CYAN}{current_branch}{Style.RESET_ALL}")
            click.echo(f"  Merge commit: {Fore.CYAN}{commit_hash[:7]}{Style.RESET_ALL}")
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()


def _is_ancestor(repo: Repository, ancestor_hash: str, commit_hash: str) -> bool:
    """Check if ancestor_hash is an ancestor of commit_hash."""
    current = commit_hash
    visited = set()
    
    while current and current not in visited:
        if current == ancestor_hash:
            return True
        
        visited.add(current)
        commit = repo.read_object(current)
        
        if isinstance(commit, Commit) and commit.parent_hashes:
            current = commit.parent_hashes[0]
        else:
            current = None
    
    return False


def _find_common_ancestor(repo: Repository, commit1_hash: str, commit2_hash: str) -> Optional[str]:
    """Find common ancestor of two commits."""
    # Get all ancestors of commit1
    ancestors1 = set()
    queue = [commit1_hash]
    
    while queue:
        current = queue.pop(0)
        if current in ancestors1:
            continue
        
        ancestors1.add(current)
        commit = repo.read_object(current)
        
        if isinstance(commit, Commit):
            queue.extend(commit.parent_hashes)
    
    # Find first common ancestor in commit2's history
    queue = [commit2_hash]
    visited = set()
    
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        
        if current in ancestors1:
            return current
        
        visited.add(current)
        commit = repo.read_object(current)
        
        if isinstance(commit, Commit):
            queue.extend(commit.parent_hashes)
    
    return None


def _get_tree_files(repo: Repository, tree_hash: str, prefix: str = "") -> Dict[str, str]:
    """Get all files from a tree recursively."""
    files = {}
    tree = repo.read_object(tree_hash)
    
    if not isinstance(tree, Tree):
        return files
    
    for entry in tree.entries:
        path = os.path.join(prefix, entry.name) if prefix else entry.name
        
        if entry.mode == "040000":  # Directory
            files.update(_get_tree_files(repo, entry.hash, path))
        else:  # File
            files[path] = entry.hash
    
    return files


def _merge_files(
    repo: Repository,
    current_files: Dict[str, str],
    target_files: Dict[str, str],
    ancestor_files: Dict[str, str],
    interactive: bool
) -> List[str]:
    """Merge file changes and return list of conflicted files."""
    conflicts = []
    all_paths = set(current_files.keys()) | set(target_files.keys()) | set(ancestor_files.keys())
    
    for filepath in all_paths:
        current_hash = current_files.get(filepath)
        target_hash = target_files.get(filepath)
        ancestor_hash = ancestor_files.get(filepath)
        
        full_path = os.path.join(repo.root_path, filepath)
        
        # Case 1: File unchanged in both branches
        if current_hash == target_hash:
            continue
        
        # Case 2: File only in target (added in target branch)
        if current_hash == ancestor_hash and target_hash:
            _checkout_file(repo, target_hash, full_path)
            continue
        
        # Case 3: File only in current (added in current branch)
        if target_hash == ancestor_hash and current_hash:
            continue
        
        # Case 4: File deleted in target
        if current_hash == ancestor_hash and target_hash is None:
            if os.path.exists(full_path):
                os.remove(full_path)
            continue
        
        # Case 5: File deleted in current
        if target_hash == ancestor_hash and current_hash is None:
            continue
        
        # Case 6: Conflict - file modified in both branches
        if current_hash and target_hash:
            if interactive:
                resolved = _interactive_conflict_resolution(repo, filepath, current_hash, target_hash, ancestor_hash)
                if not resolved:
                    conflicts.append(filepath)
            else:
                _create_conflict_markers(repo, filepath, current_hash, target_hash, ancestor_hash)
                conflicts.append(filepath)
        else:
            # One side added, other deleted
            conflicts.append(filepath)
    
    return conflicts


def _checkout_file(repo: Repository, blob_hash: str, filepath: str) -> None:
    """Checkout a single file from a blob."""
    blob = repo.read_object(blob_hash)
    if isinstance(blob, Blob):
        write_file(filepath, blob.get_content(), binary=True)


def _create_conflict_markers(
    repo: Repository,
    filepath: str,
    current_hash: str,
    target_hash: str,
    ancestor_hash: Optional[str]
) -> None:
    """Create conflict markers in file."""
    full_path = os.path.join(repo.root_path, filepath)
    
    current_blob = repo.read_object(current_hash)
    target_blob = repo.read_object(target_hash)
    
    current_content = current_blob.get_content().decode('utf-8', errors='replace')
    target_content = target_blob.get_content().decode('utf-8', errors='replace')
    
    conflict_content = f"""<<<<<<< HEAD
{current_content}=======
{target_content}>>>>>>> merge
"""
    
    write_file(full_path, conflict_content, binary=False)


def _interactive_conflict_resolution(
    repo: Repository,
    filepath: str,
    current_hash: str,
    target_hash: str,
    ancestor_hash: Optional[str]
) -> bool:
    """Interactive conflict resolution UI."""
    click.echo(f"\n{Fore.YELLOW}Conflict in: {filepath}{Style.RESET_ALL}")
    
    current_blob = repo.read_object(current_hash)
    target_blob = repo.read_object(target_hash)
    
    click.echo(f"\n{Fore.CYAN}Current branch (ours):{Style.RESET_ALL}")
    click.echo(current_blob.get_content().decode('utf-8', errors='replace')[:200])
    
    click.echo(f"\n{Fore.CYAN}Merging branch (theirs):{Style.RESET_ALL}")
    click.echo(target_blob.get_content().decode('utf-8', errors='replace')[:200])
    
    choice = click.prompt(
        "\nChoose resolution",
        type=click.Choice(['ours', 'theirs', 'edit', 'skip']),
        default='skip'
    )
    
    full_path = os.path.join(repo.root_path, filepath)
    
    if choice == 'ours':
        _checkout_file(repo, current_hash, full_path)
        return True
    elif choice == 'theirs':
        _checkout_file(repo, target_hash, full_path)
        return True
    elif choice == 'edit':
        _create_conflict_markers(repo, filepath, current_hash, target_hash, ancestor_hash)
        click.echo(f"{Fore.YELLOW}Edit the file manually and commit{Style.RESET_ALL}")
        return False
    else:  # skip
        _create_conflict_markers(repo, filepath, current_hash, target_hash, ancestor_hash)
        return False


def _update_working_dir(repo: Repository, commit: Commit) -> None:
    """Update working directory to match commit."""
    tree = repo.read_object(commit.tree_hash)
    _checkout_tree_recursive(repo, tree, repo.root_path)


def _checkout_tree_recursive(repo: Repository, tree: Tree, path: str, prefix: str = "") -> None:
    """Recursively checkout tree."""
    from utils.fileops import ensure_dir
    
    for entry in tree.entries:
        entry_path = os.path.join(path, prefix, entry.name) if prefix else os.path.join(path, entry.name)
        
        if entry.mode == "040000":
            ensure_dir(entry_path)
            subtree = repo.read_object(entry.hash)
            if isinstance(subtree, Tree):
                _checkout_tree_recursive(repo, subtree, path, os.path.join(prefix, entry.name) if prefix else entry.name)
        else:
            _checkout_file(repo, entry.hash, entry_path)


def _create_tree_from_working_dir(repo: Repository) -> str:
    """Create tree from current working directory."""
    index = Index(repo)
    
    # Add all files to index
    from utils.fileops import list_files_recursive
    all_files = list_files_recursive(repo.root_path, exclude_dirs=['.mygit'])
    
    for filepath in all_files:
        try:
            index.add_file(filepath)
        except Exception:
            pass
    
    tree = index.create_tree()
    return repo.write_object(tree)
