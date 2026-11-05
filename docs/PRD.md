# PRD — CareerSathi (current: v12.3)
> Read this file + docs/MEMORY.md first in any new session. They hold the full project state.

## Product
CareerSathi — *Guiding Futures, Building Careers*. FastAPI + Jinja + SQLAlchemy site. Legacy code (app.py, v1–v10) is untouched except 5 hook lines at its end; all new work is in `extras/`.

## Users
Students (Class 8–12, college), Parents, Mentors, Schools, Admin/Founder.

## Version history
| Ver | Scope |
|---|---|
| v1–v10 | Core platform: auth, mentors, seminars/tours/courses, colleges + reviews, journey, admin |
| v11 Growth Pack | Career Compass quiz, report, roadmaps, mentor match, points/badges/leaderboard, referral, FAQ bot, parent dashboard, plans, resume, study abroad, partners, feedback |
| v12 Launch Pack | Everything in sections A–C below |
| v12.2 | Hard assessment gate, score-based streams + preparation alert + stream roadmaps, `/admin` hidden entry, professional navbar, contact email + Instagram |

## v12 requirements and status (all implemented and tested)
### A. Student onboarding (user's explicit spec)
1. After registration a student goes to `/start` (hub): email verification → age/guardian consent → assessment → enquiry.
2. **Class 8–9:** mandatory *Stream Finder* assessment (MCQ: reasoning, maths, science, social, English, GK + interest questions) → stream suggestion.
3. **Class 10:** mandatory *Class 10 Stream Readiness Test* (high-level MCQ: reasoning 6, maths 6, science 6, social 4, English 3, GK 5 + interests) → PCM / PCB / PCMB / Commerce / Arts suggestion.
4. **Class 11, 12, college:** assessments are optional (Subject Readiness, Aptitude & Reasoning, GK Booster, plus Career Compass quiz).
5. Question bank: 84 MCQs, demanding level, with explanations. Random per attempt.
6. **Enforcement:** Class 8–10 students cannot open or submit `/enquiry` until an assessment is done and consent is complete (middleware gates `/dashboard`, `/journey`; route gate on `/enquiry`).
### B. Enquiry form (`/enquiry`, every class)
Fields: name, email, phone, class (8,9,10,11,12,college,other), marks %, entrance exam (+ score), stream (PCM, PCB, PCMB, Commerce, Arts, or "not sure"; for Class 12 the label becomes "stream you studied"), purposes (choose stream / understand roadmap / career doubt → which skills / colleges / exam prep / scholarship / other), career goal, **up to 5 colleges**, comment/doubt.
After submit: `/enquiry/{id}/mentor` suggests verified mentors by the chosen colleges + stream + exam; student picks one; admin can allot at `/admin/enquiries`. Emails sent at each step.
### C. Launch-readiness features
| Feature | Where |
|---|---|
| Email verification, password reset | `/verify/{t}`, `/forgot-password`, `/reset-password/{t}` |
| Age check + guardian consent by email | `/start/consent`, `/guardian/consent/{t}` |
| Login throttle (5 fails/pair, 30/IP per 15 min) + optional Cloudflare Turnstile CAPTCHA | login override |
| Email notifications (SMTP, outbox fallback) for bookings, mentor requests, plan, enquiry, consent | `services.py`, SQLAlchemy events |
| Razorpay payments (plans, paid items/sessions), signature + webhook verification | `/pay/...` |
| Mentor slot calendar, booking, auto video link (Jitsi or mentor's own link) | `/my/slots`, `/mentors/{id}/slots`, `/my-sessions` |
| Reminders + parent weekly digest (background thread or `/admin/run-reminders`) | routes3 |
| AI counsellor via Claude API (Hinglish, FAQ first, crisis-safe, daily cap) | `/assistant/ask`, widget |
| College reviews 2.0 (helpful votes, alumni badge, averages) | `/reviews` |
| Internship board (post → admin approve → apply) | `/internships` |
| Mock-interview + coding practice with self-score, weekly challenge | `/practice` |
| Course progress tracker + non-accredited certificate | `/progress/{id}`, `/certificate/{id}` |
| Daily streak check-in | `/rewards/checkin` |
| College predictor (admin-uploaded cutoff CSV; empty = honest message) | `/college-predictor` |
| Scholarship finder (official portal links, filters) | `/scholarships` |
| School dashboard (students' progress, attendance) | `/school` |
| Testimonials/stories (admin-approved only) | `/stories` |
| Hindi interface (nav, footer, v12 pages) via `lang` cookie | `/lang/hi` |
| PWA (manifest, service worker, offline page), dark mode, SEO blog, sitemap, robots | `/sw.js`, `/blog`, `/sitemap.xml` |
| Admin: hub, analytics funnel, audit log, outbox, CSV bulk import, blog editor, moderation | `/admin/hub` etc. |
| Sentry (optional), `/health/deep`, backups guidance | env `SENTRY_DSN` |
| Fix: legacy booking confirm/cancel 500 (expired session) | `SessionLocal.configure(expire_on_commit=False)` |

## v12.3 changes (latest release: bug fixes after user testing)
Problems reported with screenshots, and fixes:
1. **Navbar looked broken** (huge chevrons, unstyled buttons, "हिंदी" and "Log in" shown twice). Causes: (a) browser kept the OLD `extras.css`; (b) CSS specificity bug: `.links>a` overrode `.only-mobile{display:none}`. Fixes: all asset URLs carry `?v=<mtime hash>` (`asset_v` Jinja global); the navbar CSS and JS are now **inline** in the page (`templates/_nav_css.html`, `_nav_js.html`), so the navbar is correct even if a stale CSS file is cached; rule is `.links>a.only-mobile`; `.skip-link` also inline; chevron SVGs are sized.
2. **Raw JSON `{"detail": "Please answer every question (29 left)…"}`** shown on incomplete assessment. Fixes: (a) the test is now **one question at a time**: Next is disabled until the current question is answered, the question palette cannot jump ahead, Submit appears only on the last question and stays disabled until all are answered; (b) if a request still arrives incomplete, the server re-shows the test with the answers kept and a clear message (HTTP 400, HTML); (c) **all** browser errors now show a friendly page (`x_error.html`), while API clients/tests (no `text/html` in Accept) still receive JSON.
3. Result page shows the full stream name ("Commerce") instead of the code; hidden Submit/Next buttons really hide; question title no longer overlaps the card border.
Verified in a real browser with `extras.css`/`extras.js` blocked (stale-cache simulation) and with a full 38-question run. 84 tests pass.

## v12.2 changes
### D. Assessment is compulsory for Class 8–10 (no skipping)
- A finished assessment (every question answered) is required before the dashboard, journey, `/enquiry`, and the legacy `/journey/enquiry` + `/journey/assessment` forms. The `?classic=1` bypass was removed. Submitting with unanswered questions returns an error; no score or stream is shown until complete.
- Class 11, 12 and college: assessment stays optional.
### E. Streams depend on the score (Class 8–10)
- Rule lives in `extras/data3.py` (`THRESHOLD = 50`). Overall assessment score **below 50%** → Science streams (PCM, PCB, PCMB) are NOT shown or recommended; only **Commerce** and **Arts** appear (enquiry form, assessment result, legacy quiz recommendation).
- If a low-score student still wants Science: ticking "I still want a Science stream" reveals the options and shows a **Preparation needed** alert with a link to that stream's roadmap. The server requires the confirmation (`prep_ack=yes`); an auto-note is added to the enquiry comment for the mentor.
- For Class 11/12/college the stream is a fact ("stream you studied"), so it is never blocked; if a latest assessment score is low a note is added for the mentor.
- Stream roadmaps for every stream (PCM, PCB, PCMB, Commerce, Arts): `/stream-roadmap/{code}` (steps by class, subjects, careers, weak-section tips, 12-week catch-up plan).
### F. Admin entry
- No admin link anywhere in the public site or navbar (removed "Admin login" and the "Growth" link). Admin types **`/admin`** → logs in / goes to `/admin/dashboard`. Non-admins are sent to their own dashboard. Admin tools stay reachable from inside the admin dashboard and `/admin/hub`.
### G. Navbar (same options, better presentation)
- Click-to-open menus: Home · **Explore** (Seminars, Mentors, College tours, Courses, Internship board, College reviews) · **Career tools** (Career Compass, Roadmaps, Mentor match, Practice, Resume builder, Scholarship finder, College predictor, Study abroad) · Plans · About. Right side: language, dark mode, **account menu** (Dashboard, Start here, Rewards, My enquiries, My sessions, Log out; role-specific items for parent/mentor/school) or Log in + Get started. Keyboard + Escape + outside-click support. Mobile: single row, Log in and language move into the hamburger menu.
### H. Contact
- Contact page and footer show **officialcareersathi@gmail.com** and Instagram **@officialcareersathi** (https://www.instagram.com/officialcareersathi/), plus phone.
### Tests
84 tests pass (`python -m pytest -q`). New tests cover: incomplete assessment rejected, low score hides Science, acknowledgement required, high score shows all streams, Class 12 advisory only, roadmaps, bypass closed, legacy forms, `/admin` behaviour, contact details, navbar options.

## Out of scope / honest limits
- Razorpay, SMTP, Claude API, Turnstile, Sentry need the owner's credentials (env vars); without them the feature degrades gracefully (manual payment, outbox log, FAQ-only bot, no CAPTCHA).
- No fabricated mentors, partners, cutoffs or testimonials. College predictor has no data until admin imports real cutoffs.
- Hindi covers navigation, footer and v12 pages, not every legacy page.
- Certificates are completion certificates, not accredited.
- Not load-tested; legal review (DPDP, children's data) still required before public launch.

## Success criteria
1. New Class 10 student cannot send an enquiry without finishing the assessment; Class 12 can.
2. Enquiry saves all fields, ≤5 colleges, suggests mentors after colleges are chosen.
3. Admin can allot a mentor; student and mentor receive emails.
4. Payments only complete after verified Razorpay signature.
5. `pytest -q` passes (84 tests).
6. A student with <50% never sees Science unless they explicitly confirm they will prepare; `/admin` works with no public admin link.

## Next ideas (not built)
Real company onboarding, mentor payouts, WhatsApp API notifications, full Hindi translation, native mobile app, live video classes, analytics export to BI.
