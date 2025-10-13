"""
Diff command - Show changes between commits, commit and working tree, etc.

Usage: mygit diff
       mygit diff --staged
       mygit diff <commit1> <commit2>
"""

import click
import os
from colorama import Fore, Style
from difflib import unified_diff

from core.repository import Repository
from core.index import Index
from core.objects import Commit, Blob


@click.command()
@click.option('--staged', is_flag=True, help='Show staged changes')
@click.argument('commits', nargs=-1)
def diff_command(staged, commits):
    """Show changes between commits or working tree."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        if len(commits) == 2:
            # Diff between two commits
            _diff_commits(repo, commits[0], commits[1])
        elif len(commits) == 1:
            # Diff between commit and working tree
            _diff_commit_working(repo, commits[0])
        elif staged:
            # Diff between staged and last commit
            _diff_staged(repo)
        else:
            # Diff between working tree and staged
            _diff_working_staged(repo)
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()


def _diff_commits(repo: Repository, commit1_hash: str, commit2_hash: str) -> None:
    """Show diff between two commits."""
    commit1 = repo.read_object(commit1_hash)
    commit2 = repo.read_object(commit2_hash)
    
    if not isinstance(commit1, Commit) or not isinstance(commit2, Commit):
        raise ValueError("Invalid commit hash")
    
    files1 = _get_commit_files(repo, commit1.tree_hash)
    files2 = _get_commit_files(repo, commit2.tree_hash)
    
    _show_diffs(repo, files1, files2, commit1_hash[:7], commit2_hash[:7])


def _diff_staged(repo: Repository) -> None:
    """Show diff between staged and last commit."""
    current_commit_hash = repo.get_current_commit()
    
    if current_commit_hash is None:
        click.echo(f"{Fore.YELLOW}No commits yet{Style.RESET_ALL}")
        return
    
    commit = repo.read_object(current_commit_hash)
    committed_files = _get_commit_files(repo, commit.tree_hash)
    
    index = Index(repo)
    staged_files = {entry.path: entry.hash for entry in index.get_all_entries().values()}
    
    _show_diffs(repo, committed_files, staged_files, "HEAD", "staged")


def _diff_working_staged(repo: Repository) -> None:
    """Show diff between working directory and staged."""
    index = Index(repo)
    staged_files = {entry.path: entry.hash for entry in index.get_all_entries().values()}
    
    working_files = {}
    for filepath in staged_files.keys():
        full_path = os.path.join(repo.root_path, filepath)
        if os.path.exists(full_path):
            blob = Blob.from_file(full_path)
            working_files[filepath] = blob.compute_hash()
    
    _show_diffs(repo, staged_files, working_files, "staged", "working")


def _diff_commit_working(repo: Repository, commit_hash: str) -> None:
    """Show diff between commit and working directory."""
    commit = repo.read_object(commit_hash)
    if not isinstance(commit, Commit):
        raise ValueError("Invalid commit hash")
    
    committed_files = _get_commit_files(repo, commit.tree_hash)
    
    working_files = {}
    from utils.fileops import list_files_recursive
    all_files = list_files_recursive(repo.root_path, exclude_dirs=['.mygit'])
    
    for filepath in all_files:
        full_path = os.path.join(repo.root_path, filepath)
        blob = Blob.from_file(full_path)
        working_files[filepath] = blob.compute_hash()
    
    _show_diffs(repo, committed_files, working_files, commit_hash[:7], "working")


def _get_commit_files(repo: Repository, tree_hash: str, prefix: str = "") -> dict:
    """Get all files from a tree recursively."""
    from core.objects import Tree
    
    files = {}
    tree = repo.read_object(tree_hash)
    
    if not isinstance(tree, Tree):
        return files
    
    for entry in tree.entries:
        path = os.path.join(prefix, entry.name) if prefix else entry.name
        
        if entry.mode == "040000":
            files.update(_get_commit_files(repo, entry.hash, path))
        else:
            files[path] = entry.hash
    
    return files


def _show_diffs(repo: Repository, files1: dict, files2: dict, label1: str, label2: str) -> None:
    """Show diffs between two file sets."""
    all_files = set(files1.keys()) | set(files2.keys())
    
    has_changes = False
    
    for filepath in sorted(all_files):
        hash1 = files1.get(filepath)
        hash2 = files2.get(filepath)
        
        if hash1 == hash2:
            continue
        
        has_changes = True
        
        click.echo(f"\n{Fore.YELLOW}diff --mygit a/{filepath} b/{filepath}{Style.RESET_ALL}")
        
        # Get content
        content1_lines = []
        content2_lines = []
        
        if hash1:
            blob1 = repo.read_object(hash1)
            if isinstance(blob1, Blob):
                try:
                    content1_lines = blob1.get_content().decode('utf-8').splitlines(keepends=True)
                except UnicodeDecodeError:
                    click.echo(f"{Fore.YELLOW}Binary file{Style.RESET_ALL}")
                    continue
        
        if hash2:
            blob2 = repo.read_object(hash2)
            if isinstance(blob2, Blob):
                try:
                    content2_lines = blob2.get_content().decode('utf-8').splitlines(keepends=True)
                except UnicodeDecodeError:
                    click.echo(f"{Fore.YELLOW}Binary file{Style.RESET_ALL}")
                    continue
        
        # Show unified diff
        diff = unified_diff(
            content1_lines,
            content2_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            lineterm=''
        )
        
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                click.echo(f"{Fore.GREEN}{line}{Style.RESET_ALL}")
            elif line.startswith('-') and not line.startswith('---'):
                click.echo(f"{Fore.RED}{line}{Style.RESET_ALL}")
            elif line.startswith('@@'):
                click.echo(f"{Fore.CYAN}{line}{Style.RESET_ALL}")
            else:
                click.echo(line)
    
    if not has_changes:
        click.echo(f"{Fore.GREEN}No changes{Style.RESET_ALL}")
