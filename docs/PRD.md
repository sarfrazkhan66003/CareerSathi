# PRD — CareerSathi "Growth Pack" (v11)

## Product
CareerSathi — *Guiding Futures, Building Careers*. Existing FastAPI + Jinja + SQLAlchemy site (v1–v10) stays untouched. This release ADDS the features promised in the Startup Business Plan (sections 1.2, 2.1, 2.2, 2.3, 5.3, 7.1) that were still missing.

## Problem
Students in classes 8–12 get misleading, expensive or no career guidance (Plan: Core Problem Statement).

## Users
Students (8–12), Parents, Mentors, Schools/NGOs/Colleges (partners), Founder/Admin.

## MVP additions (all additive)
| # | Feature | Business-plan source | Route |
|---|---------|----------------------|-------|
| 1 | Career Compass: 24-question interest (RIASEC-style) test, ranked career matches, saved results | 2.1 Career Assessment Tool, 2.2 "Which career fits you?" | /career-quiz |
| 2 | Premium career report (printable, plan-gated) | 2.3 premium reports ₹299–₹999 | /report/{id} |
| 3 | Mentor matching (transparent rule-based scoring) | 2.1 Mentor Matching | /match |
| 4 | Career roadmaps (12 careers, step-by-step) | Skill Development Hub | /roadmaps |
| 5 | Points, badges, leaderboard (opt-in, privacy-safe names) | 2.2 Gamification | /rewards, /leaderboard |
| 6 | Referral programme | 6.1 Referral Program | /join/{code} |
| 7 | FAQ assistant (rule-based, labelled as such) | 2.2 AI chatbot for FAQs | widget + /assistant |
| 8 | Parent dashboard (student-shared link code) | 2.1 Parent Dashboard | /parent |
| 9 | Plans & pricing (₹99 / ₹299 per year, manual confirmation) | 1.2 subscription | /pricing |
| 10 | Resume builder (printable) | 2.3 resume builder | /resume-builder |
| 11 | Study abroad & scholarship guide + checklist | 5.3 / Long-term vision | /study-abroad |
| 12 | Partners page (schools, NGOs, colleges, companies) | 5.1, 5.2 | /partners |
| 13 | Feedback mechanism | Suggestions: Feedback Mechanism | /feedback |
| 14 | FAQ page + Growth console for admin | — | /faq, /admin/growth |

## Out of scope (honest limits)
Real payment gateway, real AI/LLM counselling, video playback, email/SMS, mobile app. Paid plans are *requested* and activated manually by admin until a payment provider is connected.

## Success criteria
1. Visitor completes quiz without login and sees ranked careers.
2. Logged-in student saves result, earns points, appears on opt-in leaderboard.
3. Parent links to a student with the student's code and sees progress.
4. Admin activates a plan; premium report unlocks.
5. All writes CSRF-protected; automated tests pass.
