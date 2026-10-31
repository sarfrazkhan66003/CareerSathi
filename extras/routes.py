import json, secrets, time
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func
import app as core
from .models import XQuizResult, XPoint, XProfile, XPlanRequest, XReferral, XParentLink
from . import data as D
from . import logic as L

router = APIRouter()
SessionLocal, User, Booking, Feedback, Inquiry = core.SessionLocal, core.User, core.Booking, core.Feedback, core.Inquiry
MentorCredentials, StudentJourney = core.MentorCredentials, core.StudentJourney
vt = core.validate_text
COMMON = dict(TYPES=D.TYPES, PLANS=D.PLANS)

def page(request, name, **ctx):
    return core.render(request, name, **COMMON, **ctx)

# ---------- helpers ----------
def profile_for(db, user):
    p = db.query(XProfile).filter_by(user_id=user.id).first()
    if not p:
        p = XProfile(user_id=user.id, referral_code=L.new_code(), link_code=L.new_code())
        db.add(p); db.commit(); db.refresh(p)
    return p

def award(db, user_id, action, ref=''):
    """Idempotent: (user, action, ref) can only score once."""
    if db.query(XPoint).filter_by(user_id=user_id, action=action, ref=ref).first():
        return 0
    pts = D.POINTS.get(action, 0)
    db.add(XPoint(user_id=user_id, action=action, ref=ref, points=pts)); db.commit()
    return pts

def total_points(db, uid):
    return db.query(func.coalesce(func.sum(XPoint.points), 0)).filter(XPoint.user_id == uid).scalar() or 0

def plan_of(db, user):
    if not user: return 'free'
    if user.role == 'admin': return 'pro'
    p = profile_for(db, user)
    if p.plan in ('plus', 'pro') and (not p.plan_until or p.plan_until > datetime.utcnow()):
        return p.plan
    return 'free'

def claim_referral(request, db, user):
    code = request.cookies.get('cs_ref')
    if not code: return
    ref = db.query(XProfile).filter_by(referral_code=code).first()
    if not ref or ref.user_id == user.id: return
    if db.query(XReferral).filter_by(referee_id=user.id).first(): return
    if (datetime.utcnow() - user.created_at) > timedelta(days=2): return
    db.add(XReferral(referrer_id=ref.user_id, referee_id=user.id)); db.commit()
    award(db, ref.user_id, 'referral', 'u%d' % user.id)
    award(db, user.id, 'referred', 'welcome')

def parse_scores(s):
    return {k: int(v) for k, v in (x.split(':') for x in s.split(','))}

def need_user(request, db, roles=None):
    return core.must_login(request, db, role=roles)

# ---------- Career Compass ----------
@router.get('/career-quiz')
def quiz_page(request: Request):
    return page(request, 'x_quiz.html', questions=list(enumerate(D.QUESTIONS)))

@router.post('/career-quiz')
async def quiz_submit(request: Request):
    form = await request.form()
    core.require_csrf(request, form.get('csrf_token'))
    try:
        answers = [int(form.get('q%d' % i, 0)) for i in range(len(D.QUESTIONS))]
        scores = L.score_quiz(answers)
    except ValueError:
        raise HTTPException(400, 'Please answer all 24 questions.')
    token = secrets.token_urlsafe(9)
    with SessionLocal() as db:
        user = core.current_user(request, db)
        db.add(XQuizResult(token=token, user_id=user.id if user else None,
                           scores=','.join('%s:%d' % kv for kv in scores.items()), top=''.join(L.top_types(scores))))
        db.commit()
        if user:
            award(db, user.id, 'quiz', token)
            claim_referral(request, db, user)
    return core.redirect('/career-quiz/result/' + token)

def load_result(db, token):
    r = db.query(XQuizResult).filter_by(token=token[:40]).first()
    if not r: raise HTTPException(404, 'Result not found')
    return r

