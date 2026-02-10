"""
LLM prompts for resume generation (Epic 5, Stories 5-1/5-2).

Generates a tailored resume using candidate experience, company research,
keyword priorities, and optional manual context.

Prompt placeholders:
    {skills}            - Formatted skills from experience database
    {accomplishments}   - Formatted accomplishments from experience database
    {company_name}      - Target company name
    {job_posting}       - Full job description text
    {research_context}  - Output from build_research_context() in llm_helpers.py
    {gap_note}          - Gap note from build_research_context(), or empty string
    {manual_context}    - User-provided manual context from Story 4-6, or empty string
    {keywords}          - Keyword priorities in numbered list format

Observability:
    prompt_name="generation_resume" for the user prompt
    prompt_name="generation_resume_system" for the system prompt
"""

from app.llm.prompts import PromptRegistry

RESUME_GENERATION_PROMPT = """You are an expert resume writer creating a tailored resume for a job application.

## CANDIDATE EXPERIENCE DATABASE

### Skills:
{skills}

### Accomplishments:
{accomplishments}

## TARGET POSITION

### Company: {company_name}

### Job Posting:
{job_posting}

### Company Research:
{research_context}

{gap_note}

### Additional Context from Applicant:
{manual_context}

### Keywords (in priority order):
{keywords}

## INSTRUCTIONS

1. Create a professional resume tailored to this specific position
2. Emphasize skills and accomplishments that match the keywords (in priority order)
3. Use the company research to align language and values
4. Structure with clear sections: Summary, Experience, Skills, Education
5. Be specific and quantify achievements where possible
6. If research gaps exist (noted above), focus on demonstrated skills and experience rather than company-specific positioning for those areas
7. If additional context from the applicant is provided, incorporate it naturally

## OUTPUT CONSTRAINTS (CRITICAL)

- NO em-dashes (-) - use hyphens (-) instead
- NO en-dashes (-) - use hyphens (-) instead
- NO smart quotes - use straight quotes only
- NO AI cliche terms: "leverage", "synergy", "spearhead", "utilize", "facilitate"
- NO overused phrases: "passionate about", "results-driven", "team player"
- Use active voice and concrete language
- ATS-optimized formatting (no tables, columns, or graphics)
- Maximum 2 pages worth of content (approximately 800 words)

## OUTPUT FORMAT

Return the resume as clean markdown with the following structure:

# [Candidate Name]

[Contact info placeholder]

## Professional Summary

[2-3 sentences tailored to this role]

## Experience

### [Job Title] | [Company] | [Dates]
- [Achievement with metrics]
- [Achievement with metrics]

## Skills

[Comma-separated list organized by category]

## Education

[Degrees and certifications]

Generate the resume now:
"""

RESUME_SYSTEM_PROMPT = """You are an expert resume writer. Your resumes are:
- Tailored specifically to each job posting
- Keyword-optimized for ATS systems
- Free of AI-sounding language
- Focused on quantifiable achievements
- Professionally formatted in clean markdown
- Written in active voice with concrete, specific language"""

# Register prompts
PromptRegistry.register("generation_resume", RESUME_GENERATION_PROMPT)
PromptRegistry.register("generation_resume_system", RESUME_SYSTEM_PROMPT)
