# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Easy Apply is an AI-powered job application tracker and resume tailoring tool. Full-stack monorepo with React frontend and FastAPI backend, designed for 2 users running on local network.

## Development Commands

### Backend (from `backend/` directory)
```bash
source .venv/bin/activate              # Activate venv
uv pip install -e ".[dev]"             # Install with dev dependencies
uvicorn app.main:app --reload          # Dev server (port 8000)
pytest -v                              # Run all tests
pytest tests/test_auth.py -v           # Single test file
pytest -k "test_login" -v              # Tests matching pattern
ruff check .                           # Lint
```

### Frontend (from `frontend/` directory)
```bash
npm run dev              # Vite dev server (port 5173)
npm run build            # Production build (tsc + vite)
npm run lint             # ESLint
npm run test:run         # Run Vitest once
```

### API Documentation
- Swagger UI: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health

## Architecture

### Tech Stack
- **Frontend:** React 19 + TypeScript + Vite, Zustand (state), TanStack Query (data fetching), shadcn/ui + Tailwind CSS
- **Backend:** FastAPI + Python 3.11+, SQLModel ORM, SQLite (WAL mode), bcrypt session auth
- **LLM:** Google Gemini via `google-genai` SDK with provider abstraction layer

### Project Structure
```
frontend/src/
├── api/           # API client with auto role header injection
├── components/    # UI components (shadcn/ui in ui/)
├── pages/         # Route pages
├── stores/        # Zustand stores (authStore, roleStore)
└── hooks/         # Custom React hooks

backend/app/
├── api/v1/        # FastAPI routes
├── models/        # SQLModel database models
├── services/      # Business logic (owns DB sessions)
├── utils/         # Pure utility functions
└── llm/           # LLM provider abstraction
    ├── providers/ # Gemini implementation
    ├── prompts/   # Prompt registry (all prompts externalized here)
    └── tools/     # WebSearch, WebFetch tool implementations
```

## Critical Backend Patterns

### Service Layer Session Management
Services manage their own DB sessions. **All returned objects must be expunged:**
```python
async with async_session_maker() as session:
    result = await session.execute(query)
    obj = result.scalar_one_or_none()
    if obj:
        session.expunge(obj)  # REQUIRED before returning
    return obj
```
Forgetting `session.expunge()` causes `DetachedInstanceError` when accessing returned objects outside the session context.

### Role Isolation
All data queries must be scoped to `role_id`. The frontend auto-injects `X-Role-Id` header via `apiRequest()` in `api/client.ts`. Backend validates ownership via `get_current_role` dependency in `api/deps.py`. Every role-scoped service method should include:
```python
if role_id is None:
    raise ValueError("role_id is required - data isolation violation")
```

### Application Status State Machine
Strict transitions enforced in `api/v1/applications.py`:
```
created → keywords → researching → reviewed → generating → exported → sent → callback/offer/closed
```
Invalid transitions return 422. The `VALID_TRANSITIONS` dict is the source of truth.

### Database: No Migrations
SQLModel's `create_all()` handles table creation. For adding columns to existing tables, use the `_ensure_columns` pattern in `database.py` (PRAGMA table_info + ALTER TABLE). WAL mode and foreign keys enabled via SQLite PRAGMAs on every connection.

### SQLModel Table Models
Table models (`table=True`) bypass Pydantic validation. Use manual validation in `__init__`:
```python
class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.name or len(self.name.strip()) < 1:
            raise ValueError("name cannot be empty")
```

### HTML Sanitization
Manual context writes go through a dedicated `PATCH /{id}/context` endpoint that applies `html.escape()`. The `manual_context` field is excluded from `ApplicationUpdate` to enforce this single write path.

## LLM Operations

### Provider Factory (Singleton)
```python
from app.llm import get_llm_provider
provider = get_llm_provider()  # Returns InstrumentedProvider wrapping Gemini
```
Every call is automatically instrumented with timing, structured logging, and optional DB persistence. Observability failures never break functionality (fire-and-forget).

### Prompt Registry
All prompts externalized in `app/llm/prompts/`. **No inline prompt strings in service files.**
```python
from app.llm.prompts import PromptRegistry
prompt = PromptRegistry.get("keyword_extraction", job_posting=text)
```
Prompts auto-register on module import.

