"""LLM prompt for extracting job descriptions from scraped web content."""

from app.llm.prompts import PromptRegistry

JOB_DESCRIPTION_EXTRACTION_PROMPT = """Extract ONLY the job description from this web page text. \
Remove navigation, headers, footers, sidebar content, and unrelated text. \
Return the clean, complete job description text. \
Do NOT wrap the output in code blocks or JSON - return plain text only.

Page content:
{raw_content}"""

PromptRegistry.register("job_description_extraction", JOB_DESCRIPTION_EXTRACTION_PROMPT)
