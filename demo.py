"""
Demo script to showcase MyGit functionality.

Run this script to see MyGit in action with a complete workflow.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd):
    """Run a command and print output."""
    print(f"\n{'='*60}")
    print(f"$ {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result.returncode


def create_file(path, content):
    """Create a file with given content."""
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created: {path}")


def main():
    """Run MyGit demo."""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║                                                        ║
    ║              MyGit Demo Workflow                       ║
    ║     Demonstrating Version Control Fundamentals         ║
    ║                                                        ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Setup
    demo_dir = Path("demo_repo")
    
    # Clean up if exists
    if demo_dir.exists():
        print(f"Cleaning up existing {demo_dir}...")
        shutil.rmtree(demo_dir)
    
    # Create demo directory
    demo_dir.mkdir()
    os.chdir(demo_dir)
    
    print("\n📁 Demo repository created at:", demo_dir.absolute())
    
    # 1. Initialize repository
    print("\n\n🚀 PHASE 1: Repository Initialization")
    run_command("mygit init")
    
    # 2. Create and add files
    print("\n\n📝 PHASE 2: Creating and Staging Files")
    
    create_file("README.md", """# Demo Project

This is a demo project to showcase MyGit functionality.

## Features
- Version control
- Branching
- Merging
""")
    
    create_file("main.py", """def hello():
    print("Hello, MyGit!")

if __name__ == "__main__":
    hello()
""")
    
    create_file("config.json", """{
    "version": "1.0.0",
    "name": "demo"
}
""")
    
    run_command("mygit add .")
    
    # 3. First commit
    print("\n\n💾 PHASE 3: Creating Initial Commit")
    run_command('mygit commit -m "Initial commit: Add project files"')
    
    # 4. View status and log
    print("\n\n📊 PHASE 4: Repository Status")
    run_command("mygit status")
    
    print("\n\n📜 PHASE 5: Commit History")
    run_command("mygit log")
    
    # 5. Create a feature branch
    print("\n\n🌿 PHASE 6: Creating Feature Branch")
    run_command("mygit branch feature-greeting")
    run_command("mygit branch")
    
    # 6. Switch to feature branch
    print("\n\n🔀 PHASE 7: Switching to Feature Branch")
    run_command("mygit checkout feature-greeting")
    
    # 7. Make changes in feature branch
    print("\n\n✏️ PHASE 8: Making Changes in Feature Branch")
    
    create_file("greetings.py", """def greet(name):
    return f"Hello, {name}! Welcome to MyGit."

def goodbye(name):
    return f"Goodbye, {name}! Happy coding!"
""")
    
    # Update main.py
    create_file("main.py", """from greetings import greet, goodbye

def hello():
    print(greet("User"))
    print(goodbye("User"))

if __name__ == "__main__":
    hello()
""")
    
    run_command("mygit add .")
    run_command('mygit commit -m "Add greeting functionality"')
    
    # 8. View log with feature branch
    print("\n\n📜 PHASE 9: Commit History with Feature Branch")
    run_command("mygit log --oneline")
    
    # 9. Switch back to main
    print("\n\n🔙 PHASE 10: Switching Back to Main Branch")
    run_command("mygit checkout main")
    
    # 10. Make a change in main (for merge demonstration)
    print("\n\n📝 PHASE 11: Making Change in Main Branch")
    
    create_file("LICENSE", """MIT License

Copyright (c) 2025 MyGit Demo

Permission is hereby granted...
""")
    
    run_command("mygit add LICENSE")
    run_command('mygit commit -m "Add LICENSE file"')
    
    # 11. Merge feature branch
    print("\n\n🔀 PHASE 12: Merging Feature Branch")
    run_command("mygit merge feature-greeting")
    
    # 12. View final log
    print("\n\n📜 PHASE 13: Final Commit History")
    run_command("mygit log --oneline")
    
    # 13. Show statistics
    print("\n\n📊 PHASE 14: Repository Statistics")
    run_command("mygit stats")
    
    # 14. Show diff
    print("\n\n📋 PHASE 15: View Changes")
    run_command("mygit log --oneline")
    
    print("\n\n" + "="*60)
    print("✅ Demo Complete!")
    print("="*60)
    print(f"""
Demo repository is located at: {demo_dir.absolute()}

Next steps:
1. Explore the repository: cd {demo_dir}
2. Try more commands: mygit --help
3. Launch Web UI: mygit serve
4. View files: ls or dir

To clean up: cd .. && Remove-Item -Recurse -Force {demo_dir}
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
