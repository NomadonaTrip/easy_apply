"""
LLM prompts for cover letter generation (Epic 5, Stories 5-1/5-3).

Generates a tailored cover letter using candidate experience, company research,
keyword priorities, tone preference, and optional manual context.

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
    {tone}              - One of: formal, conversational, match_culture

Observability:
    prompt_name="generation_cover_letter" for the user prompt
    prompt_name="generation_cover_letter_system" for the system prompt
"""

from app.llm.prompts import PromptRegistry

COVER_LETTER_GENERATION_PROMPT = """You are an expert cover letter writer creating a tailored cover letter.

## CANDIDATE IDENTITY (from uploaded resume)

{candidate_header}

CRITICAL: Extract the candidate's ACTUAL full name from the text above. Sign the letter with the REAL name - never use placeholder text.

## CANDIDATE BACKGROUND

### Key Skills:
{skills}

### Certifications:
{certifications}

### Notable Accomplishments (grouped by role):
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

### Keywords to Incorporate:
{keywords}

## TONE GUIDANCE

Requested tone: {tone}

- **formal**: Professional, traditional business letter style. Use complete sentences, measured language, and conventional structure.
- **conversational**: Warm but professional. More personal voice, shorter sentences, approachable without being casual.
- **match_culture**: Match the company's communication style as evidenced by their research data. Mirror their formality level, energy, and vocabulary.

## INSTRUCTIONS

1. Open with a compelling hook that shows genuine interest in this specific role
2. Connect your experience to their specific needs using the keywords
3. Reference something specific from company research to demonstrate knowledge
4. Highlight 2-3 most relevant accomplishments with concrete details
5. Close with a clear, confident call to action
6. Sign with the candidate's REAL name from the Candidate Identity section
7. If research gaps exist (noted above), focus on the role requirements and demonstrated skills rather than company-specific references for those areas
8. If additional context from the applicant is provided, weave it in naturally

## OUTPUT CONSTRAINTS (CRITICAL)

- NO em-dashes (-) - use hyphens (-) instead
- NO en-dashes (-) - use hyphens (-) instead
- NO smart quotes - use straight quotes only
- NO AI cliche terms: "leverage", "synergy", "spearhead", "utilize"
- NO generic openings: "I am writing to apply for..."
- NO "I believe I would be a great fit" - show, don't tell
- Keep to 3-4 paragraphs maximum (150-400 words)
- Be specific and genuine
- Write as plain text (no markdown formatting)

## OUTPUT FORMAT

Return the cover letter as clean text (no markdown headers):

Dear [Hiring Manager / specific name if known],

[Opening paragraph - hook and specific position reference]

[Body paragraph 1 - relevant experience and achievements tied to their needs]

[Body paragraph 2 - company-specific connection and cultural alignment]

[Closing paragraph - confident call to action]

Sincerely,
[Actual candidate name from Candidate Identity above]

Generate the cover letter now:
"""

COVER_LETTER_SYSTEM_PROMPT = """You write compelling, personalized cover letters that:
- Sound authentically human, not AI-generated
- Connect candidate experience to specific job requirements
- Show genuine knowledge of the target company
- Are concise and impactful (under 400 words)
- Match the requested tone precisely
- Use concrete details and specific examples, never generic claims
- ALWAYS use the candidate's real name - never placeholders"""

# Register prompts
PromptRegistry.register("generation_cover_letter", COVER_LETTER_GENERATION_PROMPT)
PromptRegistry.register("generation_cover_letter_system", COVER_LETTER_SYSTEM_PROMPT)
