# Test Plan
Logic: quiz scoring ranks correct type; matching favours relevant mentor; points idempotent; FAQ finds answer.
HTTP: every new public page 200; POST without CSRF → 403; quiz works anonymous and logged-in; leaderboard hides opted-out; parent link flow; plan request → admin activate → report unlocked; admin pages 403 for non-admin.
Responsive: check 375 / 768 / 1440 px manually.
Run: `pytest -q`

## v12
`tests/test_v12.py` (33 tests): verification, reset, consent, throttle, assessments per class, enquiry for all classes and streams, ≤5 colleges, assessment gate for Class 8–10, mentor suggestion/allotment, Razorpay signature, slots/video link, AI/FAQ/crisis, reviews, internships, practice, certificate, import, language, PWA, sitemap, admin access control. Run `python -m pytest -q` (68 total).
