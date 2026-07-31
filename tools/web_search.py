"""
Web Search Tool — DuckDuckGo autonomous search
No / command needed. LLM decides when to search.
"""
from typing import List, Optional

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

class WebSearchTool:
    """Autonomous web search via DuckDuckGo."""

    def __init__(self):
        self._ddgs = None

    def _get_ddgs(self):
        if not DDGS_AVAILABLE:
            return None
        if self._ddgs is None:
            self._ddgs = DDGS()
        return self._ddgs

    def search(self, query: str, max_results: int = 5) -> str:
        """Search web and return formatted results."""
        ddgs = self._get_ddgs()
        if not ddgs:
            return "[Web Search] DuckDuckGo search not available. Install: uv pip install duckduckgo-search"

        try:
            results = ddgs.text(query, max_results=max_results)
            if not results:
                return f"[Web Search] No results found for: {query}"

            lines = [f"🔍 Web Search Results for: '{query}'\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                href = r.get("href", "")
                body = r.get("body", "")[:200]
                lines.append(f"{i}. **{title}**")
                lines.append(f"   {href}")
                lines.append(f"   {body}...\n")

            return "\n".join(lines)
        except Exception as e:
            return f"[Web Search] Error: {e}"

    def search_news(self, query: str, max_results: int = 3) -> str:
        """Search news."""
        ddgs = self._get_ddgs()
        if not ddgs:
            return "[Web Search] Not available"

        try:
            results = ddgs.news(query, max_results=max_results)
            lines = [f"📰 News for: '{query}'\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. **{r.get('title', 'No title')}**")
                lines.append(f"   {r.get('url', '')}")
                lines.append(f"   {r.get('body', '')[:150]}...\n")
            return "\n".join(lines)
        except Exception as e:
            return f"[Web Search News] Error: {e}"
