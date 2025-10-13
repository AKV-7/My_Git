"""
Serve command - Launch web UI for repository visualization.

Usage: mygit serve
       mygit serve --port 5000
"""

import click
from colorama import Fore, Style

from core.repository import Repository


@click.command()
@click.option('--port', '-p', default=5000, help='Port number')
@click.option('--host', '-h', default='127.0.0.1', help='Host address')
def serve_command(port, host):
    """Launch web UI for repository visualization."""
    # Find repository
    repo = Repository.find_repo()
    if repo is None:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Not a MyGit repository", err=True)
        raise click.Abort()
    
    try:
        from web.app import create_app
        
        app = create_app(repo)
        
        click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Starting MyGit Web UI...")
        click.echo(f"  Repository: {repo.root_path}")
        click.echo(f"  URL: {Fore.CYAN}http://{host}:{port}{Style.RESET_ALL}")
        click.echo(f"\n{Fore.YELLOW}Press Ctrl+C to stop{Style.RESET_ALL}\n")
        
        app.run(host=host, port=port, debug=False)
    
    except ImportError:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Flask is required for web UI", err=True)
        click.echo("  Install with: pip install flask flask-cors")
        raise click.Abort()
    except Exception as e:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}", err=True)
        raise click.Abort()
