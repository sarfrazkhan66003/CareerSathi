# Project Memory (read this first in a new session)
**Status:** v12.3 complete, 84 tests pass (`python -m pytest -q`). Workspace: `/home/claude/CareerSathi-main`. User writes Hinglish; Windows PowerShell (no `&&`; use `python -m uvicorn`).

## Rules the user set
- Do NOT change legacy code; only add. Allowed legacy edits: app.py hook (5 lines at end), base.html/home.html links, auth/login links.
- After EVERY update: update `docs/PRD.md`, `docs/MEMORY.md`, `TASKS.md`, README, so no session needs the full history.
- Never fabricate data. Be honest about limits.

## Architecture in one glance
`app.py` (legacy FastAPI) → hook → `extras/__init__.py` (router + `promote_overrides`: middleware, `/login` + `/journey` overrides, Jinja globals `t`, scheduler, Sentry, `expire_on_commit=False`).
- `extras/data.py, logic.py, models.py, routes.py` — v11 (quiz, roadmaps, match, rewards, parent, plans, resume, FAQ).
- `extras/data2.py` (Hindi map, grades, streams, exams, purposes), `models2.py` (x_* v12 tables), `services.py` (SMTP/outbox, Razorpay, Claude, Turnstile),
  `assess.py + assess_data.py` (84-MCQ bank, scoring), `routes2.py` (verify/reset/consent/login guard/start/assessments/enquiry/mentor allotment),
  `routes3.py` (payments, slots, video, notifications, reminders, school), `routes4.py` (practice, progress, certificate, blog, sitemap, scholarships, predictor, stories, reviews, internships, language, PWA, admin hub/analytics/audit/import).
- Templates `templates/x_*.html`; assets `static/extras.css|js`; tests `tests/test_extras.py` (v11), `tests/test_v12.py`.

## v12.3 quick facts (latest)
- Navbar CSS/JS are INLINE (`templates/_nav_css.html`, `_nav_js.html`); assets use `?v={{ asset_v }}`. If the user sees an old look: hard refresh Ctrl+Shift+R. Never put critical nav rules only in `extras.css`.
- Specificity trap: `.links>a` beats `.x{}`; use `.links>a.only-mobile`.
- Assessment run page: one question at a time (`x_assess_run.html` JS), server re-renders with `incomplete` + `prefill` (status 400). `_friendly_errors` in `extras/__init__.py` returns HTML only when `Accept` has `text/html`.
- Always verify UI in a real browser (playwright) incl. stale-CSS case, and take screenshots at 375 and 1440.

## v12.2 quick facts
- Score rule: `extras/data3.py` `THRESHOLD=50`, `SCIENCE=('PCM','PCB','PCMB')`, stream roadmaps + catch-up plan. Helpers `score_info`, `science_locked`, `need_assessment`, `_legacy_gate` in `routes2.py`.
- Overrides prepended in `promote_overrides`: POST `/login`, GET `/journey`, POST `/journey/enquiry`, POST `/journey/assessment`.
- `/admin` redirects (admin → `/admin/dashboard`, others → login/own dashboard). No admin links in base.html on purpose.
- Navbar = dropdowns in `base.html` + `extras.css` + `extras.js`; mobile keeps one row (`.only-mobile` items inside hamburger).
- Contact: email officialcareersathi@gmail.com, Instagram @officialcareersathi in `contact.html` and footer.
- Test helper: `make_user(..., assessed=False)` for gate tests; default attempt has overall 80. Use `take(c, kind, answer_right=False)` to create a genuine low score.

## Key gotchas
- Emails lowercased at login: test emails must be lowercase.
- `tests/conftest.make_user` creates onboarded (consented, verified, assessed) users; pass `assessed=False` / `onboarded=False` to test gates.
- Gate: Class 8–10 students need consent + a finished `XAssessAttempt` before `/dashboard`, `/journey`, `/enquiry`.
- `extras` must be imported after `app` (circular import otherwise). Run via `uvicorn app:app`.
- Newer FastAPI does not list included routes in `app.routes`; use TestClient to check routes.
- Env vars: SECRET_KEY, DATABASE_URL, SITE_URL, SMTP_HOST/PORT/USER/PASSWORD/FROM/TLS, RAZORPAY_KEY_ID/KEY_SECRET/WEBHOOK_SECRET, ANTHROPIC_API_KEY/MODEL, TURNSTILE_SITE_KEY/SECRET, SENTRY_DSN, MENTOR_SESSION_FEE_INR, DISABLE_SCHEDULER, GOOGLE_PLACES_API_KEY.

## Not done / next
Live credentials setup by owner; legal review (DPDP); full Hindi; real cutoff data import; company onboarding; load test; deploy to preview (Docker) then production.
