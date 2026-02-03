"""Web fetch tool for LLM function calling."""

import re

import httpx

from ..base import Tool
from ..types import ToolResult


class WebFetchTool(Tool):
    """
    Web page fetching tool.

    Fetches web pages and converts them to markdown for LLM consumption.
    Useful for deep-diving into specific URLs found during research.
    """

    # Common user agent to avoid blocks
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Maximum content length to return (characters)
    MAX_CONTENT_LENGTH = 15000

    def __init__(self):
        """Initialize web fetch tool."""
        pass

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Fetch the content of a web page and return it as markdown. "
            "Use this to get detailed information from specific URLs found "
            "during web searches. Works best with article and company pages."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the web page to fetch",
                },
            },
            "required": ["url"],
        }

    async def execute(self, url: str, **kwargs) -> ToolResult:
        """
        Fetch a web page and convert to markdown.

        Args:
            url: URL to fetch

        Returns:
            ToolResult with page content as markdown
        """
        # Validate URL
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": self.USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                if "text/html" in content_type:
                    markdown = self._html_to_markdown(response.text)
                elif "application/json" in content_type:
                    markdown = f"```json\n{response.text[:self.MAX_CONTENT_LENGTH]}\n```"
                else:
                    # Plain text or other
                    markdown = response.text[: self.MAX_CONTENT_LENGTH]

                # Truncate if needed
                if len(markdown) > self.MAX_CONTENT_LENGTH:
                    markdown = (
                        markdown[: self.MAX_CONTENT_LENGTH]
                        + "\n\n[Content truncated...]"
                    )

                return ToolResult(
                    success=True,
                    content=f"# Content from {url}\n\n{markdown}",
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                content="",
                error=f"Request to {url} timed out",
            )
        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                content="",
                error=f"HTTP error {e.response.status_code} fetching {url}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to fetch {url}: {str(e)}",
            )

    def _html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to simple markdown.

        This is a basic implementation. For production, consider
        using html2text or similar library.
        """
        # Try to import html2text, fall back to basic conversion
        try:
            import html2text

            h2t = html2text.HTML2Text()
            h2t.ignore_links = False
            h2t.ignore_images = True
            h2t.ignore_emphasis = False
            h2t.body_width = 0  # Don't wrap lines
            h2t.skip_internal_links = True
            return h2t.handle(html)

        except ImportError:
            # Basic fallback conversion
            return self._basic_html_to_text(html)

    def _basic_html_to_text(self, html: str) -> str:
        """Basic HTML to text conversion without external dependencies."""
        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.I)

        # Convert headers
        html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", html, flags=re.DOTALL | re.I)
        html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", html, flags=re.DOTALL | re.I)
        html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", html, flags=re.DOTALL | re.I)

        # Convert paragraphs and line breaks
        html = re.sub(r"<p[^>]*>", "\n", html, flags=re.I)
        html = re.sub(r"</p>", "\n", html, flags=re.I)
        html = re.sub(r"<br[^>]*>", "\n", html, flags=re.I)

        # Convert lists
        html = re.sub(r"<li[^>]*>", "- ", html, flags=re.I)
        html = re.sub(r"</li>", "\n", html, flags=re.I)

        # Convert bold and italic
        html = re.sub(r"<(b|strong)[^>]*>(.*?)</\1>", r"**\2**", html, flags=re.DOTALL | re.I)
        html = re.sub(r"<(i|em)[^>]*>(.*?)</\1>", r"*\2*", html, flags=re.DOTALL | re.I)

        # Convert links
        html = re.sub(
            r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            r"[\2](\1)",
            html,
            flags=re.DOTALL | re.I,
        )

        # Remove remaining HTML tags
        html = re.sub(r"<[^>]+>", "", html)

        # Decode common HTML entities
        html = html.replace("&nbsp;", " ")
        html = html.replace("&amp;", "&")
        html = html.replace("&lt;", "<")
        html = html.replace("&gt;", ">")
        html = html.replace("&quot;", '"')
        html = html.replace("&#39;", "'")

        # Clean up whitespace
        html = re.sub(r"\n{3,}", "\n\n", html)
        html = re.sub(r" {2,}", " ", html)

        return html.strip()
