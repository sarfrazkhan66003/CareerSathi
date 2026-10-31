# CareerSathi

**Guiding Futures, Building Careers.**

CareerSathi is a career guidance platform for students in classes 8–12 in India. It brings together verified mentors, school seminars, college research, free learning material and a set of career tools in one web application. It is built from the *CareerSathi Startup Business Plan* by Mohammad Sarfraz Khan.

> **Honest by design.** CareerSathi does not guarantee admissions, jobs or income. Nothing in the app is fabricated: there are no fake mentors, partners or testimonials. Mentors, seminars, tours and internships appear only after an admin adds or verifies them.

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Quick start (Windows PowerShell)](#quick-start-windows-powershell)
4. [Quick start (macOS / Linux)](#quick-start-macos--linux)
5. [Creating the admin account](#creating-the-admin-account)
6. [Seeding content](#seeding-content)
7. [URL map](#url-map)
8. [Roles and permissions](#roles-and-permissions)
9. [How the new tools work](#how-the-new-tools-work)
10. [Project structure](#project-structure)
11. [Testing](#testing)
12. [Deployment with Docker and PostgreSQL](#deployment-with-docker-and-postgresql)
13. [Configuration](#configuration)
14. [Security](#security)
15. [Known limits and roadmap](#known-limits-and-roadmap)
16. [Troubleshooting](#troubleshooting)
17. [Credits](#credits)

---

## Features

### Core platform (v1–v10)

- Landing page, About, Contact, Privacy and Terms.
- Accounts for **students, parents, mentors and schools**, with an **admin** for the founder.
- Student journey: profile, interest assessment, enquiry for guidance.
- Mentor listing (verified only), profiles and session requests with clash checks.
- Seminars, college tours, courses, internships and resources, managed from the admin panel.
- College directory with 44 reference institutions, search, compare and moderated reviews.
- Free reading courses (about 50 guides) loaded by the seed scripts.
- Admin dashboard: traffic, users, bookings, enquiries, reviews, content publishing and CSV export.

### Growth Pack (v11), added from the Business Plan

| Feature | URL | Business Plan source |
|---|---|---|
| Career Compass: 24-question interest quiz with ranked career matches | `/career-quiz` | Career Assessment Tool |
| Career report: printable, full version for paid plans | `/report/{token}` | Premium career reports |
| 14 career roadmaps with steps, exams and skills | `/roadmaps` | Skill Development Hub |
| Mentor Match with transparent scoring | `/match` | Mentor Matching |
| Points, badges, referral link and parent code | `/rewards` | Gamification, Referral Program |
| Opt-in leaderboard | `/leaderboard` | Leaderboards and Rewards |
| FAQ assistant (chat bubble on every page) | `/assistant`, `/faq` | AI Chatbot for FAQs |
| Parent dashboard | `/parent` | Parent Dashboard |
| Plans: ₹99 and ₹299 per year | `/pricing` | Subscription model |
| Resume builder | `/resume-builder` | Resume builders |
| Study abroad and scholarship planner | `/study-abroad` | Global expansion |
| Partnerships form for schools, NGOs, colleges and companies | `/partners` | Partnerships |
| Feedback | `/feedback` | Feedback mechanism |
| Admin growth console | `/admin/growth` | Operations |

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Templates | Jinja2 (server-rendered) |
| Database | SQLAlchemy 2, SQLite by default, PostgreSQL via `DATABASE_URL` |
| Frontend | Plain HTML, CSS and a little vanilla JavaScript |
| Sessions | Signed, HTTP-only cookies |
| Tests | pytest and FastAPI TestClient |
| Deployment | Docker and Docker Compose |

---

## Quick start (Windows PowerShell)

Run these commands **one at a time** from the project folder. Older PowerShell versions do not support `&&`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python create_admin.py
python seed_content.py
python -m uvicorn app:app --reload
```

Open **http://127.0.0.1:8000**.

If PowerShell blocks the activation script, run this first and then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

If `uvicorn` is not recognised, always use `python -m uvicorn` as shown above.

## Quick start (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python create_admin.py
python seed_content.py
uvicorn app:app --reload
```

---

## Creating the admin account

Run:

```powershell
python create_admin.py
```

The script asks for three things. **Type your real values at each prompt**, and do not paste other commands there.

```
Admin email: you@example.com
Admin name: Your Name
Admin password (12+ characters): ********
```

Then log in at `/login`. Admins are sent to `/admin/dashboard`, and the growth console is at `/admin/growth`.

There are no built-in admin credentials, and anonymous admin registration is not possible. Restrict who can run `create_admin.py` on a server. Running it again with the same email resets that account.

---

## Seeding content

All seed scripts are safe to run more than once.

```powershell
python seed_content.py        # 8 courses and 10 career guides
python seed_lessons.py        # 32 additional reading modules
python seed_foundations.py    # richer Python, HTML/CSS and SQL guides
python seed_v9_course_library.py
```

Seminars, tours and internships stay empty until the admin publishes real, confirmed opportunities.

---

## URL map

**Public:** `/`, `/about`, `/contact`, `/privacy`, `/terms`, `/faq`, `/pricing`, `/partners`, `/career-quiz`, `/roadmaps`, `/roadmaps/{slug}`, `/match`, `/leaderboard`, `/resume-builder`, `/study-abroad`, `/assistant`, `/colleges`, `/college/{id}`, `/college-compare`, `/mentors`, `/mentor/{id}`, `/explore/{seminar|tour|course|internship|resource}`, `/item/{id}`, `/assessment`, `/health`

**Signed-in users:** `/dashboard`, `/profile`, `/journey`, `/rewards`, `/feedback`, `/parent` (parents)

**Admin:** `/admin/dashboard`, `/admin/growth`, `/admin/export/{users|bookings|visits}`

---

## Roles and permissions

| Role | What they can do |
|---|---|
| Student | Quiz, roadmaps, journey and assessment, bookings, mentor requests, reviews, rewards, referrals |
| Parent | Browse, book services, link a student with the student's code, view progress |
| Mentor | Edit profile and credentials, confirm own requests; listed publicly only after admin verification |
| School | Browse and request seminars and events |
| Admin | Dashboard, verify mentors, publish content, moderate reviews, handle enquiries, activate plans, export CSV |

Admin actions disable accounts softly (reversible), so booking records are preserved.

---

## How the new tools work

**Career Compass.** Each of the 24 statements belongs to one of six interest types (Doer, Thinker, Creator, Helper, Leader, Organiser), based on the RIASEC idea. Scores are converted to percentages. Each career has up to three types, weighted 3, 2 and 1, and the match percentage shows how well the work style fits your answers. It is an interest explorer, not a clinical test and not a prediction of success.

**Mentor Match.** Scoring is rule-based and shown on the page: shared interests up to 60 points, same entrance exam 25 points, same city or state 15 points. Only verified, active mentors are considered.

**Points and badges.** Points are awarded for the quiz, roadmaps, mentor matching, resume, feedback, referrals and linking a parent. Each activity scores once per user, so points cannot be farmed. Badges: Explorer, Curious, Planner, Pathfinder, Trailblazer.

**Leaderboard.** Opt-in only, and it shows first name plus last initial (for example "Riya S."), because many users are minors.

**Parent dashboard.** The student shares an 8-character code from the Rewards page. A parent who enters it sees points, badge, interest profile and recent bookings. The student can regenerate the code at any time, and the parent can unlink.

**Plans.** Free, Sathi Plus (₹99 per year) and Sathi Pro (₹299 per year). There is **no payment gateway yet**. A user requests a plan, the admin confirms payment manually and activates it for 365 days at `/admin/growth`, and the full career report unlocks.

**FAQ assistant.** A rule-based keyword matcher over about 19 curated answers. It is clearly labelled as automated and is not a generative AI. It is rate-limited and CSRF-protected.

**Resume builder.** Renders a one-page resume from a form. Nothing is stored. Use the browser's Print, then Save as PDF.

---

## Project structure

```
CareerSathi-main/
├── app.py                  # Core FastAPI app, models and routes (v1–v10) + 5-line hook for extras
├── extras/                 # v11 Growth Pack
│   ├── data.py             # Quiz questions, careers, plans, FAQ, badges (pure data)
│   ├── logic.py            # Scoring, matching, FAQ search (pure, unit-tested)
│   ├── models.py           # New x_* tables
│   └── routes.py           # HTTP layer
├── templates/              # Jinja templates (x_*.html are new)
├── static/                 # style.css, extras.css, main.js, extras.js, brand/
├── tests/                  # pytest suite (35 tests)
├── docs/                   # PRD, ARCHITECTURE, DESIGN, DECISIONS, SECURITY, TEST_PLAN, MEMORY
├── seed_*.py               # Idempotent content seeders
├── create_admin.py         # Interactive admin creation / reset
├── Dockerfile, docker-compose.yml
├── requirements.txt, .env.example
├── RULES.md, TASKS.md
└── README.md
```

The project follows a documentation-first workflow: PRD, architecture, design rules, tasks and decisions are in `docs/` and the root, so any contributor or AI tool can read the context before changing code.

---

## Testing

```powershell
python -m pip install pytest httpx
python -m pytest -q
```

The suite uses a temporary database, so it never touches `careersathi.db`. It covers quiz scoring, matching, FAQ search, idempotent points, CSRF, role checks, referral, parent linking, plan activation, HTML escaping and regression checks on existing pages.

---

## Deployment with Docker and PostgreSQL

1. Get a server with Docker Compose and a domain name. Put an HTTPS reverse proxy (Caddy, or Nginx with Let's Encrypt) in front. The compose file binds the app to `127.0.0.1:8000` only.
2. Copy `.env.example` to `.env` and set a long random `SECRET_KEY` and a strong `DB_PASSWORD`. Never commit `.env`.
3. Start it:
   ```bash
   docker compose up -d --build
   docker compose exec web python create_admin.py
   docker compose exec web python seed_content.py
   ```
4. Point the reverse proxy at `127.0.0.1:8000`, enable HTTPS and keep port 8000 closed to the public.
5. Monitor `/health`, schedule PostgreSQL backups and test restoring them.

Use a preview environment first and check it before going to production.

---

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs session cookies. Required in production. |
| `DATABASE_URL` | Defaults to SQLite (`careersathi.db`). Example: `postgresql+psycopg://user:pass@host:5432/careersathi` |
| `APP_ENV` | Set to `production` to enable secure cookies and hide API docs. |
| `DB_PASSWORD` | Used by Docker Compose for PostgreSQL. |
| `GOOGLE_PLACES_API_KEY` | Optional. Enables live institute search on the College tours page. Keep it server-side only. |

Back up `careersathi.db` regularly and never overwrite it when updating code.

---

## Security

- HTTP-only signed session cookies, salted PBKDF2 password hashes.
- CSRF token on every write, including the assistant JSON endpoint.
- Role checks on every protected route; admin routes are admin-only.
- All output is HTML-escaped by Jinja; user input is length-limited.
- Parent access works only through a code the student chooses to share.
- Leaderboard is opt-in and shows abbreviated names.
- The assistant is rate-limited per session.

---

## Known limits and roadmap

**Not built yet:** online payments (Razorpay or similar), email and SMS notifications, email verification, password reset, multi-factor login, guardian-consent flow for minors, video lessons and certificates, live webinars, and a generative AI counsellor.

**Before accepting real users, especially children:** get legal review for India's DPDP rules, add guardian consent and age checks, add email verification and password reset, set up backups, monitoring and rate limiting, and complete an accessibility and load test. The 1,000-concurrent-user and 99.9% uptime goals in the Business Plan have not been tested.

**Suggested next steps:** payment gateway and invoices, email notifications, mentor availability calendar, real verified mentor and school onboarding through the admin panel, and a Hindi interface.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `&&` is not a valid statement separator | Run commands one per line in PowerShell. |
| `uvicorn` is not recognised | Use `python -m uvicorn app:app --reload`. |
| `Activate.ps1` is blocked | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `create_admin.py` says "Email/name invalid" | Type real values at the prompts; do not paste commands. Password must be 12+ characters. |
| Mentor Match shows no mentors | Mentors must register and be verified by admin first. |
| Port 8000 is busy | `python -m uvicorn app:app --reload --port 8001` |
| Need a fresh start | Stop the server, back up `careersathi.db`, delete it, and run the setup steps again. |

---

## Credits

Founder and developer: **Mohammad Sarfraz Khan**, Sitamarhi, Bihar, India. Contact: +91 83407 83239.

> "Your future is not found in one decision; it is built with every step you take."
