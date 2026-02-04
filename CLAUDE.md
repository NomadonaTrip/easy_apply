# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Easy Apply is an AI-powered job application tracker and resume tailoring tool. It's a full-stack monorepo with a React frontend and FastAPI backend, designed for 2 users running on local network.

## Development Commands

### Frontend (from `frontend/` directory)
```bash
npm install              # Install dependencies
npm run dev              # Start Vite dev server (port 5173)
npm run build            # Production build (tsc + vite)
npm run lint             # Run ESLint
npm run test             # Run Vitest in watch mode
npm run test:run         # Run Vitest once
npm run test:coverage    # Generate coverage report
```

### Backend (from `backend/` directory)
```bash
uv venv .venv                      # Create virtual environment
source .venv/bin/activate          # Activate venv (Linux/Mac)
uv pip install -e ".[dev]"         # Install with dev dependencies
uvicorn app.main:app --reload      # Run dev server (port 8000)
pytest -v                          # Run all tests
pytest tests/test_auth.py -v       # Run single test file
pytest -k "test_login" -v          # Run tests matching pattern
ruff check .                       # Lint with Ruff
```

### API Documentation
- Swagger UI: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health

## Architecture

### Tech Stack
- **Frontend:** React 19 + TypeScript + Vite, Zustand (state), TanStack Query (data fetching), shadcn/ui + Tailwind CSS
- **Backend:** FastAPI + Python 3.11+, SQLModel ORM, SQLite (WAL mode), bcrypt auth
- **LLM Integration:** Google Gemini via `google-genai` SDK with provider abstraction layer

### Project Structure
```
easy_apply/
├── frontend/src/
│   ├── api/           # API client (client.ts, auth.ts)
│   ├── components/    # UI components (shadcn/ui in ui/)
│   ├── pages/         # Route pages
│   ├── stores/        # Zustand stores (authStore, appStore)
│   ├── hooks/         # Custom React hooks
│   └── lib/           # Utilities
│
├── backend/app/
│   ├── api/v1/        # FastAPI routes (auth.py, roles.py)
│   ├── models/        # SQLModel database models
│   ├── services/      # Business logic layer
│   └── llm/           # LLM provider abstraction
│       ├── providers/ # Gemini implementation
│       ├── tools/     # WebSearch, WebFetch tools
│       └── skills/    # Skill markdown files
│
└── data/              # SQLite database (easy_apply.db)
```

### Key Architectural Patterns

**Service Layer Pattern:** Services manage their own database sessions using `async_session_maker()` context managers. All returned objects must be expunged from session:
```python
async with async_session_maker() as session:
    result = await session.execute(query)
    obj = result.scalar_one_or_none()
    if obj:
        session.expunge(obj)  # Required before returning
    return obj
```

**Role Isolation:** All data queries must be scoped to `role_id`. The `X-Role-Id` header is validated via `get_current_user` dependency injection.

**Authentication:** Session-based with HTTP-only cookies. Password hashing via bcrypt.

**Frontend Data Flow:** TanStack Query for all API data fetching. Zustand only for client-side state (auth, active role).

### API Routes
- `/api/v1/auth/*` - Public: login, register, logout, me
- `/api/v1/roles/*` - Authenticated: role CRUD (requires session cookie)
- All role-scoped endpoints use `X-Role-Id` header

## Naming Conventions

### Backend (Python)
- Files/modules: `snake_case` (e.g., `auth_service.py`)
- Classes: `PascalCase` (e.g., `AuthService`)
- Functions/variables: `snake_case`
- API endpoints: `kebab-case` for multi-word (e.g., `/cover-letters`)
- JSON responses: `snake_case`

### Frontend (TypeScript/React)
- Components: `PascalCase` files and names (e.g., `ApplicationCard.tsx`)
- Hooks: `camelCase` with `use` prefix (e.g., `useApplications.ts`)
- Stores: `camelCase` with Store suffix (e.g., `authStore.ts`)
- Utilities: `camelCase`

### Database
- Tables: `snake_case`, plural (e.g., `users`, `roles`)
- Columns: `snake_case` (e.g., `user_id`, `created_at`)
- Foreign keys: `{table_singular}_id`

## SQLModel Table Models

SQLModel table models (`table=True`) bypass Pydantic validation. Use manual validation in `__init__`:
```python
class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.name or len(self.name.strip()) < 1:
            raise ValueError("name cannot be empty")
```

Schema classes (without `table=True`) use Pydantic validation normally.

## Environment Variables

Backend requires `.env` file (see `.env.example`):
- `LLM_API_KEY` - Required for Gemini API
- `LLM_PROVIDER` - Default: gemini
- `LLM_MODEL` - Default: gemini-2.0-flash-exp
- `SERPER_API_KEY` - Optional, for web search tool
- `DEBUG` - Default: false
