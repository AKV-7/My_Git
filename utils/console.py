"""Console output utilities with Windows compatibility."""
import sys
import os


def safe_print(text: str) -> str:
    """
    Convert Unicode characters to ASCII-safe alternatives for Windows console.
    
    Args:
        text: Text that may contain Unicode characters
        
    Returns:
        Text with safe characters for the current console
    """
    # Check if we're on Windows with a problematic encoding
    if sys.platform == 'win32' and sys.stdout.encoding.lower() in ('cp1252', 'charmap'):
        # Replace Unicode symbols with ASCII equivalents
        replacements = {
            '✓': '[OK]',
            '✔': '[OK]',
            '✗': '[X]',
            '✘': '[X]',
            '⚠': '[!]',
            '→': '->',
            '←': '<-',
            '↓': '|',
            '↑': '|',
        }
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
    
    return text


# For backwards compatibility
def echo(message: str, **kwargs):
    """Print message with Windows console compatibility."""
    import click
    safe_message = safe_print(message)
    click.echo(safe_message, **kwargs)
