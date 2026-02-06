import asyncio
import re
import logging
from typing import Optional
from fastapi import HTTPException
from app.llm import get_llm_provider, Message, Role
from app.utils.url_validator import validate_url

logger = logging.getLogger(__name__)

SCRAPE_TIMEOUT = 30  # seconds


def _extract_text_from_response(content: Optional[str]) -> str:
    """
    Extract clean text from LLM response, handling markdown code blocks.
    Reuses pattern from extraction_service.py.
    """
    if not content:
        return ""
    # Try to extract from markdown code blocks (```text ... ``` or ``` ... ```)
    code_block_pattern = r'```(?:\w+)?\s*([\s\S]*?)\s*```'
    match = re.search(code_block_pattern, content)
    if match:
        return match.group(1).strip()
    return content.strip()


async def _fetch_page_content(url: str) -> str:
    """
    Fetch rendered page content using Playwright headless Chromium.
    Handles JS-rendered pages (LinkedIn, Greenhouse, Lever, Workday, etc.).
    """
    from playwright.async_api import async_playwright

    playwright_timeout_ms = (SCRAPE_TIMEOUT - 5) * 1000  # 25s, leaving 5s headroom

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, timeout=playwright_timeout_ms, wait_until="domcontentloaded")
            # Wait for content to render (JS-heavy sites)
            await page.wait_for_timeout(2000)
            # Get the text content of the page body
            content = await page.inner_text("body")
            return content
        finally:
            try:
                await browser.close()
            except Exception:
                logger.warning("Failed to close browser cleanly during cleanup")


async def scrape_job_posting(url: str) -> str:
    """
    Fetch and extract job posting content from URL.
    Phase 1: Playwright fetches rendered page content.
    Phase 2: LLM Provider extracts clean job description from raw text.
    """
    # SSRF protection: validate URL before fetching
    is_valid, error_msg = validate_url(url)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"{error_msg}. Please paste the job description manually."
        )

    try:
        # Phase 1: Fetch with Playwright
        raw_content = await asyncio.wait_for(
            _fetch_page_content(url),
            timeout=SCRAPE_TIMEOUT
        )

        if not raw_content or len(raw_content.strip()) < 50:
            raise HTTPException(
                status_code=422,
                detail="Page content too short to contain a job description. Please paste the text manually."
            )

        # Phase 2: LLM extracts job description from raw page text
        try:
            provider = get_llm_provider()
            prompt = (
                "Extract ONLY the job description from this web page text. "
                "Remove navigation, headers, footers, sidebar content, and unrelated text. "
                "Return the clean, complete job description text. "
                "Do NOT wrap the output in code blocks or JSON - return plain text only.\n\n"
                f"Page content:\n{raw_content[:15000]}"
            )

            messages = [Message(role=Role.USER, content=prompt)]
            response = await provider.generate(messages)
            result = _extract_text_from_response(response.content)

            if not result or len(result) < 50:
                raise HTTPException(
                    status_code=422,
                    detail="Could not extract job description from URL. Please paste the text manually."
                )

            return result
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            logger.warning(
                f"LLM extraction failed for {url}, falling back to raw content: {e}"
            )
            # Return truncated raw content as fallback
            return raw_content[:15000].strip()

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="URL fetch timed out. Please paste the job description manually."
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Scrape failed for {url}: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Failed to fetch URL: {str(e)}. Please paste the job description manually."
        )
