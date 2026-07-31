"""
MCP Manager — Dynamic Model Context Protocol server manager
Supports registration via mcp_config.json or Telegram /mcp commands
"""
import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

class MCPManager:
    """Manages MCP servers and tool discovery."""

    CONFIG_PATH = "/app/mcp_config.json"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or self.CONFIG_PATH)
        self._servers: Dict[str, Dict] = {}
        self._tools: Dict[str, Dict] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load MCP config from file."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                self._servers = data.get("servers", {})
            except Exception as e:
                print(f"[MCP] Failed to load config: {e}")

    def save_config(self) -> None:
        """Save current config to file."""
        self.config_path.write_text(
            json.dumps({"servers": self._servers}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def add_server(self, name: str, command: str, args: List[str], 
                   tools: Optional[List[Dict]] = None) -> bool:
        """Add a new MCP server."""
        self._servers[name] = {
            "command": command,
            "args": args,
            "tools": tools or []
        }
        self.save_config()
        return True

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server."""
        if name in self._servers:
            self.stop_server(name)
            del self._servers[name]
            self.save_config()
            return True
        return False

    def list_servers(self) -> List[str]:
        """List all registered servers."""
        return list(self._servers.keys())

    def get_server_tools(self, server_name: str) -> List[Dict]:
        """Get tools for a specific server."""
        server = self._servers.get(server_name, {})
        return server.get("tools", [])

    def get_all_tools(self) -> Dict[str, List[Dict]]:
        """Get all tools from all servers."""
        result = {}
        for name, server in self._servers.items():
            result[name] = server.get("tools", [])
        return result

    def start_server(self, name: str) -> bool:
        """Start an MCP server process."""
        if name not in self._servers:
            return False

        server = self._servers[name]
        try:
            proc = subprocess.Popen(
                [server["command"]] + server["args"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self._processes[name] = proc
            return True
        except Exception as e:
            print(f"[MCP] Failed to start {name}: {e}")
            return False

    def stop_server(self, name: str) -> bool:
        """Stop an MCP server process."""
        if name in self._processes:
            try:
                self._processes[name].terminate()
                del self._processes[name]
                return True
            except Exception:
                pass
        return False

    def stop_all(self) -> None:
        """Stop all MCP servers."""
        for name in list(self._processes.keys()):
            self.stop_server(name)

    def discover_tools(self, server_name: str) -> List[Dict]:
        """Auto-discover tools from a running MCP server."""
        # Placeholder: In real implementation, use MCP protocol
        # to list tools from the server
        return self.get_server_tools(server_name)

    def format_tools_for_prompt(self) -> str:
        """Format all available tools for LLM system prompt."""
        if not self._servers:
            return ""

        parts = ["\n## Available MCP Tools\n"]
        for server_name, server in self._servers.items():
            parts.append(f"### Server: {server_name}")
            for tool in server.get("tools", []):
                parts.append(f"- `{tool.get('name', 'unknown')}`: {tool.get('description', 'No description')}")
            parts.append("")

        return "\n".join(parts)
