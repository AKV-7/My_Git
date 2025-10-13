"""
Show command - Show commit details and changes.

Usage: mygit show <commit-hash>
"""

import click
from colorama import Fore, Style

from core.repository import Repository
from core.objects import Commit
from commands.diff import _get_commit_files, _show_diffs


@click.command()
@click.argument('commit_hash')
def show_command(commit_hash):
    """Show commit details and changes."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        # Expand short hash if needed
        if len(commit_hash) < 40:
            objects = repo.list_objects()
            matches = [h for h in objects if h.startswith(commit_hash)]
            if len(matches) == 0:
                raise ValueError(f"Commit '{commit_hash}' not found")
            elif len(matches) > 1:
                raise ValueError(f"Ambiguous commit hash '{commit_hash}'")
            commit_hash = matches[0]
        
        # Read commit
        commit = repo.read_object(commit_hash)
        
        if not isinstance(commit, Commit):
            raise ValueError("Not a commit object")
        
        # Display commit info
        click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL}")
        click.echo(f"Author: {commit.author} <{commit.email}>")
        click.echo(f"Date:   {commit.timestamp.strftime('%a %b %d %H:%M:%S %Y')}")
        click.echo()
        
        for line in commit.message.split('\n'):
            click.echo(f"    {line}")
        click.echo()
        
        # Show diff from parent
        if commit.parent_hashes:
            parent_commit = repo.read_object(commit.parent_hashes[0])
            if isinstance(parent_commit, Commit):
                parent_files = _get_commit_files(repo, parent_commit.tree_hash)
                commit_files = _get_commit_files(repo, commit.tree_hash)
                _show_diffs(repo, parent_files, commit_files, "parent", "commit")
        else:
            click.echo(f"{Fore.YELLOW}(Initial commit - no parent to compare){Style.RESET_ALL}")
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
