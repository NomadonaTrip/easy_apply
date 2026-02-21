"""
LLM prompts for resume generation (Epic 5, Stories 5-1/5-2).

Generates a tailored resume using candidate experience, company research,
keyword priorities, and optional manual context.

Prompt placeholders:
    {candidate_header}  - First ~500 chars of resume text (name, contact, summary)
    {skills}            - Formatted skills from experience database
    {certifications}    - Certifications/qualifications separated from skills
    {accomplishments}   - Role-grouped accomplishments from experience database
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

## CANDIDATE IDENTITY (from uploaded resume)

{candidate_header}

CRITICAL: Extract the candidate's ACTUAL full name and contact information from the text above. Use the REAL name - never use placeholder text like "[Candidate Name]" or "[Your Name]".

## CANDIDATE EXPERIENCE DATABASE

### Skills:
{skills}

### Certifications:
{certifications}

CRITICAL: ALL certifications listed above MUST appear in the final resume under Education or a dedicated Certifications section. Do not omit any.

### Experience (grouped by company):
{accomplishments}

CRITICAL: Each company and date range combination MUST appear EXACTLY ONCE in the Experience section. Do NOT duplicate companies. Place each accomplishment under its original company heading only.
When multiple role titles are listed for the same company (separated by "/"), pick one and adjust its language to best fit the target job description. For example, if the target role is "Backend Engineering Lead" and source titles are "Senior Developer / Lead Engineer", you might use "Lead Backend Engineer". Do NOT list multiple titles -- produce a single, tailored title.

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

### Identity & Structure
1. Use the candidate's REAL name and contact info from the Candidate Identity section above
2. Preserve the company-accomplishment grouping from the Experience section - each company+dates combination appears exactly once
3. Include ALL certifications from the Certifications section
4. Structure with clear sections: Summary, Experience, Skills, Education/Certifications

### Keyword Coverage (CRITICAL)
5. Every MUST-HAVE keyword (priority 8-10) MUST appear at least once in the final resume. Target 100% must-have coverage.
6. Place technical_skill keywords in BOTH the Skills section AND at least one Experience bullet
7. Place tool keywords in Skills AND mention in relevant Experience context
8. Demonstrate soft_skill keywords through action verbs in Experience bullets (e.g., for "leadership" write "Led a team of 8 engineers...")
9. Place qualification keywords in Education/Certifications or Summary as appropriate
10. IMPORTANT keywords (priority 5-7) should appear where they naturally fit. Target 80%+ coverage.

### JD Language Mirroring (CRITICAL)
11. Use the EXACT phrases and terminology from the job posting. If the JD says "microservices architecture", write "microservices architecture" - not "distributed systems". If it says "CI/CD pipelines", write "CI/CD pipelines" - not "continuous integration".
12. Mirror the JD's phrasing for years of experience, tools, methodologies, and domain terms
13. Echo the job title language in the Professional Summary

### Accomplishment Prioritization
14. Lead each company section with accomplishments tagged [Relevant to: ...] - these are the most JD-aligned
15. Within each company, prioritize JD-relevance over chronological ordering
16. Be specific and quantify achievements where possible

### Context Integration
17. Use company research to align language and values
18. If research gaps exist (noted above), focus on demonstrated skills rather than company-specific positioning for those areas
19. If additional context from the applicant is provided, incorporate it naturally

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

Return the resume as clean markdown. The name and contact info MUST be real (from Candidate Identity above):

# [Actual candidate name from above]

[Actual contact info: email, phone, location from above]

## Professional Summary

[2-3 sentences tailored to this role]

## Experience

### [Job Title] | [Company] | [Dates]
- [Achievement with metrics]
- [Achievement with metrics]

## Skills

[Comma-separated list organized by category]

## Education & Certifications

[Degrees and ALL certifications from the list above]

Generate the resume now:
"""

RESUME_SYSTEM_PROMPT = """You are an expert resume writer. Your resumes are:
- Tailored specifically to each job posting using the EXACT terminology from the job description - never paraphrase key terms
- Keyword-optimized for ATS systems - every MUST-HAVE keyword appears at least once
- Free of AI-sounding language
- Focused on quantifiable achievements
- Professionally formatted in clean markdown
- Written in active voice with concrete, specific language
- Prioritize accomplishments tagged [Relevant to: ...] as they match the JD
- ALWAYS use the candidate's real name and contact info - never placeholders"""

# Register prompts
PromptRegistry.register("generation_resume", RESUME_GENERATION_PROMPT)
PromptRegistry.register("generation_resume_system", RESUME_SYSTEM_PROMPT)
