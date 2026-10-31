# CareerSathi — full-stack startup website

**CareerSathi** — *Guiding Futures, Building Careers*. A responsive, database-backed web application based on the uploaded 38-page CareerSathi business plan, its SRS (pages 23–28), and webpage specifications (pages 32–38).

## Included and working

- Responsive, editorial-style landing page, About, Contact, Privacy/Terms drafts.
- Account creation and password-protected login for students, parents, mentors and schools.
- Role-aware dashboard; editable profiles; mentor verification controlled by admins.
- Live database listings for seminars, college tours, courses, internships and learning resources.
- Bookings and enrolment requests, capacity checks, status tracking, cancellation and mentor confirmation.
- Mentor search and mentoring requests; no fake published mentors.
- Basic **interest explorer** with transparent rules (not an AI psychometric model).
- College reviews held for administrator approval.
- Founder/admin dashboard: real page views, approximate distinct-browser counts, 14-day traffic bars, registered users, account suspension/reinstatement, verified mentors, bookings, enquiries and reviews, content publishing, CSV exports.
- HTTP-only signed session cookies, PBKDF2 salted password hashes, CSRF checks on every write, authorization checks, protected admin routes.
- SQLite out of the box, PostgreSQL via DATABASE_URL, Docker Compose and basic health endpoint.

## Run locally (Windows/macOS/Linux)

Requires Python 3.11+ and internet access to install packages.

```bash
cd CareerSathi
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python create_admin.py
python seed_content.py
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000**. Admin account logs in normally at `/login` and is redirected to `/admin/dashboard`. There are **no built-in admin credentials**. Run `python seed_content.py` once to install 18 informational courses/resource guides (safe to rerun). Seminar, tour and internship listings stay empty until admin adds confirmed real opportunities. The college research directory contains 44 reference institutions; **these are not partnerships or bookable tours**. India-wide location enquiries are supported through the Contact form and stored in admin enquiries. A `careersathi.db` SQLite file is created automatically on first run. **Back it up.**

## Cloud hosting with Docker + PostgreSQL

1. Get a VPS with Docker Compose and a domain name. Configure DNS and an HTTPS reverse proxy (Caddy or Nginx + Let's Encrypt); the Compose web port binds only to loopback.
2. Copy `.env.example` to `.env`. Generate a strong new session key and database password (never commit them).
3. `docker compose up -d --build`.
4. `docker compose exec web python create_admin.py`.
5. Configure the reverse proxy to `127.0.0.1:8000`, enable HTTPS, set secure headers and monitor `/health`. Configure a firewall so port 8000 is not exposed publicly.
6. Set up scheduled PostgreSQL backups and verified restore drills, log monitoring, a privacy/consent policy, incident response and a real support channel.

⚠️ **This is a substantial deployable starter application, not a certified production launch.** The following must be completed *before accepting real users, especially children or collecting payments*: guardian consent and age-assurance flows, legal review (Indian DPDP compliance and other applicable rules), password reset/email verification, MFA, account recovery, anti-abuse/rate limiting, production email/SMS notifications, scheduling/availability and payments/refunds integrations, audits and tests, accessibility review, privacy retention/deletion workflows, secure backup/restore, observability, performance/load tests, and static asset hosting / CSP review. The 1,000 concurrent users / 99.9% SLA goals specified in the PDF are **not tested or guaranteed**. The interest explorer is **not** the PDF's proposed AI psychometric system. Course content playback and internship hiring integrations are not implemented. No payment gateway is connected; paid requests are labelled *unpaid* and require manual confirmation. The original PDF's React/Node/Mongo suggestions are not mandatory functional requirements; this build intentionally uses Python FastAPI + Jinja templates + SQLAlchemy / PostgreSQL for a simpler maintainable server-rendered architecture.

## Roles & permission overview

| Role | Features |
| --- | --- |
| Student | Browse, interest explorer, seminar/tour/course/internship booking requests, mentorship, reviews |
| Parent | Browse, mentorship and services booking, reviews |
| Mentor | Edit portfolio, see and confirm own mentorship requests (public listing after verification) |
| School | Browse, book seminar/event services and see own requests |
| Admin | Dashboard metrics, manage account access and mentor verification, publish/unpublish content, bookings, review moderation, support enquiries, export CSV |

User accounts are **soft-disabled** (reversible), not permanently deleted by the admin action. This preserves booking records. No one can disable the current admin account via the web dashboard. Restrict who can run `create_admin.py` on the server.

## Key URL map

`/`, `/about`, `/register`, `/login`, `/dashboard`, `/profile`, `/mentors`, `/mentor/{id}`, `/explore/seminar`, `/explore/tour`, `/explore/course`, `/explore/internship`, `/explore/resource`, `/item/{id}`, `/assessment`, `/colleges`, `/contact`, `/admin/dashboard`, `/health`.

## Important privacy note

Visitor metrics count visits (page loads) and distinct pseudonymous browser cookies, **not exact people**. The original business plan is conceptual and does not contain verified mentor names, partner schools, testimonials or operational contact details. Nothing has been fabricated to imply existing partnerships or client results. Add verified data yourself via the admin interface.

## v2 content expansion (24 October 2026)
- `/colleges`: curated, searchable college research directory with official university links, stream and 36-state/UT filters, plus moderated user reviews. Curated directory **is not every Indian college**. Public data example source: https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html.
- `/contact`: state / union territory, city / district, institution and seminar/college enquiry inputs; submissions reach the existing admin enquiries list.
- `/about`: founder Mohammad Sarfraz Khan, project's mission, platform roles, coverage and current operational status, without invented office address or founder biography.
- `/explore/...`: nationwide state/city filtering of admin-published opportunities and clear links to request locally relevant seminars and tours.
- `seed_content.py`: 8 free self-learning course outlines and 10 career articles/guide summaries. These are **not** teacher-led courses, complete lesson libraries, certificates or guarantees of placement.
- Real operational data still needed from the founder: verified schools, partner institutes, seminars with dates, approved speaker bios, actual internships, location and contact address, payment provider, legal policies, real complete course lessons, media rights.
- On existing installations: **do not delete or overwrite `careersathi.db`**. Replace source/templates/static files and run `python seed_content.py` in the existing virtualenv.

## Version 3 — all-India institution finder and expanded learning (24 October 2026)

**New URL:** `/institutes`. Visitors filter by institution name, state/UT, district/city and school/college/university category. Curated college references work **offline**; Bhopal + Madhya Pradesh + `LNCT` is supported as a local match. A live search button optionally calls **Google Places API (New) Text Search** from the server, rather than scraping Google. It may return up to 20 results per request; **it is not all schools and colleges in India**. Google charges according to its pricing, terms, usage and requested fields; confirm billing and configure API quotas. Search API responses are not stored in the local directory. No partnership is implied.

To enable live results: create a Google Cloud project, enable Places API (New) and billing, configure a restricted server-side API key with appropriate limits, and set `GOOGLE_PLACES_API_KEY` in the server environment (or `.env` for Docker). **Do not put the key in frontend JavaScript or commit it to Git.** On PowerShell, for a temporary local development session: `$env:GOOGLE_PLACES_API_KEY='YOUR_SERVER_KEY'` and restart the app. Without the key, reference college listings still work but Google-powered school discovery won't. Production should use rate limits, caching where legally allowed, budget alerts and abuse prevention.

**Free theoretical courses:** run `python seed_lessons.py` to add 32 additional reading modules, each with introduction, foundations, practice, examples, exercises and safety/next steps. This is original introductory educational material, not a professional certificate or full accredited syllabus. Rerunning does not duplicate titles. To keep old users/bookings, keep your original `careersathi.db`; never copy the ZIP's database over it. The ZIP intentionally excludes all account databases. Run `python seed_content.py` then `python seed_lessons.py` after extracting.

Footer now names **Mohammad Sarfraz Khan** as founder/developer and features an original motivational quote. A street address has not been invented; update the location text after the founder supplies a verified public office/city address.

**Official API reference:** https://developers.google.com/maps/documentation/places/web-service/text-search


## V4 changes (2026-10-24)
- The **Institutes** top-navigation item has been removed; `/institutes` now redirects to `/explore/tour`, preserving old links.
- `/explore/tour` searches the embedded public **44-institution starter directory** by name, Indian state and city/district, and can optionally query Google Places (New) when a server-side `GOOGLE_PLACES_API_KEY` is configured. Results appear directly on the College tours page. **Not every Google-listed institute is included offline.** No unconfirmed tour is presented as bookable.
- `/explore/course` features a free knowledge hub with existing beginner reading materials. `seed_lessons.py` loads 32 topic guides, and `seed_foundations.py` enriches Python, HTML/CSS, and SQL guides with concrete examples. Run seeders only once if preferred: they are idempotent.
- Admin sign-in uses `/login`; run `python create_admin.py` locally to create/reset a founder admin account. **Never allow anonymous admin-role registration.** Dashboard lives at `/admin/dashboard`.

### Windows update (preserve your existing database)
Backup the existing folder and `careersathi.db`. Copy updated source files into your working folder **without deleting or overwriting your local database**. From PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python seed_content.py
python seed_lessons.py
python seed_foundations.py
python create_admin.py
python -m uvicorn app:app --reload
```
On a fresh install no database is shipped inside the ZIP. Locally generated data is preserved as long as the existing database file is kept. For a cloud production launch, use persistent PostgreSQL, secure HTTPS, a stable SECRET_KEY, backups, parental consent handling and security/load testing.