@router.get('/career-quiz/result/{token}')
def quiz_result(request: Request, token: str):
    with SessionLocal() as db:
        r = load_result(db, token); scores = parse_scores(r.scores)
        user = core.current_user(request, db); plan = plan_of(db, user)
    ranked = L.rank_careers(scores)
    return page(request, 'x_result.html', token=token, scores=scores, pct=L.percent(scores), top=L.top_types(scores), ranked=ranked[:3], plan=plan, order=L.ORDER)

@router.get('/report/{token}')
def report(request: Request, token: str):
    with SessionLocal() as db:
        r = load_result(db, token); scores = parse_scores(r.scores)
        user = core.current_user(request, db); plan = plan_of(db, user)
        owner_ok = (r.user_id is None) or (user and (user.id == r.user_id or user.role == 'admin'))
    unlocked = plan in ('plus', 'pro') and owner_ok
    ranked = L.rank_careers(scores)
    return page(request, 'x_report.html', token=token, scores=scores, pct=L.percent(scores), top=L.top_types(scores), ranked=ranked[:8 if unlocked else 3],
                unlocked=unlocked, plan=plan, order=L.ORDER, generated=datetime.utcnow())

# ---------- Roadmaps ----------
@router.get('/roadmaps')
def roadmaps(request: Request, q: str = ''):
    items = [c for c in D.CAREERS if not q or q.lower()[:60] in (c['title'] + c['summary']).lower()]
    return page(request, 'x_roadmaps.html', careers=items, q=q)

@router.get('/roadmaps/{slug}')
def roadmap(request: Request, slug: str):
    c = D.CAREER_BY_SLUG.get(slug)
    if not c: raise HTTPException(404, 'Roadmap not found')
    with SessionLocal() as db:
        user = core.current_user(request, db)
        if user: award(db, user.id, 'roadmap', slug)
    return page(request, 'x_roadmap.html', c=c)

# ---------- Mentor Match ----------
@router.get('/match')
def match(request: Request, interests: str = '', exam: str = '', city: str = '', state: str = '', goal: str = ''):
    with SessionLocal() as db:
        user = core.current_user(request, db)
        prefill = dict(interests=interests, exam=exam, city=city, state=state, goal=goal)
        if user and user.role == 'student' and not any(prefill.values()):
            j = db.query(StudentJourney).filter_by(user_id=user.id).first()
            if j: prefill = dict(interests=(j.interests or '').replace(',', ' '), exam=j.exam or '', city=j.city or '', state=j.state or '', goal=j.aim or '')
        searched = any(v.strip() for v in (interests, exam, city, state, goal))
        results = []
        if searched:
            rows = db.query(User, MentorCredentials).outerjoin(MentorCredentials, MentorCredentials.user_id == User.id)\
                .filter(User.role == 'mentor', User.verified == True, User.active == True).all()
            mentors = [dict(id=u.id, name=u.name, expertise=u.expertise, bio=u.bio, city=u.city, stream=(c.stream if c else ''), university=(c.university if c else ''),
                            exam=(c.exam if c else ''), degree=(c.degree if c else ''), company=(c.company if c else '')) for u, c in rows]
            results = L.match_mentors(dict(interests=interests, exam=exam, city=city, state=state, goal=goal), mentors)[:8]
            if user: award(db, user.id, 'match', 'first')
    return page(request, 'x_match.html', prefill=prefill, results=results, searched=searched)

# ---------- Rewards, leaderboard, referral ----------
@router.get('/rewards')
def rewards(request: Request):
    with SessionLocal() as db:
        user = need_user(request, db); claim_referral(request, db, user)
        p = profile_for(db, user); pts = total_points(db, user.id)
        hist = db.query(XPoint).filter_by(user_id=user.id).order_by(XPoint.created_at.desc()).limit(12).all()
        history = [(h.action, h.points, h.created_at) for h in hist]
        refs = db.query(XReferral).filter_by(referrer_id=user.id).count()
        info = dict(code=p.referral_code, link=p.link_code, optin=p.leaderboard_optin, plan=plan_of(db, user), refs=refs)
    badge, nxt = L.badge_for(pts)
    return page(request, 'x_rewards.html', pts=pts, badge=badge, nxt=nxt, history=history, info=info, base=str(request.base_url).rstrip('/'), badges=D.BADGES, POINTS=D.POINTS)

