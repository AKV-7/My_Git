"""
Add command - Add files to the staging area.

Usage: mygit add <file>...
       mygit add .
"""

import click
from colorama import Fore, Style

from core.repository import Repository
from core.index import Index


@click.command()
@click.argument('files', nargs=-1, required=True)
def add_command(files):
    """Add file contents to the staging area."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    # Load index
    index = Index(repo)
    
    try:
        # Add files
        added_files = index.add_files(list(files))
        
        if added_files:
            click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Added {len(added_files)} file(s) to staging area:")
            for filepath in added_files[:10]:  # Show first 10
                click.echo(f"  {Fore.GREEN}+{Style.RESET_ALL} {filepath}")
            
            if len(added_files) > 10:
                click.echo(f"  ... and {len(added_files) - 10} more")
        else:
            click.echo(f"{Fore.YELLOW}Warning:{Style.RESET_ALL} No files matched the pattern")
    
    except FileNotFoundError as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
