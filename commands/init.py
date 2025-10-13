"""
Init command - Initialize a new MyGit repository.

Usage: mygit init
"""

import click
from colorama import Fore, Style

from core.repository import Repository
from utils.console import safe_print


@click.command()
@click.option('--branch', '-b', default='main', help='Initial branch name')
def init_command(branch):
    """Initialize a new MyGit repository."""
    try:
        repo = Repository()
        repo.init(initial_branch=branch)
        
        click.echo(safe_print(f"{Fore.GREEN}✓{Style.RESET_ALL} Initialized empty MyGit repository in {repo.git_dir}"))
        click.echo(f"  Initial branch: {Fore.CYAN}{branch}{Style.RESET_ALL}")
        
    except ValueError as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