@router.post('/rewards/settings')
def rewards_settings(request: Request, action: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        user = need_user(request, db); p = profile_for(db, user)
        if action == 'optin': p.leaderboard_optin = True
        elif action == 'optout': p.leaderboard_optin = False
        elif action == 'newcode': p.link_code = L.new_code()
        else: raise HTTPException(400, 'Unknown action')
        db.commit()
    core.notice(request, 'Settings updated.'); return core.redirect('/rewards')

@router.get('/join/{code}')
def join(request: Request, code: str):
    with SessionLocal() as db:
        ok = db.query(XProfile).filter_by(referral_code=code[:12].upper()).first()
    resp = core.redirect('/register')
    if ok: resp.set_cookie('cs_ref', code[:12].upper(), max_age=60 * 60 * 24 * 30, httponly=True, samesite='lax')
    return resp

@router.get('/leaderboard')
def leaderboard(request: Request):
    with SessionLocal() as db:
        rows = db.query(User.name, func.sum(XPoint.points).label('p')).join(XPoint, XPoint.user_id == User.id)\
            .join(XProfile, XProfile.user_id == User.id).filter(XProfile.leaderboard_optin == True, User.active == True)\
            .group_by(User.id, User.name).order_by(func.sum(XPoint.points).desc()).limit(20).all()
        board = [(L.public_name(n), int(p), L.badge_for(int(p))[0][1]) for n, p in rows]
    return page(request, 'x_leaderboard.html', board=board)

# ---------- FAQ assistant ----------
@router.get('/assistant')
def assistant_page(request: Request):
    return page(request, 'x_assistant.html')

@router.post('/assistant/ask')
async def assistant_ask(request: Request):
    if not request.headers.get('x-csrf') or request.headers.get('x-csrf') != request.session.get('csrf'):
        return JSONResponse({'error': 'Security token missing. Refresh the page.'}, status_code=403)
    hits = [t for t in request.session.get('x_rl', []) if time.time() - t < 600]
    if len(hits) >= 30: return JSONResponse({'error': 'Too many questions. Please wait a few minutes.'}, status_code=429)
    hits.append(time.time()); request.session['x_rl'] = hits
    try: q = str((await request.json()).get('q', ''))[:300]
    except Exception: q = ''
    ans = L.faq_answer(q)
    if not ans:
        return {'answer': "I could not find that in my FAQ. Try the Career Compass quiz, browse Roadmaps, or send us a message from the Contact page.", 'found': False}
    return {'answer': ans, 'found': True}

@router.get('/faq')
def faq(request: Request):
    return page(request, 'x_faq.html', faq=list(zip(D.FAQ_TITLES, [a for _, a in D.FAQ])))

# ---------- Parent dashboard ----------
@router.get('/parent')
def parent(request: Request):
    with SessionLocal() as db:
        user = need_user(request, db, ['parent', 'admin'])
        links = db.query(XParentLink, User).join(User, User.id == XParentLink.student_id).filter(XParentLink.parent_id == user.id).all()
        kids = []
        for l, s in links:
            pts = total_points(db, s.id)
            quiz = db.query(XQuizResult).filter_by(user_id=s.id).order_by(XQuizResult.created_at.desc()).first()
            journey = db.query(StudentJourney).filter_by(user_id=s.id).first()
            bks = db.query(Booking).filter(Booking.user_id == s.id).order_by(Booking.created_at.desc()).limit(5).all()
            kids.append(dict(link_id=l.id, name=L.public_name(s.name), pts=pts, badge=L.badge_for(pts)[0][1], top=[D.TYPES[t][0] for t in (quiz.top if quiz else '')],
                             stage=journey.stage if journey else 'registered', grade=journey.grade if journey else s.grade,
                             bookings=[(b.kind, b.status, b.scheduled_at) for b in bks]))
    return page(request, 'x_parent.html', kids=kids)

@router.post('/parent/link')
def parent_link(request: Request, code: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        user = need_user(request, db, ['parent', 'admin'])
        p = db.query(XProfile).filter_by(link_code=code.strip().upper()[:12]).first()
        if not p or p.user_id == user.id: raise HTTPException(400, 'That code is not valid. Ask your child to copy it again from Rewards.')
        s = db.get(User, p.user_id)
        if not s or s.role != 'student' or not s.active: raise HTTPException(400, 'That code is not valid.')
        if not db.query(XParentLink).filter_by(parent_id=user.id, student_id=s.id).first():
            db.add(XParentLink(parent_id=user.id, student_id=s.id)); db.commit()
            award(db, s.id, 'parent_link', 'p%d' % user.id)
    core.notice(request, 'Student linked. You can now see their progress.'); return core.redirect('/parent')

@router.post('/parent/unlink/{link_id}')
def parent_unlink(request: Request, link_id: int, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        user = need_user(request, db, ['parent', 'admin'])
        l = db.get(XParentLink, link_id)
        if not l or l.parent_id != user.id: raise HTTPException(404)
        db.delete(l); db.commit()
    core.notice(request, 'Link removed.'); return core.redirect('/parent')

# ---------- Pricing / plans ----------
@router.get('/pricing')
def pricing(request: Request):
    with SessionLocal() as db:
        user = core.current_user(request, db); plan = plan_of(db, user)
        pending = db.query(XPlanRequest).filter_by(user_id=user.id, status='requested').first() if user else None
        pending = pending.plan if pending else None
    return page(request, 'x_pricing.html', current=plan, pending=pending)

@router.post('/pricing/request')
def pricing_request(request: Request, plan: str = Form(...), note: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if plan not in ('plus', 'pro'): raise HTTPException(400, 'Choose a paid plan')
    with SessionLocal() as db:
        user = need_user(request, db)
        if db.query(XPlanRequest).filter_by(user_id=user.id, status='requested').first(): raise HTTPException(400, 'You already have a pending request.')
        db.add(XPlanRequest(user_id=user.id, plan=plan, note=vt(note, 300))); db.commit()
    core.notice(request, 'Plan request received. No payment has been taken; our team will contact you to confirm.'); return core.redirect('/pricing')

# ---------- Resume builder ----------
@router.get('/resume-builder')
def resume_form(request: Request):
    return page(request, 'x_resume.html')

@router.post('/resume-builder')
def resume_view(request: Request, name: str = Form(...), email: str = Form(''), phone: str = Form(''), city: str = Form(''), objective: str = Form(''),
                education: str = Form(''), skills: str = Form(''), projects: str = Form(''), achievements: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if len(name.strip()) < 2: raise HTTPException(400, 'Enter your name')
    lines = lambda s, n: [x.strip() for x in vt(s, n).splitlines() if x.strip()][:12]
    r = dict(name=vt(name, 80), email=vt(email, 120), phone=vt(phone, 30), city=vt(city, 80), objective=vt(objective, 500), education=lines(education, 1200),
             skills=[x.strip() for x in vt(skills, 400).split(',') if x.strip()][:20], projects=lines(projects, 1500), achievements=lines(achievements, 1200))
    with SessionLocal() as db:
        user = core.current_user(request, db)
        if user: award(db, user.id, 'resume', 'first')
    return page(request, 'x_resume_view.html', r=r)

# ---------- Static-content pages ----------
@router.get('/study-abroad')
def abroad(request: Request):
    return page(request, 'x_abroad.html', steps=D.ABROAD_STEPS, check=D.ABROAD_CHECK, sch=D.SCHOLAR)

@router.get('/partners')
def partners(request: Request):
    return page(request, 'x_partners.html')

@router.post('/partners')
def partners_submit(request: Request, org_type: str = Form(...), org_name: str = Form(...), contact_name: str = Form(...), email: str = Form(...), city: str = Form(''), message: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if org_type not in ('School', 'College / University', 'NGO', 'Company / Internship provider', 'Coaching institute', 'Other') or '@' not in email or len(message.strip()) < 10:
        raise HTTPException(400, 'Please complete all required fields.')
    with SessionLocal() as db:
        db.add(Inquiry(name=vt(contact_name, 130), email=vt(email, 230), topic='Partnership: ' + org_type,
                       message=vt('Organisation: %s\nCity: %s\n\n%s' % (org_name[:150], city[:80], message), 4000))); db.commit()
    core.notice(request, 'Thank you! Our team will reach out about a partnership.'); return core.redirect('/partners')

# ---------- Feedback ----------
@router.get('/feedback')
def feedback_form(request: Request):
    with SessionLocal() as db: need_user(request, db)
    return page(request, 'x_feedback.html')

@router.post('/feedback')
def feedback_submit(request: Request, rating: int = Form(...), message: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if not 1 <= rating <= 5 or len(message.strip()) < 10: raise HTTPException(400, 'Give a rating and at least 10 characters of feedback.')
    with SessionLocal() as db:
        user = need_user(request, db)
        db.add(Feedback(user_id=user.id, rating=rating, message=vt(message, 1500))); db.commit()
        got = award(db, user.id, 'feedback', 'first')
    core.notice(request, 'Thank you for your feedback!' + (' +%d points.' % got if got else '')); return core.redirect('/feedback')

# ---------- Admin growth console ----------
@router.get('/admin/growth')
def admin_growth(request: Request):
    with SessionLocal() as db:
        core.must_login(request, db, role=['admin'])
        reqs = db.query(XPlanRequest, User).join(User, User.id == XPlanRequest.user_id).order_by(XPlanRequest.created_at.desc()).limit(50).all()
        fb = db.query(Feedback, User).join(User, User.id == Feedback.user_id).order_by(Feedback.created_at.desc()).limit(30).all()
        avg = db.query(func.avg(Feedback.rating)).scalar()
        stats = dict(quizzes=db.query(XQuizResult).count(), points=int(db.query(func.coalesce(func.sum(XPoint.points), 0)).scalar()),
                     referrals=db.query(XReferral).count(), parents=db.query(XParentLink).count(), paid=db.query(XProfile).filter(XProfile.plan != 'free').count(),
                     pending=db.query(XPlanRequest).filter_by(status='requested').count(), avg=round(avg, 1) if avg else '–')
        reqs = [(r.id, u.name, u.email, r.plan, r.status, r.payment_status, r.note, r.created_at) for r, u in reqs]
        fb = [(u.name, f.rating, f.message, f.created_at) for f, u in fb]
    return page(request, 'x_admin.html', reqs=reqs, fb=fb, stats=stats)

@router.post('/admin/growth/plan/{rid}/{action}')
def admin_plan(request: Request, rid: int, action: str, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if action not in ('activate', 'reject'): raise HTTPException(400)
    with SessionLocal() as db:
        core.must_login(request, db, role=['admin'])
        r = db.get(XPlanRequest, rid)
        if not r or r.status != 'requested': raise HTTPException(404, 'Request not found or already handled')
        if action == 'activate':
            p = db.query(XProfile).filter_by(user_id=r.user_id).first()
            if not p: p = XProfile(user_id=r.user_id, referral_code=L.new_code(), link_code=L.new_code()); db.add(p)
            p.plan, p.plan_until = r.plan, datetime.utcnow() + timedelta(days=365)
            r.status, r.payment_status = 'active', 'confirmed_manually'
        else:
            r.status = 'rejected'
        db.commit()
    core.notice(request, 'Plan request ' + {'activate': 'activated', 'reject': 'rejected'}[action] + '.'); return core.redirect('/admin/growth')
