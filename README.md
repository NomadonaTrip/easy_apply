# Easy Apply

AI-powered job application tracker and resume tailoring tool.

## Tech Stack

- **Frontend:** React 19 + TypeScript + Vite
- **UI Components:** shadcn/ui (Radix primitives) + Tailwind CSS
- **State Management:** Zustand + TanStack Query
- **Backend:** FastAPI + Python 3.11+
- **Database:** SQLite with WAL mode
- **ORM:** SQLModel

## Project Structure

```
easy_apply/
├── frontend/          # Vite + React + shadcn/ui
├── backend/           # FastAPI + Python
├── data/              # SQLite database
└── .claude/skills/    # Claude Code skills
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- uv (recommended) or pip

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

### Backend Setup

```bash
cd backend
uv venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

uv pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000

### API Documentation

- Swagger UI: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health

## Development

### Running Tests

```bash
cd backend
pytest -v
```

### Linting

```bash
# Frontend
cd frontend && npm run lint

# Backend
cd backend && ruff check .
```

## Architecture

The application uses a monorepo structure with separate frontend and backend projects. The frontend proxies `/api/*` requests to the backend during development.

See `_bmad-output/planning-artifacts/architecture.md` for detailed architecture documentation.
