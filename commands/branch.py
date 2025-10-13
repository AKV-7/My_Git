"""
Branch command - List, create, or delete branches.

Usage: mygit branch
       mygit branch <branch-name>
       mygit branch -d <branch-name>
"""

import click
from colorama import Fore, Style

from core.repository import Repository


@click.command()
@click.argument('branch_name', required=False)
@click.option('--delete', '-d', is_flag=True, help='Delete a branch')
def branch_command(branch_name, delete):
    """List, create, or delete branches."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        if delete:
            # Delete branch
            if not branch_name:
                click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Branch name required for deletion", err=True)
                raise click.Abort()
            
            current_branch = repo.get_current_branch()
            if current_branch == branch_name:
                click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Cannot delete the currently checked out branch", err=True)
                raise click.Abort()
            
            import os
            branch_file = os.path.join(repo.heads_dir, branch_name)
            if not os.path.exists(branch_file):
                click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Branch '{branch_name}' not found", err=True)
                raise click.Abort()
            
            os.remove(branch_file)
            click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Deleted branch {Fore.CYAN}{branch_name}{Style.RESET_ALL}")
        
        elif branch_name:
            # Create new branch
            current_commit = repo.get_current_commit()
            if current_commit is None:
                click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Cannot create branch - no commits yet", err=True)
                raise click.Abort()
            
            # Check if branch already exists
            if repo.get_branch_commit(branch_name) is not None:
                click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Branch '{branch_name}' already exists", err=True)
                raise click.Abort()
            
            # Create branch pointing to current commit
            repo.set_branch_commit(branch_name, current_commit)
            click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Created branch {Fore.CYAN}{branch_name}{Style.RESET_ALL} at {current_commit[:7]}")
        
        else:
            # List all branches
            branches = repo.list_branches()
            current_branch = repo.get_current_branch()
            
            if not branches:
                click.echo(f"{Fore.YELLOW}No branches yet{Style.RESET_ALL}")
                return
            
            for branch in sorted(branches):
                if branch == current_branch:
                    click.echo(f"{Fore.GREEN}* {branch}{Style.RESET_ALL}")
                else:
                    click.echo(f"  {branch}")
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
