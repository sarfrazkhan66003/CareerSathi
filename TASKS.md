# Tasks
## v11 Growth Pack — done
Quiz, report, roadmaps, match, rewards, leaderboard, referral, FAQ bot, parent, plans, resume, study abroad, partners, feedback, admin growth.
## v12 Launch Pack — done
- [x] Email verification + password reset  - [x] Age check + guardian consent  - [x] Login throttle + optional CAPTCHA
- [x] Post-registration hub `/start`  - [x] Assessments (84 MCQ): Class 8–9 stream finder, Class 10 readiness (mandatory), Class 11/12 optional
- [x] Enquiry form (all classes, streams, entrance, ≤5 colleges, purposes, comment) + mentor suggestion/allotment
- [x] Enquiry gated behind assessment for Class 8–10 (route + middleware)
- [x] SMTP/outbox notifications, reminders, parent digest  - [x] Razorpay  - [x] Mentor slots + video links
- [x] AI counsellor (Claude API, FAQ fallback)  - [x] Reviews 2.0  - [x] Internship board  - [x] Practice  - [x] Progress + certificate
- [x] Streaks  - [x] College predictor (data-driven)  - [x] Scholarship finder  - [x] School dashboard  - [x] Stories
- [x] Hindi  - [x] PWA  - [x] Dark mode  - [x] Blog + sitemap  - [x] Admin hub/analytics/audit/outbox/import  - [x] Sentry optional
- [x] Fix legacy booking-confirm 500  - [x] 84 tests pass
## v12.2 — done
- [x] Assessment compulsory for Class 8–10 (no skip, no classic bypass, legacy forms guarded)
- [x] Score-based streams (<50% hides Science) + preparation alert + acknowledgement + stream roadmaps
- [x] `/admin` hidden entry, admin links removed from public site  - [x] Professional click-to-open navbar (desktop + mobile)
- [x] Contact email + Instagram (page + footer)  - [x] Checkbox and mobile-header CSS fixes  - [x] 84 tests pass
## v12.3 — done (bug fixes)
- [x] Navbar immune to stale cache (inline CSS/JS, versioned assets), duplicate "हिंदी/Log in" fixed
- [x] Assessment: one question at a time, no skipping, no raw JSON (friendly page, answers kept)
- [x] Friendly HTML error pages for browsers  - [x] Full stream name on result  - [x] 84 tests pass, browser-verified
## Next (needs owner)
- [ ] Add real credentials (SMTP, Razorpay, Anthropic, Turnstile)  - [ ] Legal review  - [ ] Import real cutoffs  - [ ] Preview deploy (Docker) then production
