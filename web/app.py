"""
Flask web application for MyGit visualization.

Provides a web UI to explore repository contents, commits, and diffs.
"""

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from typing import List, Dict

from core.repository import Repository
from core.objects import Commit, Tree, Blob


def create_app(repo: Repository) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    CORS(app)
    
    # Store repository reference
    app.config['REPO'] = repo
    
    @app.route('/')
    def index():
        """Serve main page."""
        return render_template_string(HTML_TEMPLATE)
    
    @app.route('/api/branches')
    def get_branches():
        """Get list of branches."""
        try:
            branches = repo.list_branches()
            current_branch = repo.get_current_branch()
            
            branch_data = []
            for branch in branches:
                commit_hash = repo.get_branch_commit(branch)
                is_current = branch == current_branch
                
                branch_info = {
                    'name': branch,
                    'commit': commit_hash,
                    'current': is_current
                }
                
                if commit_hash:
                    try:
                        commit = repo.read_object(commit_hash)
                        if isinstance(commit, Commit):
                            branch_info['message'] = commit.get_summary()
                            branch_info['author'] = commit.author
                            branch_info['date'] = commit.timestamp.isoformat()
                    except Exception:
                        pass
                
                branch_data.append(branch_info)
            
            return jsonify({'branches': branch_data})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/commits')
    def get_commits():
        """Get commit history."""
        try:
            branch = request.args.get('branch')
            limit = int(request.args.get('limit', 50))
            
            if branch:
                commit_hash = repo.get_branch_commit(branch)
            else:
                commit_hash = repo.get_current_commit()
            
            if not commit_hash:
                return jsonify({'commits': []})
            
            commits = []
            visited = set()
            count = 0
            
            while commit_hash and count < limit and commit_hash not in visited:
                visited.add(commit_hash)
                
                try:
                    commit = repo.read_object(commit_hash)
                    if not isinstance(commit, Commit):
                        break
                    
                    commits.append({
                        'hash': commit_hash,
                        'short_hash': commit_hash[:7],
                        'message': commit.message,
                        'summary': commit.get_summary(),
                        'author': commit.author,
                        'email': commit.email,
                        'date': commit.timestamp.isoformat(),
                        'parents': commit.parent_hashes
                    })
                    
                    if commit.parent_hashes:
                        commit_hash = commit.parent_hashes[0]
                    else:
                        commit_hash = None
                    
                    count += 1
                except Exception:
                    break
            
            return jsonify({'commits': commits})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/commit/<commit_hash>')
    def get_commit(commit_hash):
        """Get commit details."""
        try:
            commit = repo.read_object(commit_hash)
            
            if not isinstance(commit, Commit):
                return jsonify({'error': 'Not a commit'}), 404
            
            # Get files in this commit
            files = _get_tree_files(repo, commit.tree_hash)
            
            # Get diff from parent
            diff_data = []
            if commit.parent_hashes:
                parent_commit = repo.read_object(commit.parent_hashes[0])
                if isinstance(parent_commit, Commit):
                    parent_files = _get_tree_files(repo, parent_commit.tree_hash)
                    diff_data = _compute_diff(repo, parent_files, files)
            
            return jsonify({
                'hash': commit_hash,
                'tree': commit.tree_hash,
                'parents': commit.parent_hashes,
                'author': commit.author,
                'email': commit.email,
                'date': commit.timestamp.isoformat(),
                'message': commit.message,
                'files': files,
                'diff': diff_data
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/tree/<tree_hash>')
    def get_tree(tree_hash):
        """Get tree contents."""
        try:
            tree = repo.read_object(tree_hash)
            
            if not isinstance(tree, Tree):
                return jsonify({'error': 'Not a tree'}), 404
            
            entries = []
            for entry in tree.entries:
                entries.append({
                    'mode': entry.mode,
                    'name': entry.name,
                    'hash': entry.hash,
                    'type': 'tree' if entry.mode == '040000' else 'blob'
                })
            
            return jsonify({'entries': entries})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/blob/<blob_hash>')
    def get_blob(blob_hash):
        """Get blob content."""
        try:
            blob = repo.read_object(blob_hash)
            
            if not isinstance(blob, Blob):
                return jsonify({'error': 'Not a blob'}), 404
            
            content = blob.get_content()
            
            # Try to decode as text
            try:
                text_content = content.decode('utf-8')
                return jsonify({
                    'type': 'text',
                    'content': text_content,
                    'size': len(content)
                })
            except UnicodeDecodeError:
                return jsonify({
                    'type': 'binary',
                    'size': len(content),
                    'message': 'Binary file'
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/stats')
    def get_stats():
        """Get repository statistics."""
        try:
            objects = repo.list_objects()
            branches = repo.list_branches()
            
            object_types = {'blob': 0, 'tree': 0, 'commit': 0}
            for obj_hash in objects:
                try:
                    obj = repo.read_object(obj_hash)
                    object_types[obj.type] += 1
                except Exception:
                    pass
            
            return jsonify({
                'total_objects': len(objects),
                'blobs': object_types['blob'],
                'trees': object_types['tree'],
                'commits': object_types['commit'],
                'branches': len(branches)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app


def _get_tree_files(repo: Repository, tree_hash: str, prefix: str = "") -> Dict[str, str]:
    """Get all files from a tree recursively."""
    import os
    files = {}
    tree = repo.read_object(tree_hash)
    
    if not isinstance(tree, Tree):
        return files
    
    for entry in tree.entries:
        path = os.path.join(prefix, entry.name) if prefix else entry.name
        
        if entry.mode == "040000":
            files.update(_get_tree_files(repo, entry.hash, path))
        else:
            files[path] = entry.hash
    
    return files


def _compute_diff(repo: Repository, files1: Dict[str, str], files2: Dict[str, str]) -> List[Dict]:
    """Compute diff between two file sets."""
    all_paths = set(files1.keys()) | set(files2.keys())
    diffs = []
    
    for path in all_paths:
        hash1 = files1.get(path)
        hash2 = files2.get(path)
        
        if hash1 == hash2:
            continue
        
        diff_entry = {'path': path}
        
        if hash1 is None:
            diff_entry['status'] = 'added'
        elif hash2 is None:
            diff_entry['status'] = 'deleted'
        else:
            diff_entry['status'] = 'modified'
        
        diffs.append(diff_entry)
    
    return diffs


# Embedded HTML template for the web UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MyGit - Repository Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f6f8fa;
            color: #24292e;
        }
        
        .header {
            background: #24292e;
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid #e1e4e8;
        }
        
        .tab {
            padding: 0.75rem 1.5rem;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 500;
            color: #586069;
            transition: all 0.2s;
        }
        
        .tab:hover {
            color: #24292e;
        }
        
        .tab.active {
            color: #0366d6;
            border-bottom-color: #0366d6;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .card {
            background: white;
            border-radius: 6px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .commit {
            padding: 1rem;
            border-left: 3px solid #0366d6;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .commit:hover {
            background: #f6f8fa;
        }
        
        .commit-hash {
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
            color: #0366d6;
            font-weight: 600;
        }
        
        .commit-message {
            font-weight: 500;
            margin: 0.5rem 0;
        }
        
        .commit-meta {
            font-size: 0.875rem;
            color: #586069;
        }
        
        .branch {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: #f1f8ff;
            color: #0366d6;
            border-radius: 12px;
            margin: 0.25rem;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .branch.current {
            background: #28a745;
            color: white;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            font-size: 0.875rem;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #586069;
        }
        
        .error {
            background: #ffeef0;
            color: #d73a49;
            padding: 1rem;
            border-radius: 6px;
            border-left: 3px solid #d73a49;
        }
        
        .commit-details {
            background: #f6f8fa;
            padding: 1rem;
            border-radius: 6px;
            margin-top: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
        }
        
        .file-change {
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-radius: 4px;
        }
        
        .file-added {
            background: #d4edda;
            color: #155724;
        }
        
        .file-modified {
            background: #fff3cd;
            color: #856404;
        }
        
        .file-deleted {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 MyGit Repository Viewer</h1>
    </div>
    
    <div class="container">
        <div class="tabs">
            <button class="tab active" onclick="showTab('commits')">Commits</button>
            <button class="tab" onclick="showTab('branches')">Branches</button>
            <button class="tab" onclick="showTab('stats')">Statistics</button>
        </div>
        
        <div id="commits-tab" class="tab-content active">
            <div class="card">
                <h2 style="margin-bottom: 1rem;">Commit History</h2>
                <div id="commits-list" class="loading">Loading commits...</div>
            </div>
        </div>
        
        <div id="branches-tab" class="tab-content">
            <div class="card">
                <h2 style="margin-bottom: 1rem;">Branches</h2>
                <div id="branches-list" class="loading">Loading branches...</div>
            </div>
        </div>
        
        <div id="stats-tab" class="tab-content">
            <div class="card">
                <h2 style="margin-bottom: 1rem;">Repository Statistics</h2>
                <div id="stats-grid" class="stats-grid"></div>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
        }
        
        async function loadCommits() {
            try {
                const response = await fetch('/api/commits');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('commits-list').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    return;
                }
                
                if (data.commits.length === 0) {
                    document.getElementById('commits-list').innerHTML = 
                        '<p>No commits yet</p>';
                    return;
                }
                
                let html = '';
                data.commits.forEach(commit => {
                    const date = new Date(commit.date).toLocaleString();
                    html += `
                        <div class="commit" onclick="showCommitDetails('${commit.hash}')">
                            <div class="commit-hash">${commit.short_hash}</div>
                            <div class="commit-message">${commit.summary}</div>
                            <div class="commit-meta">${commit.author} • ${date}</div>
                        </div>
                    `;
                });
                
                document.getElementById('commits-list').innerHTML = html;
            } catch (error) {
                document.getElementById('commits-list').innerHTML = 
                    '<div class="error">Error loading commits: ' + error.message + '</div>';
            }
        }
        
        async function showCommitDetails(hash) {
            try {
                const response = await fetch('/api/commit/' + hash);
                const commit = await response.json();
                
                if (commit.error) {
                    alert('Error: ' + commit.error);
                    return;
                }
                
                let diffHtml = '';
                if (commit.diff && commit.diff.length > 0) {
                    commit.diff.forEach(file => {
                        const className = 'file-' + file.status;
                        diffHtml += `<div class="file-change ${className}">${file.status}: ${file.path}</div>`;
                    });
                } else {
                    diffHtml = '<p>No changes (initial commit)</p>';
                }
                
                const detailsHtml = `
                    <div class="commit-details">
                        <strong>Commit:</strong> ${commit.hash}<br>
                        <strong>Author:</strong> ${commit.author} <${commit.email}><br>
                        <strong>Date:</strong> ${new Date(commit.date).toLocaleString()}<br>
                        <strong>Message:</strong><br>
                        ${commit.message}<br><br>
                        <strong>Files Changed:</strong><br>
                        ${diffHtml}
                    </div>
                `;
                
                // Find the commit element and append details
                const commitElements = document.querySelectorAll('.commit');
                commitElements.forEach(el => {
                    if (el.querySelector('.commit-hash').textContent === hash.substring(0, 7)) {
                        const existing = el.querySelector('.commit-details');
                        if (existing) {
                            existing.remove();
                        } else {
                            el.insertAdjacentHTML('beforeend', detailsHtml);
                        }
                    }
                });
            } catch (error) {
                alert('Error loading commit details: ' + error.message);
            }
        }
        
        async function loadBranches() {
            try {
                const response = await fetch('/api/branches');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('branches-list').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    return;
                }
                
                let html = '';
                data.branches.forEach(branch => {
                    const className = branch.current ? 'branch current' : 'branch';
                    const marker = branch.current ? ' ✓ ' : '';
                    html += `<span class="${className}">${marker}${branch.name}</span>`;
                });
                
                document.getElementById('branches-list').innerHTML = html;
            } catch (error) {
                document.getElementById('branches-list').innerHTML = 
                    '<div class="error">Error loading branches: ' + error.message + '</div>';
            }
        }
        
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                if (stats.error) {
                    document.getElementById('stats-grid').innerHTML = 
                        '<div class="error">Error: ' + stats.error + '</div>';
                    return;
                }
                
                const statsHtml = `
                    <div class="stat-card">
                        <div class="stat-value">${stats.total_objects}</div>
                        <div class="stat-label">Total Objects</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.commits}</div>
                        <div class="stat-label">Commits</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.branches}</div>
                        <div class="stat-label">Branches</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.blobs}</div>
                        <div class="stat-label">Files (Blobs)</div>
                    </div>
                `;
                
                document.getElementById('stats-grid').innerHTML = statsHtml;
            } catch (error) {
                document.getElementById('stats-grid').innerHTML = 
                    '<div class="error">Error loading statistics: ' + error.message + '</div>';
            }
        }
        
        // Load initial data
        loadCommits();
        loadBranches();
        loadStats();
    </script>
</body>
</html>
"""
