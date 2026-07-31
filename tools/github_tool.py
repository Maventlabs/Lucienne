"""
GitHub Tool — Wrapper for gh CLI
Pre-installed in Dockerfile.
"""
import subprocess
from typing import Optional

class GitHubTool:
    """GitHub operations via gh CLI."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self._available = self._check_gh()

    def _check_gh(self) -> bool:
        try:
            result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _run(self, args: list, cwd: Optional[str] = None) -> str:
        if not self._available:
            return "[GitHub] gh CLI not installed. Install: https://cli.github.com"

        env = {}
        if self.token:
            env["GH_TOKEN"] = self.token

        try:
            result = subprocess.run(
                ["gh"] + args,
                capture_output=True,
                text=True,
                cwd=cwd,
                env={**subprocess.os.environ, **env}
            )
            if result.returncode != 0:
                return f"[GitHub Error] {result.stderr}"
            return result.stdout or "Success"
        except Exception as e:
            return f"[GitHub Error] {e}"

    def clone(self, repo: str, dir_name: Optional[str] = None) -> str:
        """Clone a repository."""
        args = ["repo", "clone", repo]
        if dir_name:
            args.append(dir_name)
        return self._run(args)

    def create_pr(self, title: str, body: str = "", base: str = "main") -> str:
        """Create a pull request."""
        return self._run(["pr", "create", "--title", title, "--body", body, "--base", base])

    def list_issues(self, repo: str, state: str = "open") -> str:
        """List issues."""
        return self._run(["issue", "list", "--repo", repo, "--state", state])

    def repo_info(self, repo: str) -> str:
        """Get repo info."""
        return self._run(["repo", "view", repo, "--json", "name,description,stargazersCount,primaryLanguage,pushedAt"])

    def status(self) -> str:
        """Get current repo status."""
        return self._run(["status"])

    def auth_status(self) -> str:
        """Check auth status."""
        return self._run(["auth", "status"])
