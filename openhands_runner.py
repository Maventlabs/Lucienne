"""
OpenHands Runner — Absolute Edition
Wraps OpenHands SDK Conversation with:
- SOUL injection
- Memory persistence
- Skill auto-match
- MCP integration
- Safety layer (pause/approve/reject)
- Autonomous web search trigger
"""
import asyncio
import json
import os
import re
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional

from openhands.sdk import Conversation, Agent
from openhands.sdk.event.base import Event

from core.personality_engine import PersonalityEngine
from core.memory_manager import MemoryManager
from core.autonomous_loop import AutonomousLoop
from skills.skill_manager import SkillManager
from mcp_tools.mcp_manager import MCPManager
from tools.web_search import WebSearchTool
from tools.github_tool import GitHubTool


class LucienneRunner:
    """
    Absolute runner for Lucienne (CENGO).
    Persistent conversation, auto-init, hybrid safety.
    """

    # Event kinds that trigger safety pause
    RISKY_ACTION_KINDS = {
        "execute_ipython", "execute_bash", "execute",
        "file_delete", "file_edit", "write",
        "git_push", "git_reset", "git_force",
        "browser", "wget", "curl",
    }

    # Keywords that trigger autonomous web search
    SEARCH_TRIGGERS = {
        "cari", "search", "find", "lookup", "research",
        "latest", "terbaru", "update", "berita", "news",
        "documentation", "docs", "how to", "cara",
        "github.com", "npm", "pypi", "crate", "maven",
    }

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        github_token: Optional[str] = None,
        on_event: Optional[Callable[[str, Dict], Coroutine[Any, Any, None]]] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")

        self.on_event = on_event

        # Subsystems
        self.personality = PersonalityEngine()
        self.memory = MemoryManager()
        self.skills = SkillManager()
        self.mcp = MCPManager()
        self.web_search = WebSearchTool()
        self.github = GitHubTool(token=self.github_token)

        # OpenHands state
        self.conversation: Optional[Conversation] = None
        self.agent: Optional[Agent] = None
        self._pending_actions: List[Dict] = []
        self._is_paused = False
        self._current_task_id: Optional[str] = None

        # Autonomous loop
        self.autonomous: Optional[AutonomousLoop] = None

    # ========== INITIALIZATION ==========

    async def init(self) -> bool:
        """Initialize runner: create agent, conversation, enable safety."""
        try:
            # Create agent — OpenHands SDK requires `llm` config object
            self.agent = Agent(
                llm={
                    "model": self.model,
                    "api_key": self.api_key,
                    "base_url": self.base_url,
                },
            )

            # Build system prompt with SOUL + memory + skills + MCP
            system_prompt = self._build_system_prompt()

            # Create conversation with callbacks
            self.conversation = Conversation(
                agent=self.agent,
                callbacks=[self._event_callback],
            )

            # Enable confirmation policy (safety layer 1)
            if hasattr(self.conversation, "set_confirmation_policy"):
                self.conversation.set_confirmation_policy(enabled=True)

            # Send system prompt as first message
            await self._send_system_context(system_prompt)

            # Init autonomous loop
            self.autonomous = AutonomousLoop(
                llm_callback=self._llm_call,
                tool_callback=self._tool_call,
                on_step=self._on_autonomous_step,
            )

            return True
        except Exception as e:
            print(f"[Runner] Init failed: {e}")
            return False

    def _build_system_prompt(self) -> str:
        """Build full system prompt with all context."""
        parts = []

        # 1. SOUL
        parts.append(self.personality.get_system_prompt(mode="chat"))

        # 2. Memory context
        mem_context = self.memory.get_full_context()
        if mem_context:
            parts.append(mem_context)

        # 3. Skills context (generic, will be refined per-task)
        skill_names = self.skills.list_skills()
        if skill_names:
            parts.append(f"\n## Available Skills: {', '.join(skill_names[:10])}")

        # 4. MCP tools
        mcp_tools = self.mcp.format_tools_for_prompt()
        if mcp_tools:
            parts.append(mcp_tools)

        # 5. Web search capability
        parts.append("\n## Web Search\nYou can search the internet using DuckDuckGo. If user asks about current events, latest versions, or external knowledge, automatically search the web before answering.")

        # 6. GitHub capability
        parts.append("\n## GitHub\nYou can interact with GitHub repos via gh CLI. Token available if configured.")

        return "\n\n".join(parts)

    async def _send_system_context(self, prompt: str) -> None:
        """Send system context to conversation."""
        if self.conversation:
            # Use a hidden/system message approach
            self.conversation.send_message(
                message=f"[SYSTEM CONTEXT]\n{prompt}\n[/SYSTEM CONTEXT]\n\nAcknowledge you understand your role as CENGO.",
                is_system=True,
            )

    # ========== CHAT ==========

    async def chat(self, user_message: str, user_id: str = "default") -> str:
        """
        Handle free-form chat. Auto-detect search needs, inject skills.
        """
        if not self.conversation:
            success = await self.init()
            if not success:
                return "❌ Failed to initialize Lucienne. Check logs."

        # Log to memory
        self.memory.add_message("user", user_message, {"user_id": user_id})

        # Check if message triggers web search
        enriched_message = await self._maybe_enrich_with_search(user_message)

        # Match and inject skills
        skill_context = self.skills.get_skill_context(user_message)
        if skill_context:
            enriched_message = f"{skill_context}\n\nUser: {enriched_message}"

        # Send to OpenHands
        self.conversation.send_message(message=enriched_message)

        # Run conversation
        try:
            self.conversation.run()
        except Exception as e:
            return f"❌ Execution error: {e}"

        # Get response (OpenHands will stream via callback)
        # For non-streaming, we need to capture the final response
        # This is a simplified version; in production, response comes via callback
        response = "⚡ Processing... Check status for updates."

        self.memory.add_message("assistant", response, {"user_id": user_id})
        return response

    async def _maybe_enrich_with_search(self, message: str) -> str:
        """Auto-trigger web search if message contains search triggers."""
        msg_lower = message.lower()

        # Check for search triggers
        should_search = any(trigger in msg_lower for trigger in self.SEARCH_TRIGGERS)

        # Also check for URL patterns that suggest external lookup
        url_pattern = re.compile(r'(https?://|www\.)[^\s]+')
        has_url = bool(url_pattern.search(message))

        if should_search and not has_url:
            # Extract what to search for (naive: use whole message)
            search_query = message
            search_result = self.web_search.search(search_query, max_results=3)

            if search_result and not search_result.startswith("["):
                return f"[AUTO-SEARCH RESULTS]\n{search_result}\n[/AUTO-SEARCH]\n\nUser question: {message}"

        return message

    # ========== TASK ==========

    async def run_task(self, task_description: str, user_id: str = "default") -> str:
        """Run a specific task via OpenHands agent."""
        if not self.conversation:
            await self.init()

        task_id = str(uuid.uuid4())[:8]
        self._current_task_id = task_id

        self.memory.log_task(task_id, task_description, "running")

        # Inject task-specific skill context
        skill_context = self.skills.get_skill_context(task_description)

        prompt = f"""🌙 TASK: {task_description}

Execute this task step by step. If you need to search the web, use web_search tool. If you need GitHub, use github tool.
{skill_context}

Report progress and final result clearly.
"""

        self.conversation.send_message(message=prompt)

        try:
            self.conversation.run()
            self.memory.update_task_status(task_id, "completed")
            return f"⚡ Task {task_id} initiated. Monitoring execution..."
        except Exception as e:
            self.memory.update_task_status(task_id, "failed", error=str(e))
            return f"❌ Task {task_id} failed: {e}"

    # ========== AUTONOMOUS ==========

    async def run_autonomous(self, task: str, user_id: str = "default") -> Dict[str, Any]:
        """Run autonomous multi-step loop."""
        if not self.autonomous:
            return {"status": "error", "error": "Autonomous loop not initialized"}

        context = self.memory.get_full_context()
        result = await self.autonomous.run(task, context)

        # Log to memory
        self.memory.log_task(
            result["task_id"],
            task,
            result["status"],
            result=result["result"],
            error="; ".join(result["errors"]) if result["errors"] else ""
        )

        return result

    # ========== SAFETY CONTROLS ==========

    def approve_pending(self) -> str:
        """Approve pending risky action."""
        if not self._is_paused:
            return "No pending action to approve."

        self._is_paused = False
        try:
            if hasattr(self.conversation, "run"):
                self.conversation.run()
            return "✅ Approved. Continuing execution..."
        except Exception as e:
            return f"❌ Error after approval: {e}"

    def reject_pending(self) -> str:
        """Reject pending risky action."""
        if not self._is_paused:
            return "No pending action to reject."

        self._is_paused = False
        try:
            if hasattr(self.conversation, "reject_pending_actions"):
                self.conversation.reject_pending_actions()
            return "❌ Rejected. Skipping action..."
        except Exception as e:
            return f"⚠️ Rejected but error: {e}"

    def cancel_execution(self) -> str:
        """Cancel current execution."""
        if self.autonomous:
            self.autonomous.cancel()

        try:
            if self.conversation and hasattr(self.conversation, "interrupt"):
                self.conversation.interrupt()
        except Exception:
            pass

        self._is_paused = False
        return "🛑 Execution cancelled."

    def reset_conversation(self) -> str:
        """Reset conversation state."""
        self.conversation = None
        self._pending_actions.clear()
        self._is_paused = False
        self.memory.clear_short_term()
        return "🔄 Conversation reset. Starting fresh."

    # ========== CALLBACKS ==========

    def _event_callback(self, event: Event) -> None:
        """Handle events from OpenHands conversation."""
        try:
            event_data = event.model_dump() if hasattr(event, "model_dump") else dict(event)
        except Exception:
            event_data = {"raw": str(event)}

        kind = event_data.get("kind", "unknown")
        content = event_data.get("content", "")

        # Check for risky actions
        if kind in self.RISKY_ACTION_KINDS:
            self._is_paused = True
            self._pending_actions.append(event_data)

            if self.on_event:
                asyncio.create_task(self.on_event("safety_pause", {
                    "kind": kind,
                    "content": content,
                    "action_id": event_data.get("id", "unknown"),
                }))
            return

        # Stream normal events
        if self.on_event:
            asyncio.create_task(self.on_event("stream", {
                "kind": kind,
                "content": content,
            }))

    async def _llm_call(self, prompt: str) -> str:
        """Callback for autonomous loop LLM calls."""
        if not self.conversation:
            return "[Error] Conversation not initialized"

        self.conversation.send_message(message=prompt)
        self.conversation.run()

        # In real implementation, capture response from callback
        # Here we return a placeholder
        return "[LLM Response Placeholder — integrate with actual OpenHands response capture]"

    async def _tool_call(self, tool_name: str, params: Dict) -> str:
        """Callback for autonomous loop tool calls."""
        if tool_name == "web_search":
            return self.web_search.search(params.get("query", ""))
        elif tool_name == "read_file":
            try:
                path = params.get("path", "")
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading {params.get('path')}: {e}]"
        elif tool_name == "write_file":
            try:
                path = params.get("path", "")
                content = params.get("content", "")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"[Written {path}]"
            except Exception as e:
                return f"[Error writing {params.get('path')}: {e}]"
        elif tool_name == "execute_shell":
            try:
                import subprocess
                result = subprocess.run(
                    params.get("command", ""),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.stdout or result.stderr or "[No output]"
            except Exception as e:
                return f"[Shell error: {e}]"
        elif tool_name == "github":
            action = params.get("action", "")
            if action == "clone":
                return self.github.clone(params.get("repo", ""))
            elif action == "info":
                return self.github.repo_info(params.get("repo", ""))
            else:
                return self.github._run(params.get("command", []))
        elif tool_name == "mcp":
            return "[MCP tool execution not yet implemented in autonomous loop]"
        else:
            return f"[Unknown tool: {tool_name}]"

    async def _on_autonomous_step(self, step_num: int, phase: str, message: str) -> None:
        """Callback for autonomous step updates."""
        if self.on_event:
            await self.on_event("autonomous_step", {
                "step": step_num,
                "phase": phase,
                "message": message,
            })

    # ========== STATUS ==========

    def get_status(self) -> Dict[str, Any]:
        """Get current runner status."""
        return {
            "initialized": self.conversation is not None,
            "paused": self._is_paused,
            "pending_actions": len(self._pending_actions),
            "current_task": self._current_task_id,
            "skills_loaded": len(self.skills.list_skills()),
            "mcp_servers": len(self.mcp.list_servers()),
            "memory_tasks": len(self.memory.get_task_history()),
        }
