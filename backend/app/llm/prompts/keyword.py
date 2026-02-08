"""LLM prompt for keyword extraction from job postings."""

from app.llm.prompts import PromptRegistry

KEYWORD_EXTRACTION_PROMPT = """Analyze this job posting and extract the most important keywords and skills.

For each keyword:
1. Identify the specific skill, technology, or qualification
2. Assign a priority score from 1-10 (10 = essential/mentioned multiple times, 1 = nice-to-have)
3. Categorize as: technical_skill, soft_skill, experience, qualification, tool, or domain

Return exactly 15-20 keywords in JSON format:
{{
    "keywords": [
        {{"text": "Python", "priority": 9, "category": "technical_skill"}},
        {{"text": "Leadership", "priority": 7, "category": "soft_skill"}}
    ]
}}

Job Posting:
{job_posting}

Return ONLY valid JSON, no other text."""

PromptRegistry.register("keyword_extraction", KEYWORD_EXTRACTION_PROMPT)
