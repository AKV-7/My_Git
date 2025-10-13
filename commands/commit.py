"""
Commit command - Record changes to the repository.

Usage: mygit commit -m "message"
"""

import click
from colorama import Fore, Style
from datetime import datetime

from core.repository import Repository
from core.index import Index
from core.objects import Commit


@click.command()
@click.option('--message', '-m', required=True, help='Commit message')
def commit_command(message):
    """Record changes to the repository."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    # Load index
    index = Index(repo)
    
    if index.is_empty():
        click.echo(f"{Fore.YELLOW}Warning:{Style.RESET_ALL} No changes staged for commit")
        click.echo("  Use 'mygit add <file>' to stage changes")
        return
    
    try:
        # Create tree from staged files
        tree = index.create_tree()
        tree_hash = repo.write_object(tree)
        
        # Get parent commit (if exists)
        parent_hash = repo.get_current_commit()
        parent_hashes = [parent_hash] if parent_hash else []
        
        # Get author info from config
        config = repo.get_config()
        author_name = config.get('user', {}).get('name', 'Unknown')
        author_email = config.get('user', {}).get('email', 'unknown@example.com')
        
        # Create commit object
        commit = Commit(
            tree_hash=tree_hash,
            parent_hashes=parent_hashes,
            author=author_name,
            email=author_email,
            message=message,
            timestamp=datetime.now()
        )
        
        commit_hash = repo.write_object(commit)
        
        # Update current branch
        current_branch = repo.get_current_branch()
        if current_branch:
            repo.set_branch_commit(current_branch, commit_hash)
        else:
            # Detached HEAD - update HEAD directly
            repo.set_head(commit_hash)
        
        # Clear staging area
        index.clear()
        
        # Display success message
        click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Created commit {Fore.CYAN}{commit_hash[:7]}{Style.RESET_ALL}")
        if current_branch:
            click.echo(f"  Branch: {Fore.CYAN}{current_branch}{Style.RESET_ALL}")
        click.echo(f"  Message: {message}")
        
        if parent_hashes:
            click.echo(f"  Parent: {parent_hashes[0][:7]}")
        else:
            click.echo(f"  {Fore.YELLOW}(Initial commit){Style.RESET_ALL}")
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
