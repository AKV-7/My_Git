#!/usr/bin/env python3
"""
MyGit - A minimal distributed version control system.

Main CLI entry point for MyGit commands.
"""

import sys
import os
import click
from colorama import init, Fore, Style

# Initialize colorama for Windows support with Unicode handling
init(autoreset=True)

# Force UTF-8 encoding on Windows to handle Unicode characters
if sys.platform == 'win32':
    try:
        # Try to set UTF-8 encoding for console
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        # Fallback: set environment variable for UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'

from commands.init import init_command
from commands.add import add_command
from commands.commit import commit_command
from commands.log import log_command
from commands.status import status_command
from commands.branch import branch_command
from commands.checkout import checkout_command
from commands.merge import merge_command
from commands.diff import diff_command
from commands.show import show_command
from commands.stats import stats_command
from commands.serve import serve_command


@click.group()
@click.version_option(version="1.0.0", prog_name="mygit")
def cli():
    """MyGit - A minimal distributed version control system.
    
    Build your own Git to understand version control internals.
    """
    pass


# Register all commands
cli.add_command(init_command, name="init")
cli.add_command(add_command, name="add")
cli.add_command(commit_command, name="commit")
cli.add_command(log_command, name="log")
cli.add_command(status_command, name="status")
cli.add_command(branch_command, name="branch")
cli.add_command(checkout_command, name="checkout")
cli.add_command(merge_command, name="merge")
cli.add_command(diff_command, name="diff")
cli.add_command(show_command, name="show")
cli.add_command(stats_command, name="stats")
cli.add_command(serve_command, name="serve")


def main():
    """Main entry point for MyGit CLI."""
    try:
        cli()
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
