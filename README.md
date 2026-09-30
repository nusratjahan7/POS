# POS — Point of Sale Platform

A production-oriented Point of Sale system. Separate Next.js frontend and FastAPI
backend that communicate exclusively over a versioned REST API (`/api/v1`).

```
POS/
├── backend/     FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL
├── frontend/    Next.js (App Router) + TypeScript + Tailwind + shadcn/ui
└── docker-compose.yml   Local PostgreSQL (and optional Redis)
```

## Architecture rules (non-negotiable)

- The frontend never talks to the database and never holds business logic.
- All business rules are validated in the FastAPI service layer; frontend
  validation exists purely for UX.
- Authorization is enforced server-side on every protected endpoint.
  Frontend permission checks are cosmetic.
- Money is never represented as a float — `Numeric`/`Decimal` in the backend,
  minor-unit integers or validated decimal strings on the wire.
- Schema changes always ship with an Alembic migration.
- Secrets come from environment variables only.
- Multi-tenant ready: every branch-scoped row carries a `branch_id`.

## Prerequisites

| Tool           | Version    | Notes                                        |
| -------------- | ---------- | -------------------------------------------- |
| Python         | ≥ 3.12     | 3.13 tested                                  |
| uv             | latest     | `pip install uv`                             |
| Node.js        | ≥ 20       | 24 tested                                    |
| Docker         | latest     | for local PostgreSQL                         |

## Quick start

### 1. Infrastructure

```bash
docker compose up -d            # PostgreSQL on localhost:5432
```

### 2. Backend

```bash
cd backend
cp .env.example .env            # adjust secrets for anything non-local
uv sync                         # create venv + install deps
uv run alembic upgrade head     # apply migrations
uv run python -m app.scripts.seed   # create permissions, roles, superuser
uv run uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/api/v1/openapi.json
- Health: http://localhost:8000/api/v1/health

Default seeded superuser (override via `backend/.env`):

```
email:    admin@pos.local
password: ChangeMe123!
```

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev                     # http://localhost:3000
```

## Testing

```bash
# Backend (requires PostgreSQL; uses TEST_DATABASE_URL)
cd backend && uv run pytest

# Frontend
cd frontend && npm run test
```

## Common commands

```bash
# Backend
uv run alembic revision --autogenerate -m "message"   # new migration
uv run alembic upgrade head                           # apply
uv run alembic downgrade -1                           # roll back one
uv run ruff check . && uv run ruff format .           # lint + format
uv run mypy app                                       # type check

# Frontend
npm run lint
npm run typecheck
npm run build
```

## API conventions

- Versioned prefix: `/api/v1`.
- Errors share one envelope:
  ```json
  { "error": { "code": "not_found", "message": "…", "details": [] } }
  ```
- Collections return `{ "items": [...], "total": n, "page": n, "page_size": n, "pages": n }`.
- Query parameters: `page`, `page_size`, `search`, `sort`, plus resource filters.
- Auth: `Authorization: Bearer <access_token>`; refresh token is an httpOnly cookie.

## Modules delivered so far

| Module                | Status |
| --------------------- | ------ |
| Foundation + Auth     | ✅     |
| Sales Management      | ✅     |
| Sales Returns & Refunds | ✅   |
| Dues Management (Customer & Supplier Ledgers) | ✅ |

See `backend/README.md` and `frontend/README.md` for module-level detail.
