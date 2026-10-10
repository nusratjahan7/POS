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
| Expenses & Cash Register | ✅ |
| Discounts & Coupons   | ✅     |
| Reporting & Analytics | ✅     |
| Notifications & Audit Logging | ✅     |
| Barcode & Printing    | ✅     |
| Multi-Branch Support  | ✅     |

See `backend/README.md` and `frontend/README.md` for module-level detail.

## Notifications & audit log

Two cross-cutting subsystems, both added in MODULE 20.

**Notifications** are in-app and per-user: actions fan a row out to each recipient
(audience resolved by permission, the actor excluded), so an unread count and read
state are exact. Triggered by: low stock, out of stock, customer due, supplier due,
new sale, refund, and important system events.

- `GET /api/v1/notifications` — your notifications (`unread`, `type` filters).
- `GET /api/v1/notifications/unread-count` — the bell's number.
- `POST /api/v1/notifications/{id}/read` and `POST /api/v1/notifications/read-all`.
- Surfaced in the header bell and at `/notifications`. Guarded by `notifications:read`.

**Audit log** persists sensitive actions (sign-in, product create/update and price
changes, stock adjustments, sale/refund creation, cancellation, user/permission/
settings changes) with actor, action, module, entity, old/new JSON snapshots, IP and
timestamp. Snapshots run through a deep redactor, so a password, hash or token can
never reach the table.

- `GET /api/v1/audit-logs` — newest first, filterable by module/action/user/date.
- Read at `/audit`. Guarded by `audit:read`.

## Multi-branch support

Branch scoping is enforced **server-side** on every branch-scoped endpoint
(MODULE 22) — the frontend selectors only reflect it.

- **`branches:all`** is the grant that means "every branch"; it ships on the
  built-in Administrator role. Superusers bypass as everywhere. Managers do not
  get it.
- **Assignments.** `users.branch_id` stays the *primary/default* branch; a new
  `user_branches` many-to-many holds explicit assignments. A user with no
  assignment falls back to their primary branch, else the first active branch —
  so a single-branch install behaves exactly as before.
- **Reads** are *silently scoped*: a restricted user who omits `branch_id` sees
  only their branches; an explicit out-of-scope `branch_id` is `403`
  (`branch_forbidden`).
- **Writes** are *asserted*: creating/updating a sale, purchase, expense, stock
  movement, register or register session at a branch outside the scope is `403`.
- **`GET /branches/options`** returns only the caller's branches (all for an
  administrator), which is what every selector reads. `GET /branches` remains the
  administration catalogue (`branches:read`/`branches:write`).
- **`/auth/me`** carries `branches` and `all_branches`, so the client can build
  selectors and defaults without a second call.
- Product master data stays global; stock is per branch in `stock_levels`
  (`(product_id, branch_id)`), unchanged — definitions and inventory were already
  separate.

Reusable UI: `components/branch/branch-filter.tsx` (offers only your branches;
adds "All branches" only for the grant holder; renders nothing for a
single-branch user) and `lib/auth/branches.ts` (`canSeeAllBranches`,
`defaultBranchId`, `ALL_BRANCHES`). Users are managed with a branch-access
checklist plus a primary-branch picker.

## Barcode & printing

**Barcode generation** (`frontend/src/lib/barcode/`) supports EAN-13, UPC-A and
Code 128B. The symbology is auto-detected from the value: a valid 13-digit number
renders as EAN-13, a 12-digit number as UPC-A, anything else (internal SKUs, sale
numbers) as Code 128. A value that cannot be encoded renders a small notice instead
of breaking the page, and an EAN/UPC with a bad check digit falls back to Code 128.

- **Scanning**: the register's search field is autofocused and treats a barcode
  scanner as a keyboard (it types the code, then Enter). A scan matches exactly on
  barcode or SKU, is added to the cart with a beep, and an unknown code warns and
  keeps the field focused for the next scan. Misses fall back to the server.
- **Search**: products and the POS catalog accept an exact `?barcode=` filter
  (case-insensitive, never a substring match).

**Printing** produces real text (never a screenshot) sent through a hidden iframe,
so "Save as PDF" works and a pop-up blocker cannot stop it.

- **Thermal receipt** (80 mm) and **A4 invoice** — from any sale, with a live
  preview and layout tabs.
- **Barcode labels** — from the Products list: a per-row action or the bulk
  "Print labels" picker. Two physical layouts: a **50 × 25 mm thermal roll** (one
  label per page) and **A4 sheets of 63.5 × 38.1 mm labels** (3 × 8, 24 per page).
  Each label carries the product name, an optional price, and a scannable barcode
  (the SKU when the product has none).


