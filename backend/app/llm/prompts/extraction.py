"""LLM prompts for skill and accomplishment extraction."""

SKILL_EXTRACTION_PROMPT = """
Analyze the following resume text and extract all professional skills.

Resume Text:
{resume_text}

Instructions:
1. Identify both hard skills (technical abilities) and soft skills
2. Categorize each skill (e.g., "Programming", "Leadership", "Tools", "Domain Knowledge")
3. Include tools, technologies, methodologies, and certifications
4. Be comprehensive but avoid duplicates

Return a JSON array of skills with this structure:
{{
  "skills": [
    {{"name": "Python", "category": "Programming"}},
    {{"name": "Project Management", "category": "Leadership"}},
    {{"name": "AWS", "category": "Cloud"}}
  ]
}}

Return ONLY the JSON, no other text.
"""

ACCOMPLISHMENT_EXTRACTION_PROMPT = """
Analyze the following resume text and extract notable accomplishments.

Resume Text:
{resume_text}

Instructions:
1. Identify specific achievements with measurable outcomes when possible
2. Include context (role, company, or project when mentioned)
3. Focus on impact and results, not just responsibilities
4. Rephrase vague statements into concrete accomplishments
5. Extract the company name, role title, and employment dates as separate fields when available

Return a JSON array of accomplishments with this structure:
{{
  "accomplishments": [
    {{
      "description": "Led migration to microservices, reducing deployment time by 60%",
      "context": "Senior Engineer at TechCorp",
      "company_name": "TechCorp",
      "role_title": "Senior Engineer",
      "dates": "2020-2024"
    }},
    {{
      "description": "Grew team from 3 to 12 engineers while maintaining velocity",
      "context": "Engineering Manager at StartupCo",
      "company_name": "StartupCo",
      "role_title": "Engineering Manager",
      "dates": "2018-2020"
    }}
  ]
}}

Notes:
- "context" is a human-readable summary of the role (keep for backward compatibility)
- "company_name" is ONLY the company/organization name
- "role_title" is ONLY the job title
- "dates" is the employment period (e.g., "2020-2024", "Jan 2020 - Present")
- If any field is unknown, set it to null

Return ONLY the JSON, no other text.
"""

from app.llm.prompts import PromptRegistry  # noqa: E402

PromptRegistry.register("skill_extraction", SKILL_EXTRACTION_PROMPT)
PromptRegistry.register("accomplishment_extraction", ACCOMPLISHMENT_EXTRACTION_PROMPT)