### Retry & Resilience
- `generate_with_retry()` in `utils/llm_helpers.py`: 3 attempts, exponential backoff (5s, 10s, 20s) on 429 rate limits
- `RatePacer`: Enforces minimum interval between LLM calls (asyncio lock)
- `CircuitBreaker`: Three-state (closed → open → half-open), opens after 3 consecutive failures, resets after 60s

### Output Constraints
Post-generation enforcement in `utils/text_processing.py` and `utils/constraints.py`:
- Auto-replaces em-dashes, smart quotes, ellipsis, bullets
- Detects AI cliches (70+ terms) — logged as warnings, not auto-replaced
- ATS formatting validation (tables, long lines)
- `enforce_output_constraints_detailed()` returns `ConstraintResult` with cleaned text + violation metadata

### JSON Extraction
LLM responses often wrap JSON in markdown code blocks. Use `extract_json_from_response()` from `utils/llm_helpers.py`.

## Frontend Patterns

### API Client & Role Header
`api/client.ts` `apiRequest()` auto-injects `X-Role-Id` header for role-scoped endpoints. Auth endpoints and `/roles` are excluded. Throws if no role selected for role-scoped requests.

### TanStack Query Conventions
- Query keys include `roleId`: `['applications', roleId]`
- Queries use `enabled: !!roleId` to prevent fetching without a role
- Mutations invalidate related query keys on success
- Global 401 handler clears auth state automatically (`lib/queryClient.ts`)
- Defaults: `staleTime: 30s`, `gcTime: 5min`, `retry: 1` for queries

### Zustand Stores
- `roleStore`: Persisted to localStorage. Changing role invalidates all role-scoped query caches. Clearing role clears all caches.
- `authStore`: Coordinates with roleStore on logout (cross-store).
- Zustand for client-side state only. All server state via TanStack Query.

### SSE Integration
Research progress streams via `text/event-stream`. Backend uses `SSEManager` singleton with per-application `asyncio.Queue`. Research runs as `BackgroundTasks`. Frontend connects to `/research/stream` endpoint.

## Testing

### Backend Test Infrastructure
- `conftest.py` provides session-scoped test DB setup (`settings.testing = True` switches DB URL)
- Function-scoped `clean_database` fixture: raw SQL DELETE in FK dependency order (avoids ORM autoflush issues)
- `client` fixture (sync TestClient) and `async_client` fixture (AsyncClient for SSE tests)
- `pytest-asyncio` mode: `strict` — all async tests need `@pytest.mark.asyncio`
- LLM calls in tests: mock via `patch("app.services.generation_service.generate_with_retry", new_callable=AsyncMock)`

### Frontend Test Patterns
- Vitest + React Testing Library
- Mock API modules with `vi.mock('@/api/applications', () => ({...}))`
- Wrap components in `QueryClientProvider` + `MemoryRouter` for tests
- Mock `Application` objects must include all interface fields (TypeScript enforced)

## Naming Conventions

### Backend (Python)
- Files: `snake_case` — Classes: `PascalCase` — Functions/vars: `snake_case`
- API endpoints: `kebab-case` for multi-word (e.g., `/cover-letters`)
- JSON responses: `snake_case`

### Frontend (TypeScript/React)
- Components: `PascalCase` files and names
- Hooks: `camelCase` with `use` prefix
- Stores: `camelCase` with `Store` suffix

### Database
- Tables: `snake_case`, plural — Columns: `snake_case` — Foreign keys: `{table_singular}_id`

## Environment Variables

Backend `.env` file (see `.env.example`):
- `LLM_API_KEY` - Required for Gemini API
- `LLM_PROVIDER` - Default: `gemini`
- `LLM_MODEL` - Default: `gemini-2.0-flash-exp`
- `SERPER_API_KEY` - Optional, enables web search tool
- `DEBUG` - Default: `false`

## BMAD Workflow

This repo uses a BMAD (Business-Method-Automated-Development) framework in `_bmad/` for AI-assisted development workflows. Sprint tracking lives in `_bmad-output/implementation-artifacts/sprint-status.yaml`. Story files live in `_bmad-output/implementation-artifacts/`. The `_bmad/` directory is tooling infrastructure, not application code.
