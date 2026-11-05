# Architecture — HOW
Existing: FastAPI (app.py) · Jinja2 templates · SQLAlchemy (SQLite default, PostgreSQL via DATABASE_URL) · session cookies.

## Additive design
```
app.py  ──(3 lines at the end)──▶  extras/__init__.py  (router)
                                     ├─ models.py   new tables, share app.Base
                                     ├─ data.py     questions, careers, roadmaps, FAQ, plans, badges (pure data)
                                     ├─ logic.py    pure functions: scoring, matching, points, FAQ search (unit-testable)
                                     └─ routes.py   HTTP layer (thin)
templates/x_*.html   new pages (extend base.html)
static/extras.css, extras.js
tests/               pytest + FastAPI TestClient
```
## Rules
- No UI file contains DB logic beyond reading context from routes.
- Business logic lives in `logic.py` (no HTTP, no DB) so it is testable.
- Existing helpers (`render`, `must_login`, `require_csrf`, `validate_text`) are reused, never duplicated.
- New tables only (`x_*` prefix). Existing tables are never altered.
- Points are idempotent: unique (user_id, action, ref).
