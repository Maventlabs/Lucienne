"""
Personality Engine — SOUL Injector for Lucienne (CENGO)
Auto-injects SOUL.md context into every LLM conversation.
"""
import os
from pathlib import Path
from typing import Optional

class PersonalityEngine:
    """Loads and injects SOUL.md persona into agent context."""

    SOUL_PATH = "/app/soul/SOUL.md"

    def __init__(self, soul_path: Optional[str] = None):
        self.soul_path = soul_path or self.SOUL_PATH
        self._soul_text: Optional[str] = None
        self._load_soul()

    def _load_soul(self) -> None:
        """Load SOUL.md from disk."""
        path = Path(self.soul_path)
        if path.exists():
            self._soul_text = path.read_text(encoding="utf-8")
        else:
            # Fallback minimal soul
            self._soul_text = (
                "You are Lucienne Nightfall (CENGO). "
                "Direct, technical, autonomous code executor. "
                "Safety-first. Bilingual ID/EN."
            )

    def get_system_prompt(self, mode: str = "chat") -> str:
        """
        Generate system prompt with SOUL injection.

        Args:
            mode: 'chat', 'auto', 'task', 'code', 'debug'
        """
        base = f"""{self._soul_text}

---

## Current Mode: {mode.upper()}

Rules for this session:
1. You are operating inside a Docker container with OpenHands SDK.
2. Workspace: /app/workspace
3. Skills: /opt/skills (auto-scanned, read-only)
4. You can execute code, search web, use GitHub, and access MCP tools.
5. ALWAYS explain what you are about to do BEFORE executing risky actions.
6. If uncertain, ask clarifying questions rather than guessing.
7. Respond in the user's language (default Indonesian, switch to English for technical terms).
8. Use emoji sparingly: 🌙 for identity, ⚡ for execution, 🔒 for safety.
"""

        mode_addons = {
            "auto": """
9. AUTONOMOUS MODE: You are in a multi-step loop. Plan first, then execute step-by-step.
10. After each step, reflect: Did it work? What next? Any risks?
11. Max 10 iterations. If stuck, report failure with analysis.
""",
            "code": """
9. CODE MODE: Write clean, documented code. Include error handling.
10. Test before declaring success. Show test output.
11. Follow language-specific best practices.
""",
            "debug": """
9. DEBUG MODE: Analyze root cause systematically.
10. Check logs, reproduce issue, isolate variables.
11. Propose fix with explanation, not just patch.
""",
        }

        return base + mode_addons.get(mode, "")

    def refresh_soul(self) -> None:
        """Reload SOUL.md from disk (for live updates)."""
        self._load_soul()
