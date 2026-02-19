"""LLM prompt for experience enrichment analysis."""

ENRICHMENT_ANALYSIS_PROMPT = """
Analyze the following document and identify NEW skills and accomplishments that are NOT already in the user's experience database.

Document Content:
{document_content}

Existing Skills (already in database - DO NOT include these or near-duplicates):
{existing_skills}

Existing Accomplishments (already in database - DO NOT include these or near-duplicates):
{existing_accomplishments}

Instructions:
1. Identify skills demonstrated in the document that are NOT in the existing skills list
2. Identify accomplishments described in the document that are NOT in the existing accomplishments list
3. Skip any skill that is a synonym, abbreviation, or minor variation of an existing skill (e.g., "JS" = "JavaScript", "K8s" = "Kubernetes")
4. Skip any accomplishment that restates or rephrases an existing accomplishment
5. Only include genuinely NEW and specific items - avoid overly generic terms like "communication" or "teamwork" unless they are clearly demonstrated with specific context
6. For skills, include a relevant category (e.g., "Programming", "Cloud", "Leadership", "DevOps")
7. For accomplishments, include the context where the accomplishment was demonstrated
8. Limit your response to the 10 most significant new skills and 5 most impactful new accomplishments. Quality over quantity -- only include items that would meaningfully strengthen a future application.

Return a JSON object with this structure:
{{
  "new_skills": [
    {{"name": "Terraform", "category": "Infrastructure"}},
    {{"name": "Event-Driven Architecture", "category": "Architecture"}}
  ],
  "new_accomplishments": [
    {{
      "description": "Designed real-time data pipeline processing 1M events/day",
      "context": "Data Engineering role at StreamCo"
    }}
  ]
}}

If no new skills or accomplishments are found, return:
{{
  "new_skills": [],
  "new_accomplishments": []
}}

Return ONLY the JSON, no other text.
"""

from app.llm.prompts import PromptRegistry  # noqa: E402

PromptRegistry.register("enrichment_analysis", ENRICHMENT_ANALYSIS_PROMPT)
