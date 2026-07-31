"""
Skill Manager — Auto-scan and match skills from /opt/skills
Supports: Claude (.md XML), OpenCode (.json), Vercel (.md frontmatter), Custom (.py)
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class SkillManager:
    """Manages skill discovery, loading, and matching."""

    SKILL_DIR = "/opt/skills"

    def __init__(self, skill_dir: Optional[str] = None):
        self.skill_dir = Path(skill_dir or self.SKILL_DIR)
        self._skills: Dict[str, Dict] = {}
        self._scan_skills()

    def _scan_skills(self) -> None:
        """Recursively scan skill directory."""
        if not self.skill_dir.exists():
            return

        for file_path in self.skill_dir.rglob("*"):
            if file_path.is_file():
                skill = self._parse_skill(file_path)
                if skill:
                    self._skills[skill["name"]] = skill

    def _parse_skill(self, file_path: Path) -> Optional[Dict]:
        """Parse a skill file based on extension and content."""
        ext = file_path.suffix.lower()
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        if ext == ".md":
            return self._parse_md_skill(file_path, content)
        elif ext == ".json":
            return self._parse_json_skill(file_path, content)
        elif ext == ".py":
            return self._parse_py_skill(file_path, content)
        return None

    def _parse_md_skill(self, path: Path, content: str) -> Optional[Dict]:
        """Parse Claude XML-style or Vercel frontmatter skill."""
        # Claude style: <skill name="...">...</skill>
        claude_match = re.search(r'<skill\s+name="([^"]+)"[^>]*>(.*?)</skill>', content, re.DOTALL)
        if claude_match:
            return {
                "name": claude_match.group(1),
                "type": "claude",
                "source": str(path),
                "content": claude_match.group(2).strip(),
                "keywords": self._extract_keywords(claude_match.group(2)),
            }

        # Vercel style: --- skill: name ---
        vercel_match = re.search(r'^---\s*\nskill:\s*(\w+)', content)
        if vercel_match:
            return {
                "name": vercel_match.group(1),
                "type": "vercel",
                "source": str(path),
                "content": content,
                "keywords": self._extract_keywords(content),
            }
        return None

    def _parse_json_skill(self, path: Path, content: str) -> Optional[Dict]:
        """Parse OpenCode JSON skill."""
        try:
            data = json.loads(content)
            if "name" in data:
                return {
                    "name": data["name"],
                    "type": "opencode",
                    "source": str(path),
                    "content": content,
                    "keywords": self._extract_keywords(json.dumps(data)),
                    "schema": data,
                }
        except json.JSONDecodeError:
            pass
        return None

    def _parse_py_skill(self, path: Path, content: str) -> Optional[Dict]:
        """Parse Custom Python skill."""
        spec_match = re.search(r'SKILL_SPEC\s*=\s*({.*?})', content, re.DOTALL)
        if spec_match:
            try:
                spec = eval(spec_match.group(1))
                return {
                    "name": spec.get("name", path.stem),
                    "type": "custom",
                    "source": str(path),
                    "content": content,
                    "keywords": spec.get("keywords", self._extract_keywords(content)),
                    "spec": spec,
                }
            except Exception:
                pass
        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Filter common words
        stopwords = {"this", "that", "with", "from", "they", "have", "will", "been", "their", "what", "when", "where", "which", "while", "about", "could", "would", "should"}
        keywords = [w for w in words if w not in stopwords]
        # Return unique
        return list(dict.fromkeys(keywords))[:20]

    def match_skills(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Match skills to a query using simple keyword overlap scoring.
        Returns list of (skill_name, confidence) sorted by confidence.
        """
        query_words = set(self._extract_keywords(query))
        if not query_words:
            return []

        scores = []
        for name, skill in self._skills.items():
            skill_words = set(skill.get("keywords", []))
            if not skill_words:
                continue

            overlap = len(query_words & skill_words)
            union = len(query_words | skill_words)
            confidence = overlap / union if union > 0 else 0

            # Boost exact matches
            if any(word in name.lower() for word in query_words):
                confidence += 0.2

            if confidence > 0.1:
                scores.append((name, min(confidence, 1.0)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_skill(self, name: str) -> Optional[Dict]:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        """List all loaded skill names."""
        return list(self._skills.keys())

    def get_skill_context(self, query: str, threshold: float = 0.6) -> str:
        """Get formatted skill context for LLM injection."""
        matches = self.match_skills(query)
        filtered = [(n, s) for n, s in matches if s >= threshold]

        if not filtered:
            return ""

        parts = ["\n## Relevant Skills\n"]
        for name, score in filtered:
            skill = self._skills[name]
            parts.append(f"### {name} (confidence: {score:.2f})")
            parts.append(f"Type: {skill['type']}")
            content = skill.get("content", "")[:500]
            parts.append(f"Content: {content}...")
            parts.append("")

        return "\n".join(parts)

    def refresh(self) -> None:
        """Rescan skills directory."""
        self._skills.clear()
        self._scan_skills()