## V11 — Growth Pack (31 October 2026): features from the Startup Business Plan
Everything below is ADDED; no existing route, table or behaviour was changed. Code lives in `extras/`, templates `templates/x_*.html`, assets `static/extras.css|js`, docs in `docs/`, tests in `tests/`.

| Feature | URL |
|---|---|
| Career Compass (24-question RIASEC-style quiz, ranked matches) | `/career-quiz` |
| Career report (printable; Plus/Pro unlock full 8 matches + 30-60-90 plan) | `/report/{token}` |
| 14 career roadmaps | `/roadmaps`, `/roadmaps/{slug}` |
| Mentor match (transparent scoring over verified mentors only) | `/match` |
| Points, badges, referral link, parent code | `/rewards` |
| Opt-in leaderboard (first name + initial) | `/leaderboard` |
| FAQ assistant (rule-based chat bubble, labelled as automated) | widget, `/assistant`, `/faq` |
| Parent dashboard (student-shared code) | `/parent` |
| Plans ₹99 / ₹299 per year (manual activation, no gateway) | `/pricing`, admin: `/admin/growth` |
| Resume builder (not stored; print to PDF) | `/resume-builder` |
| Study abroad & scholarship planner | `/study-abroad` |
| Partners (schools, NGOs, colleges, companies) → admin enquiries | `/partners` |
| Feedback | `/feedback` |

Run: `pip install -r requirements.txt && python create_admin.py && python seed_content.py && uvicorn app:app --reload`
Tests: `pip install pytest httpx && pytest -q` (35 tests). New tables (`x_*`) are created automatically.
Honest limits: no payment gateway, no generative AI, no email/SMS. Plans are activated by admin after manual payment confirmation.
