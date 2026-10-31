# Decisions
ADR-001 Keep FastAPI + Jinja. Reason: user asked not to change existing code; server-rendered is simple to host.
ADR-002 New package `extras/` with its own APIRouter. Reason: additive, easy to remove.
ADR-003 Rule-based matching/quiz/FAQ, no LLM. Reason: no API key/cost, transparent, honest labelling.
ADR-004 Manual plan activation. Reason: no payment gateway yet; avoids fake "paid" states.
ADR-005 Leaderboard shows "FirstName L." and is opt-in. Reason: users are minors.
ADR-006 Parent link via student-generated code. Reason: student consent without email infrastructure.
