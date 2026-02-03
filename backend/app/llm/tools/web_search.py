"""Web search tool for LLM function calling."""

import httpx

from ..base import Tool
from ..types import ToolResult


class WebSearchTool(Tool):
    """
    Web search tool using Serper API (or similar).

    Provides web search capabilities to LLMs for researching
    companies, roles, and other job-related information.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize web search tool.

        Args:
            api_key: Serper API key (or similar search API)
        """
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for current information about companies, job roles, "
            "industry news, and other relevant topics. Returns top search results "
            "with titles, URLs, and snippets."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(
        self, query: str, num_results: int = 5, **kwargs
    ) -> ToolResult:
        """
        Execute a web search.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            ToolResult with formatted search results
        """
        if not self._api_key:
            return ToolResult(
                success=False,
                content="",
                error="Web search API key not configured",
            )

        num_results = min(num_results, 10)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json={"q": query, "num": num_results},
                )
                response.raise_for_status()
                results = response.json()
                formatted = self._format_results(results)
                return ToolResult(success=True, content=formatted)

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                content="",
                error="Search request timed out",
            )
        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Search API error: {e.response.status_code}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Search failed: {str(e)}",
            )

    def _format_results(self, results: dict) -> str:
        """Format search results for LLM consumption."""
        lines = []

        # Knowledge graph if available
        if "knowledgeGraph" in results:
            kg = results["knowledgeGraph"]
            lines.append("## Knowledge Graph")
            if "title" in kg:
                lines.append(f"**{kg['title']}**")
            if "type" in kg:
                lines.append(f"Type: {kg['type']}")
            if "description" in kg:
                lines.append(f"Description: {kg['description']}")
            lines.append("")

        # Organic results
        if "organic" in results:
            lines.append("## Search Results")
            for i, item in enumerate(results["organic"], 1):
                lines.append(f"### {i}. {item.get('title', 'No title')}")
                lines.append(f"**URL:** {item.get('link', 'N/A')}")
                if "snippet" in item:
                    lines.append(f"**Snippet:** {item['snippet']}")
                lines.append("")

        # People also ask
        if "peopleAlsoAsk" in results:
            lines.append("## Related Questions")
            for qa in results["peopleAlsoAsk"][:3]:
                lines.append(f"- {qa.get('question', '')}")
            lines.append("")

        return "\n".join(lines) if lines else "No results found."
