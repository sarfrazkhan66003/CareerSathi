# Decisions
ADR-001 Keep FastAPI + Jinja. Reason: user asked not to change existing code; server-rendered is simple to host.
ADR-002 New package `extras/` with its own APIRouter. Reason: additive, easy to remove.
ADR-003 Rule-based matching/quiz/FAQ, no LLM. Reason: no API key/cost, transparent, honest labelling.
ADR-004 Manual plan activation. Reason: no payment gateway yet; avoids fake "paid" states.
ADR-005 Leaderboard shows "FirstName L." and is opt-in. Reason: users are minors.
ADR-006 Parent link via student-generated code. Reason: student consent without email infrastructure.
ADR-007 (v12) Override `/login` and `/journey` by prepending routes in `promote_overrides`, wrapping the original handlers. Reason: add throttle/CAPTCHA/onboarding gate without editing legacy code.
ADR-008 (v12) Booking emails via SQLAlchemy `after_commit` events. Reason: legacy booking routes stay untouched.
ADR-009 (v12) `expire_on_commit=False` on SessionLocal. Reason: legacy `booking_action` read `user.role` after the session closed (500).
ADR-010 (v12) Email, payments, AI, CAPTCHA are env-driven with graceful fallbacks (outbox log, manual payment, FAQ-only, no CAPTCHA). Reason: works without paid accounts; no fake success states.
ADR-011 (v12) Class 8–10 must finish assessment before enquiry; 11/12 optional. Reason: user requirement; assessment drives stream suggestion.
ADR-012 (v12) College predictor reads admin-imported cutoffs only. Reason: never invent cutoff numbers.
ADR-013 (v12.2) Science hidden below 50% overall score for Class 8–10; override only with explicit preparation acknowledgement (server-enforced). Reason: user requirement; protects students from unrealistic choices while respecting choice.
ADR-014 (v12.2) Remove `?classic=1` bypass and guard legacy `/journey/*` POSTs. Reason: assessment must not be skippable.
ADR-015 (v12.2) Admin reachable only via typed `/admin`. Reason: no public admin link; access control unchanged (role checks).
ADR-016 (v12.3) Critical navbar CSS/JS inline + versioned asset URLs. Reason: stale browser cache broke the header; the header must never depend on a cached file.
ADR-017 (v12.3) Assessment is shown one question at a time with server-side re-render on incomplete submit. Reason: no skipping, no raw JSON.
