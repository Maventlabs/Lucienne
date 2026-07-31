"""
Memory Manager — Persistent conversation & task memory for Lucienne.
Similar to Hermes memory system but optimized for CENGO execution context.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

class MemoryManager:
    """
    Manages 5 memory layers:
    - short_term: Current conversation (last 20 messages)
    - long_term: Persistent facts, preferences
    - task_log: All tasks with metadata
    - folder_map: Workspace structure history
    - skill_registry: Skill usage tracking
    """

    def __init__(self, memory_dir: str = "/app/memory"):
        self.memory_dir = Path(memory_dir)
        self.short_term_path = self.memory_dir / "short_term.json"
        self.long_term_path = self.memory_dir / "long_term.json"
        self.task_log_path = self.memory_dir / "task_log.json"
        self.folder_map_path = self.memory_dir / "folder_map.json"
        self.skill_registry_path = self.memory_dir / "skill_registry.json"

        self._ensure_dirs()
        self._init_files()

    def _ensure_dirs(self) -> None:
        for subdir in ["short_term", "long_term", "task_log", "folder_map", "skill_registry"]:
            (self.memory_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _init_files(self) -> None:
        for path in [self.short_term_path, self.long_term_path, 
                     self.task_log_path, self.folder_map_path, self.skill_registry_path]:
            if not path.exists():
                path.write_text("[]" if "short_term" in str(path) or "task_log" in str(path) else "{}")

    # ========== SHORT TERM MEMORY ==========
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to short-term memory."""
        messages = self._load_json(self.short_term_path, [])
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        # Keep last 20
        messages = messages[-20:]
        self._save_json(self.short_term_path, messages)

        # Auto-consolidate every 5 messages
        if len(messages) % 5 == 0:
            self._consolidate_short_term()

    def get_conversation_context(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation context."""
        messages = self._load_json(self.short_term_path, [])
        return messages[-limit:]

    def clear_short_term(self) -> None:
        """Clear short-term memory (e.g., on /reset)."""
        self._save_json(self.short_term_path, [])

    # ========== LONG TERM MEMORY ==========
    def remember_fact(self, key: str, value: Any) -> None:
        """Store a persistent fact."""
        facts = self._load_json(self.long_term_path, {})
        facts[key] = {
            "value": value,
            "updated_at": datetime.utcnow().isoformat()
        }
        self._save_json(self.long_term_path, facts)

    def recall_fact(self, key: str) -> Optional[Any]:
        """Recall a persistent fact."""
        facts = self._load_json(self.long_term_path, {})
        entry = facts.get(key)
        return entry["value"] if entry else None

    def recall_all_facts(self) -> Dict:
        """Get all long-term facts."""
        return self._load_json(self.long_term_path, {})

    # ========== TASK LOG ==========
    def log_task(self, task_id: str, description: str, status: str, 
                 result: str = "", error: str = "", metadata: Optional[Dict] = None) -> None:
        """Log a task execution."""
        tasks = self._load_json(self.task_log_path, [])
        tasks.append({
            "task_id": task_id,
            "description": description,
            "status": status,  # pending, running, completed, failed, cancelled
            "result": result,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        self._save_json(self.task_log_path, tasks)

    def get_task_history(self, limit: int = 20) -> List[Dict]:
        """Get recent task history."""
        tasks = self._load_json(self.task_log_path, [])
        return tasks[-limit:]

    def update_task_status(self, task_id: str, status: str, result: str = "", error: str = "") -> None:
        """Update status of an existing task."""
        tasks = self._load_json(self.task_log_path, [])
        for task in reversed(tasks):
            if task["task_id"] == task_id:
                task["status"] = status
                if result:
                    task["result"] = result
                if error:
                    task["error"] = error
                task["updated_at"] = datetime.utcnow().isoformat()
                break
        self._save_json(self.task_log_path, tasks)

    # ========== FOLDER MAP ==========
    def update_folder_map(self, path: str, metadata: Optional[Dict] = None) -> None:
        """Update folder structure memory."""
        folder_map = self._load_json(self.folder_map_path, {})
        folder_map[path] = {
            "last_seen": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self._save_json(self.folder_map_path, folder_map)

    def get_folder_map(self) -> Dict:
        """Get known folder structures."""
        return self._load_json(self.folder_map_path, {})

    # ========== SKILL REGISTRY ==========
    def log_skill_usage(self, skill_name: str, success: bool, task_type: str = "") -> None:
        """Log skill usage for future matching."""
        registry = self._load_json(self.skill_registry_path, {})
        if skill_name not in registry:
            registry[skill_name] = {"uses": 0, "successes": 0, "last_used": "", "task_types": []}

        registry[skill_name]["uses"] += 1
        if success:
            registry[skill_name]["successes"] += 1
        registry[skill_name]["last_used"] = datetime.utcnow().isoformat()
        if task_type and task_type not in registry[skill_name]["task_types"]:
            registry[skill_name]["task_types"].append(task_type)

        self._save_json(self.skill_registry_path, registry)

    def get_skill_stats(self, skill_name: str) -> Optional[Dict]:
        """Get skill success stats."""
        registry = self._load_json(self.skill_registry_path, {})
        return registry.get(skill_name)

    def get_all_skill_stats(self) -> Dict:
        """Get all skill stats."""
        return self._load_json(self.skill_registry_path, {})

    # ========== HELPERS ==========
    def _load_json(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    def _save_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _consolidate_short_term(self) -> None:
        """Move important facts from short_term to long_term."""
        messages = self._load_json(self.short_term_path, [])
        # Simple heuristic: if user explicitly states preferences
        for msg in messages:
            content = msg.get("content", "")
            if "suka" in content.lower() or "prefer" in content.lower() or "gunakan" in content.lower():
                # Extract simple preference (naive implementation)
                self.remember_fact(f"preference_{len(self.recall_all_facts())}", content)

    def get_full_context(self) -> str:
        """Generate full context string for LLM injection."""
        parts = []

        # Recent conversation
        recent = self.get_conversation_context(5)
        if recent:
            parts.append("## Recent Conversation")
            for m in recent:
                parts.append(f"{m['role']}: {m['content'][:200]}")

        # Recent tasks
        tasks = self.get_task_history(3)
        if tasks:
            parts.append("\n## Recent Tasks")
            for t in tasks:
                parts.append(f"- [{t['status']}] {t['description'][:100]}")

        # Known facts
        facts = self.recall_all_facts()
        if facts:
            parts.append("\n## Known Facts")
            for k, v in list(facts.items())[:5]:
                parts.append(f"- {k}: {str(v['value'])[:100]}")

        return "\n".join(parts)
