"""
Log command - Show commit history.

Usage: mygit log
       mygit log --oneline
"""

import click
from colorama import Fore, Style
from datetime import datetime

from core.repository import Repository
from core.objects import Commit


@click.command()
@click.option('--oneline', is_flag=True, help='Show abbreviated commit info')
@click.option('--max-count', '-n', type=int, help='Limit number of commits')
def log_command(oneline, max_count):
    """Show commit history."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    # Get current commit
    current_hash = repo.get_current_commit()
    
    if current_hash is None:
        click.echo(f"{Fore.YELLOW}No commits yet{Style.RESET_ALL}")
        return
    
    try:
        # Traverse commit history
        count = 0
        commit_hash = current_hash
        
        while commit_hash:
            if max_count and count >= max_count:
                break
            
            # Read commit object
            commit = repo.read_object(commit_hash)
            
            if not isinstance(commit, Commit):
                break
            
            # Display commit
            if oneline:
                # One-line format
                short_hash = Fore.YELLOW + commit_hash[:7] + Style.RESET_ALL
                message = commit.get_summary()
                click.echo(f"{short_hash} {message}")
            else:
                # Full format
                click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL}")
                click.echo(f"Author: {commit.author} <{commit.email}>")
                click.echo(f"Date:   {commit.timestamp.strftime('%a %b %d %H:%M:%S %Y')}")
                click.echo()
                
                # Indent commit message
                for line in commit.message.split('\n'):
                    click.echo(f"    {line}")
                click.echo()
            
            # Move to parent commit
            if commit.parent_hashes:
                commit_hash = commit.parent_hashes[0]
            else:
                commit_hash = None
            
            count += 1
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
