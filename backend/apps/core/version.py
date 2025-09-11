"""
Version tracking service using GitPython
"""
import os
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class VersionService:
    """Service for tracking application version and build information"""
    
    @staticmethod
    @lru_cache(maxsize=1)
    def get_version_info() -> Dict[str, Any]:
        """
        Get comprehensive version information from git and environment.
        Cached to avoid repeated git operations.
        """
        info = {
            'version': 'unknown',
            'commit': 'unknown',
            'branch': 'unknown',
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'dirty': False,
            'ahead': 0,
            'build_date': datetime.now().isoformat(),
            'build_number': os.getenv('BUILD_NUMBER', '0'),
            'frontend_version': None,
            'backend_version': None,
            'python_version': None,
        }
        
        # Get Git information
        if GIT_AVAILABLE:
            git_info = VersionService._get_git_info()
            info.update(git_info)
        
        # Get package versions
        package_info = VersionService._get_package_info()
        info.update(package_info)
        
        # Get Python version
        import sys
        info['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Determine environment from branch if not set
        if info['environment'] == 'development':
            branch = info.get('branch', '')
            if isinstance(branch, str):
                if branch == 'main' or branch == 'master':
                    info['environment'] = 'production'
                elif branch == 'staging':
                    info['environment'] = 'staging'
                elif branch.startswith('feature/') or branch.startswith('dev'):
                    info['environment'] = 'development'
        
        return info
    
    @staticmethod
    def _get_git_info() -> Dict[str, Any]:
        """Get information from git repository"""
        try:
            # Find git repo from current or parent directories
            repo_path = Path(__file__).resolve().parent.parent.parent.parent
            # Go up until we find .git directory
            while repo_path.parent != repo_path:
                if (repo_path / '.git').exists():
                    break
                repo_path = repo_path.parent
            
            if not (repo_path / '.git').exists():
                # Try from cwd as fallback
                repo_path = Path.cwd()
                while repo_path.parent != repo_path:
                    if (repo_path / '.git').exists():
                        break
                    repo_path = repo_path.parent
            
            repo = Repo(repo_path)
            
            # Get latest tag for version
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime) if repo.tags else []
            latest_tag = tags[-1].name if tags else 'v0.0.0'
            
            # Remove 'v' prefix if present
            version = latest_tag.lstrip('v') if latest_tag else '0.0.0'
            
            # Get current commit (short hash)
            commit = repo.head.commit.hexsha[:7]
            
            # Get branch name
            try:
                branch = repo.active_branch.name
            except TypeError:
                # Detached HEAD state
                branch = 'detached'
            
            # Check if working directory is dirty (has uncommitted changes)
            is_dirty = repo.is_dirty()
            
            # Count commits ahead of latest tag
            ahead = 0
            if tags:
                try:
                    ahead = len(list(repo.iter_commits(f'{latest_tag}..HEAD')))
                except:
                    ahead = 0
            
            # Get last commit date
            last_commit_date = repo.head.commit.committed_datetime.isoformat()
            
            return {
                'version': version,
                'commit': commit,
                'branch': branch,
                'dirty': is_dirty,
                'ahead': ahead,
                'last_commit_date': last_commit_date,
                'tag': latest_tag,
            }
        except Exception as e:
            return {
                'version': '0.0.0',
                'commit': 'unknown',
                'branch': 'unknown',
                'error': str(e)
            }
    
    @staticmethod
    def _get_package_info() -> Dict[str, Any]:
        """Get version information from package.json files"""
        info = {}
        
        # Try to get frontend version from package.json
        try:
            frontend_package = Path.cwd() / 'frontend' / 'package.json'
            if not frontend_package.exists():
                frontend_package = Path.cwd().parent / 'frontend' / 'package.json'
            
            if frontend_package.exists():
                with open(frontend_package, 'r') as f:
                    data = json.load(f)
                    info['frontend_version'] = data.get('version', 'unknown')
        except Exception:
            info['frontend_version'] = 'unknown'
        
        # Try to get backend version from setup.py or pyproject.toml
        try:
            pyproject = Path.cwd() / 'pyproject.toml'
            if not pyproject.exists():
                pyproject = Path.cwd().parent / 'pyproject.toml'
            
            if pyproject.exists():
                # Simple extraction - could use toml library for proper parsing
                with open(pyproject, 'r') as f:
                    content = f.read()
                    if 'version = ' in content:
                        import re
                        match = re.search(r'version\s*=\s*"([^"]+)"', content)
                        if match:
                            info['backend_version'] = match.group(1)
        except Exception:
            info['backend_version'] = 'unknown'
        
        return info
    
    @staticmethod
    def get_simple_version() -> str:
        """Get a simple version string for display"""
        info = VersionService.get_version_info()
        version = info.get('version', '0.0.0')
        
        # Add commit hash if ahead of tag
        if info.get('ahead', 0) > 0:
            version = f"{version}+{info.get('commit', 'unknown')}"
        
        # Add dirty flag if uncommitted changes
        if info.get('dirty', False):
            version = f"{version}-dirty"
        
        return version
    
    @staticmethod
    def clear_cache():
        """Clear the version cache (useful for development)"""
        VersionService.get_version_info.cache_clear()


# Convenience function
def get_version() -> str:
    """Get the current application version"""
    return VersionService.get_simple_version()