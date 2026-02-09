"""
LLM prompts for company/role research (Epic 4).

All prompts serve one core question: Why does [company] need this [role] at this time?

Research serves two distinct purposes:
- Content positioning (WHAT to write): strategic_initiatives, competitive_landscape,
  news_momentum, industry_context
- Tone calibration (HOW to write it): culture_values, leadership_direction
"""

from app.llm.prompts import PromptRegistry

STRATEGIC_INITIATIVES_PROMPT = """Research {company_name}'s strategic initiatives to understand why they might be hiring.

Investigate:
1. What is the company building, expanding, or transforming right now?
2. What strategic bets are they making? (new markets, products, technologies)
3. What growth areas or transformation efforts are underway?
4. Any recent pivots, expansions, or major strategic shifts?
5. What problems are they trying to solve that would require new talent?

Job posting for context:
{job_posting_summary}

Synthesize findings into strategic context that explains why this role exists now.
Focus on publicly available information from company blog, press releases, earnings calls, and news."""

COMPETITIVE_LANDSCAPE_PROMPT = """Analyze {company_name}'s competitive landscape and market position.

Investigate:
1. Who are the top 3-5 direct competitors?
2. How does {company_name} differentiate itself?
3. What is their market position (leader, challenger, niche player)?
4. What competitive pressures might drive hiring for this type of role?
5. Growth trajectory compared to competitors

Job posting for context:
{job_posting_summary}

Provide competitive context that would help a candidate understand the strategic environment."""

NEWS_MOMENTUM_PROMPT = """Search for recent news and momentum signals about {company_name} from the last 6-12 months.

Find and summarize:
1. Product launches or major feature releases
2. Funding rounds or financial milestones (revenue, IPO, earnings)
3. Strategic partnerships or acquisitions
4. Major hires or organizational changes
5. Industry recognition or awards
6. Any challenges, pivots, or market shifts

Prioritize developments that signal why this company is hiring now and what kind of candidate they need."""

INDUSTRY_CONTEXT_PROMPT = """Research the industry context surrounding {company_name}.

Investigate:
1. What market trends are driving their industry?
2. What regulatory shifts or compliance requirements affect them?
3. What technology changes are reshaping their space?
4. What macro-economic or sector-specific challenges exist?
5. How is the industry evolving and what does that mean for talent needs?

Job posting for context:
{job_posting_summary}

Provide industry context that helps explain why this role matters in the current environment."""

CULTURE_VALUES_PROMPT = """Research {company_name}'s culture and values as they present themselves publicly.

Investigate:
1. Core values stated on their website, careers page, or about page
2. How they describe their work environment and team culture
3. What they publicly prioritize (innovation, collaboration, speed, quality, etc.)
4. Employer branding messages and tone
5. Any notable cultural identity markers (engineering-driven, customer-obsessed, etc.)

This research is for TONE CALIBRATION - understanding how the company sees itself
so application materials can emotionally resonate with their identity.

Focus on the company's own voice, not external reviews."""

LEADERSHIP_DIRECTION_PROMPT = """Research the strategic direction articulated by {company_name}'s leadership.

Investigate:
1. CEO/founder public statements about company direction and vision
2. Executive blog posts, conference talks, or interviews
3. Leadership backgrounds that signal strategic priorities (e.g., CEO from payments vs infrastructure)
4. Publicly stated goals, OKRs, or priorities
5. Any leadership changes that signal strategic shifts

Job posting for context:
{job_posting_summary}

Focus on STRATEGIC VISION and DIRECTION, not personal career histories.
This research enables tone calibration - understanding how leaders think so application
materials can speak their language."""

SYNTHESIS_PROMPT = """You are a strategic analyst synthesizing company research for a job application.

Based on the following research findings about {company_name}, answer the core question:
**"Why does {company_name} need this role at this time?"**

Research findings:
{research_findings}

Job posting summary:
{job_posting_summary}

Create a strategic narrative (3-5 paragraphs) that:
1. Connects the company's strategic direction to the role requirements
2. Identifies the key business problems this hire is meant to solve
3. Highlights timing signals (why NOW, not 6 months ago or later)
4. Suggests positioning angles for the candidate's application materials

Write in a confident, analytical tone. Be specific and cite the research where possible."""

# Register all prompts
PromptRegistry.register("research_strategic_initiatives", STRATEGIC_INITIATIVES_PROMPT)
PromptRegistry.register("research_competitive_landscape", COMPETITIVE_LANDSCAPE_PROMPT)
PromptRegistry.register("research_news_momentum", NEWS_MOMENTUM_PROMPT)
PromptRegistry.register("research_industry_context", INDUSTRY_CONTEXT_PROMPT)
PromptRegistry.register("research_culture_values", CULTURE_VALUES_PROMPT)
PromptRegistry.register("research_leadership_direction", LEADERSHIP_DIRECTION_PROMPT)
PromptRegistry.register("research_synthesis", SYNTHESIS_PROMPT)
