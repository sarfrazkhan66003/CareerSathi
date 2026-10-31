# Test Plan
Logic: quiz scoring ranks correct type; matching favours relevant mentor; points idempotent; FAQ finds answer.
HTTP: every new public page 200; POST without CSRF → 403; quiz works anonymous and logged-in; leaderboard hides opted-out; parent link flow; plan request → admin activate → report unlocked; admin pages 403 for non-admin.
Responsive: check 375 / 768 / 1440 px manually.
Run: `pytest -q`
