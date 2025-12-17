"""
Git Helper Module
Detects code changes in Git repositories for targeted documentation updates
"""

import subprocess
from pathlib import Path
from typing import List, Optional


class GitHelper:
    """Helper class for Git operations and change detection"""

    def __init__(self, repo_path: str, default_branch: str = "main"):
        self.repo_path = Path(repo_path)
        self.default_branch = default_branch

    def get_changed_files(self, compare_branch: Optional[str] = None, file_extension: str = ".py") -> List[str]:
        """
        Get list of changed files compared to a branch

        Args:
            compare_branch: Branch to compare against (default: main/master)
            file_extension: Filter by file extension (default: .py)

        Returns:
            List of changed file paths
        """

        if compare_branch is None:
            compare_branch = self._get_default_branch()

        try:
            # Get changed files
            cmd = ["git", "diff", "--name-only", f"{compare_branch}...HEAD"]
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, check=True)

            files = result.stdout.strip().split("\n")

            # Filter by extension
            if file_extension:
                files = [f for f in files if f.endswith(file_extension)]

            return [f for f in files if f]  # Remove empty strings

        except subprocess.CalledProcessError as e:
            print(f"Error getting changed files: {e}")
            return []

    def get_current_branch(self) -> str:
        """Get the current Git branch name"""

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def _get_default_branch(self) -> str:
        """Determine the default branch (main or master)"""

        try:
            # Try to get remote default branch
            result = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip().split("/")[-1]
            return branch
        except subprocess.CalledProcessError:
            # Fallback to configured or default
            return self.default_branch

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes"""

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def commit_documentation(self, file_paths: List[str], message: str = "docs: Update API documentation"):
        """
        Commit documentation files

        Args:
            file_paths: List of documentation files to commit
            message: Commit message
        """

        try:
            # Add files
            for file_path in file_paths:
                subprocess.run(["git", "add", file_path], cwd=self.repo_path, check=True)

            # Commit
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)

            print(f"✅ Committed documentation: {message}")

        except subprocess.CalledProcessError as e:
            print(f"Error committing documentation: {e}")

    def is_git_repository(self) -> bool:
        """Check if the path is a Git repository"""

        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
