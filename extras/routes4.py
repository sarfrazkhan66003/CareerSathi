"""v12 · Content & growth: practice, course progress, streaks, blog/SEO, finders, stories, reviews 2.0, internships,
language, PWA, health, admin tools (analytics, audit, outbox, import, approvals)."""
import csv, io, re, os, json, random
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import Response, JSONResponse, PlainTextResponse
from sqlalchemy import func
import app as core
from .models import XProfile, XPoint, XQuizResult
from .models2 import *
from . import services as S, data as D, data2 as D2, assess_data as AD, logic as L
from .routes import page, award, SessionLocal, User, Booking, vt, total_points
from .routes2 import flag_for, consent_ok, need_consent, college_names

router = APIRouter()
Item = core.Item
Review = core.Review

def _login(request, role=None):
    with SessionLocal() as db: u = core.must_login(request, db, role=role); return u.id

# ---------- practice: mock interview, coding ----------
@router.get('/practice')
def practice_hub(request: Request):
    with SessionLocal() as db:
        u = core.current_user(request, db)
        hist = db.query(XPractice).filter_by(user_id=u.id).order_by(XPractice.created_at.desc()).limit(6).all() if u else []
        hist = [(h.topic, h.score, h.total, h.created_at) for h in hist]
    return page(request, 'x_practice.html', topics=D2.PRACTICE_TOPICS, hist=hist, challenges=D2.CODING)

@router.get('/practice/{topic}')
def practice_run(request: Request, topic: str):
    if topic not in D2.PRACTICE_TOPICS: raise HTTPException(404, 'Unknown topic')
    title, qs = D2.PRACTICE_TOPICS[topic]
    return page(request, 'x_practice_run.html', topic=topic, title=title, qs=[(q[0], q[1], q[2]) for q in qs])

@router.post('/practice/{topic}')
async def practice_grade(request: Request, topic: str):
    if topic not in D2.PRACTICE_TOPICS: raise HTTPException(404)
    form = await request.form(); core.require_csrf(request, form.get('csrf_token')); title, qs = D2.PRACTICE_TOPICS[topic]
    rows, score = [], 0
    for qid, q, opts, a, why in qs:
        try: got = int(form.get('q_' + qid, -1))
        except ValueError: got = -1
        ok = got == a; score += ok; rows.append(dict(q=q, opts=opts, chosen=got, right=a, ok=ok, why=why))
    with SessionLocal() as db:
        u = core.current_user(request, db)
        if u:
            db.add(XPractice(user_id=u.id, topic=topic, score=score, total=len(qs))); db.commit(); award(db, u.id, 'practice', '%s-%s' % (topic, date.today().isoformat()))
    return page(request, 'x_practice_result.html', title=title, rows=rows, score=score, total=len(qs), topic=topic)

@router.post('/practice/challenge/solved')
def challenge_solved(request: Request, idx: int = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if not 0 <= idx < len(D2.CODING): raise HTTPException(400)
    with SessionLocal() as db:
        u = core.must_login(request, db); got = award(db, u.id, 'practice', 'challenge-%d' % idx)
    core.notice(request, 'Marked as solved.' + (' +%d points.' % got if got else '')); return core.redirect('/practice')

# ---------- course progress + certificate ----------
def sections_of(item): return [s.strip() for s in re.split(r'\n\s*\n', item.description or '') if s.strip()][:60]

@router.get('/progress/{item_id}')
def progress(request: Request, item_id: int):
    with SessionLocal() as db:
        u = core.must_login(request, db); it = db.get(Item, item_id)
        if not it or it.kind not in ('course', 'resource'): raise HTTPException(404, 'Course not found')
        secs = sections_of(it); done = {l.idx for l in db.query(XLesson).filter_by(user_id=u.id, item_id=item_id)}
        data = dict(item=dict(id=it.id, title=it.title, kind=it.kind), secs=[(i, s[:600], i in done) for i, s in enumerate(secs)], pct=round(len(done) / len(secs) * 100) if secs else 0)
    return page(request, 'x_progress.html', **data)

@router.post('/progress/{item_id}/toggle')
def progress_toggle(request: Request, item_id: int, idx: int = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db); it = db.get(Item, item_id)
        if not it or it.kind not in ('course', 'resource'): raise HTTPException(404)
        n = len(sections_of(it))
        if not 0 <= idx < n: raise HTTPException(400, 'Invalid lesson')
        row = db.query(XLesson).filter_by(user_id=u.id, item_id=item_id, idx=idx).first()
        if row: db.delete(row)
        else: db.add(XLesson(user_id=u.id, item_id=item_id, idx=idx))
        db.commit()
        if db.query(XLesson).filter_by(user_id=u.id, item_id=item_id).count() >= n: award(db, u.id, 'lesson_done', str(item_id))
    return core.redirect('/progress/%d#l%d' % (item_id, idx))

@router.get('/certificate/{item_id}')
def certificate(request: Request, item_id: int):
    with SessionLocal() as db:
        u = core.must_login(request, db); it = db.get(Item, item_id)
        if not it: raise HTTPException(404)
        n = len(sections_of(it)); done = db.query(XLesson).filter_by(user_id=u.id, item_id=item_id).count()
        if not n or done < n: raise HTTPException(400, 'Complete all lessons to unlock the certificate.')
        data = dict(name=u.name, title=it.title)
    return page(request, 'x_certificate.html', today=date.today(), **data)

# ---------- streak + weekly challenge ----------
def week_start(d=None): d = d or date.today(); return datetime.combine(d - timedelta(days=d.weekday()), datetime.min.time())

def weekly_status(db, uid):
    ws = week_start(); acts = [a for (a,) in db.query(XPoint.action).filter(XPoint.user_id == uid, XPoint.created_at >= ws).all()]
    tasks = [('Check in on 3 different days', acts.count('checkin') >= 3), ('Finish 1 assessment or practice set', ('assess' in acts or 'practice' in acts)), ('Read 2 career roadmaps', acts.count('roadmap') >= 2)]
    return tasks

def rewards_extra(db, user):
    s = db.query(XStreak).filter_by(user_id=user.id).first(); today = date.today()
    tasks = weekly_status(db, user.id); allok = all(ok for _, ok in tasks)
    if allok: award(db, user.id, 'weekly', week_start().date().isoformat())
    return dict(streak=(s.count if s and s.last_day and (today - s.last_day).days <= 1 else 0), best=s.best if s else 0, checked=bool(s and s.last_day == today), tasks=tasks)

@router.post('/rewards/checkin')
def checkin(request: Request, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db); today = date.today(); s = db.query(XStreak).filter_by(user_id=u.id).first()
        if not s: s = XStreak(user_id=u.id, count=0, best=0); db.add(s)
        if s.last_day == today: core.notice(request, 'Already checked in today. Come back tomorrow!'); return core.redirect('/rewards')
        s.count = s.count + 1 if s.last_day == today - timedelta(days=1) else 1; s.last_day = today; s.best = max(s.best or 0, s.count); db.commit()
        got = award(db, u.id, 'checkin', today.isoformat())
        if s.count % 7 == 0: got += award(db, u.id, 'streak7', today.isoformat())
    core.notice(request, 'Checked in! Streak: %d day(s). +%d points.' % (s.count, got)); return core.redirect('/rewards')

# ---------- blog, sitemap, robots ----------
def ensure_posts():
    with SessionLocal() as db:
        if db.query(XPost).count() == 0:
            for slug, title, summary, body in D2.POSTS: db.add(XPost(slug=slug, title=title, summary=summary, body=body))
            db.commit()

@router.get('/blog')
def blog(request: Request):
    ensure_posts()
    with SessionLocal() as db: rows = [(p.slug, p.title, p.summary, p.created_at) for p in db.query(XPost).filter_by(published=True).order_by(XPost.created_at.desc(), XPost.id.desc()).all()]
    return page(request, 'x_blog.html', rows=rows)

@router.get('/blog/{slug}')
def blog_post(request: Request, slug: str):
    ensure_posts()
    with SessionLocal() as db:
        p = db.query(XPost).filter_by(slug=slug[:120], published=True).first()
        if not p: raise HTTPException(404, 'Article not found')
        data = dict(title=p.title, summary=p.summary, paras=[x.strip() for x in re.split(r'\n\s*\n', p.body) if x.strip()], at=p.created_at, slug=p.slug)
    return page(request, 'x_blog_post.html', **data)

@router.get('/sitemap.xml')
def sitemap():
    ensure_posts(); base = S.site_url()
    urls = ['/', '/about', '/contact', '/career-quiz', '/roadmaps', '/pricing', '/faq', '/blog', '/study-abroad', '/partners', '/internships', '/scholarships', '/college-predictor', '/practice', '/stories', '/colleges', '/mentors', '/resume-builder']
    urls += ['/roadmaps/' + c['slug'] for c in D.CAREERS]
    with SessionLocal() as db:
        urls += ['/blog/' + p.slug for p in db.query(XPost).filter_by(published=True)]
        urls += ['/item/%d' % i.id for i in db.query(Item).filter_by(published=True).limit(500)]
    body = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>%s%s</loc></url>' % (base, u) for u in urls) + '</urlset>'
    return Response(body, media_type='application/xml')

@router.get('/robots.txt')
def robots():
    return PlainTextResponse('User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /dashboard\nDisallow: /rewards\nDisallow: /parent\nSitemap: %s/sitemap.xml\n' % S.site_url())

# ---------- finders ----------
@router.get('/scholarships')
def scholarship_finder(request: Request, state: str = '', category: str = '', level: str = '', income: str = ''):
    searched = bool(category and level)
    res = D2.scholarships(state[:60], category, level, income) if searched and category in D2.CAT and level in dict(D2.LEVELS) else []
    return page(request, 'x_scholarships.html', cats=D2.CAT, levels=D2.LEVELS, incomes=D2.INCOME, q=dict(state=state, category=category, level=level, income=income), res=res, searched=searched)

@router.get('/college-predictor')
def predictor(request: Request, exam: str = '', rank: str = ''):
    msg, link, err = '', '', ''
    if exam or rank:
        if exam not in D2.PREDICT_EXAMS: err = 'Choose an exam.'
        elif not rank.isdigit() or not 1 <= int(rank) <= 5000000: err = 'Enter your rank as a number.'
        else: msg, link = D2.predict_bands(exam, int(rank)), D2.PREDICT_EXAMS[exam]
    return page(request, 'x_predictor.html', exams=list(D2.PREDICT_EXAMS), exam=exam, rank=rank, msg=msg, link=link, err=err)

# ---------- stories (testimonials) ----------
@router.get('/stories')
def stories(request: Request):
    with SessionLocal() as db: rows = [(t.text, t.label, t.created_at) for t in db.query(XTestimonial).filter_by(approved=True).order_by(XTestimonial.created_at.desc()).limit(30)]
    return page(request, 'x_stories.html', rows=rows)

@router.post('/stories/submit')
def story_submit(request: Request, text: str = Form(...), label: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if len(text.strip()) < 30: raise HTTPException(400, 'Please write at least 30 characters about your real experience.')
    with SessionLocal() as db:
        u = core.must_login(request, db)
        if db.query(XTestimonial).filter_by(user_id=u.id, approved=False).count() >= 2: raise HTTPException(400, 'You already have stories waiting for review.')
        db.add(XTestimonial(user_id=u.id, text=vt(text, 800), label=vt(label, 80) or u.role.title())); db.commit(); award(db, u.id, 'story', 'first')
    core.notice(request, 'Thank you! Your story will appear after admin review.'); return core.redirect('/stories')

def approved_stories(n=3):
    try:
        with SessionLocal() as db: return [(t.text, t.label) for t in db.query(XTestimonial).filter_by(approved=True).order_by(XTestimonial.created_at.desc()).limit(n)]
    except Exception: return []

# ---------- college reviews 2.0 ----------
@router.get('/reviews')
def reviews(request: Request, college: str = ''):
    with SessionLocal() as db:
        votes = dict(db.query(XReviewVote.review_id, func.count()).group_by(XReviewVote.review_id).all())
        q = db.query(Review, User).join(User, User.id == Review.author_id).filter(Review.approved == True)
        if college: q = q.filter(Review.college == college[:180])
        rows = q.order_by(Review.created_at.desc()).limit(200).all()
        agg = db.query(Review.college, func.avg(Review.rating), func.count()).filter(Review.approved == True).group_by(Review.college).order_by(func.count().desc()).limit(40).all()
        mine = {v.review_id for v in db.query(XReviewVote).filter_by(user_id=core.current_user(request, db).id)} if core.current_user(request, db) else set()
        items = sorted([dict(id=r.id, college=r.college, rating=r.rating, text=r.text, at=r.created_at, votes=votes.get(r.id, 0), voted=r.id in mine,
                             badge=('Verified mentor' if (u.role == 'mentor' and u.verified) else ''), who=L.public_name(u.name)) for r, u in rows], key=lambda x: (-x['votes'], x['at']), reverse=False)
    return page(request, 'x_reviews.html', items=items, agg=[(c, round(float(a), 1), n) for c, a, n in agg], college=college)

@router.post('/reviews/{rid}/vote')
def review_vote(request: Request, rid: int, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db); r = db.get(Review, rid)
        if not r or not r.approved: raise HTTPException(404)
        if r.author_id == u.id: raise HTTPException(400, 'You cannot vote on your own review.')
        ex = db.query(XReviewVote).filter_by(review_id=rid, user_id=u.id).first()
        if ex: db.delete(ex)
        else: db.add(XReviewVote(review_id=rid, user_id=u.id))
        db.commit()
    return core.redirect('/reviews')

# ---------- internship board ----------
@router.get('/internships')
def internships(request: Request, q: str = ''):
    with SessionLocal() as db:
        qs = db.query(XInternship).filter_by(status='approved')
        if q: qs = qs.filter(XInternship.title.ilike('%' + q[:60] + '%') | XInternship.company.ilike('%' + q[:60] + '%'))
        rows = [(i.id, i.title, i.company, i.location, i.stipend, i.apply_by) for i in qs.order_by(XInternship.created_at.desc()).limit(60)]
    return page(request, 'x_internships.html', rows=rows, q=q)

@router.get('/internships/post')
def internship_post_form(request: Request): return page(request, 'x_internship_post.html')

@router.post('/internships/post')
def internship_post(request: Request, company: str = Form(...), contact_name: str = Form(...), contact_email: str = Form(...), title: str = Form(...), description: str = Form(...),
                    location: str = Form(''), stipend: str = Form(''), apply_by: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if '@' not in contact_email or len(title.strip()) < 4 or len(description.strip()) < 30 or len(company.strip()) < 2: raise HTTPException(400, 'Please fill all required fields (description: at least 30 characters).')
    with SessionLocal() as db:
        db.add(XInternship(company=vt(company, 150), contact_name=vt(contact_name, 130), contact_email=vt(contact_email, 230).lower(), title=vt(title, 180), description=vt(description, 3000), location=vt(location, 100), stipend=vt(stipend, 60), apply_by=vt(apply_by, 20))); db.commit()
    core.notice(request, 'Thank you. Your internship will be listed after admin review.'); return core.redirect('/internships')

@router.get('/internships/{iid}')
def internship_detail(request: Request, iid: int):
    with SessionLocal() as db:
        i = db.get(XInternship, iid)
        if not i or i.status != 'approved': raise HTTPException(404, 'Internship not found')
        u = core.current_user(request, db); applied = bool(u and db.query(XApplication).filter_by(internship_id=iid, user_id=u.id).first())
        data = dict(i=dict(id=i.id, title=i.title, company=i.company, description=i.description, location=i.location, stipend=i.stipend, apply_by=i.apply_by), applied=applied)
    return page(request, 'x_internship.html', **data)

@router.post('/internships/{iid}/apply')
def internship_apply(request: Request, iid: int, message: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['student']); need_consent(request, db, u); i = db.get(XInternship, iid)
        if not i or i.status != 'approved': raise HTTPException(404)
        if db.query(XApplication).filter_by(internship_id=iid, user_id=u.id).first(): raise HTTPException(400, 'You have already applied.')
        db.add(XApplication(internship_id=iid, user_id=u.id, message=vt(message, 1500))); db.commit(); award(db, u.id, 'internship', str(iid))
        S.send_email(i.contact_email, 'New applicant: %s' % i.title, 'Applicant: %s (%s), class %s.\nMessage: %s' % (u.name, u.email, u.grade or 'n/a', vt(message, 800)))
        S.send_email(u.email, 'Application sent: %s' % i.title, 'Your application to %s for "%s" was sent. The company may contact you directly.' % (i.company, i.title))
    core.notice(request, 'Application sent.'); return core.redirect('/internships/%d' % iid)

# ---------- language, PWA, health ----------
@router.get('/lang/{code}')
def lang(request: Request, code: str):
    ref = request.headers.get('referer', ''); base = str(request.base_url)
    resp = core.redirect(ref if ref.startswith(base) else '/')
    resp.set_cookie('lang', 'hi' if code == 'hi' else 'en', max_age=31536000, samesite='lax'); return resp

SW = """const V='cs-v12';const PRE=['/offline','/static/style.css','/static/extras.css','/static/main.js','/static/extras.js'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(PRE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);if(u.origin!==location.origin)return;
 if(u.pathname.startsWith('/static/')){e.respondWith(caches.match(r).then(m=>m||fetch(r).then(x=>{const c=x.clone();caches.open(V).then(ch=>ch.put(r,c));return x})));return}
 if(r.mode==='navigate'){e.respondWith(fetch(r).catch(()=>caches.match('/offline')))}});"""

@router.get('/sw.js')
def sw(): return Response(SW, media_type='application/javascript', headers={'Cache-Control': 'no-cache', 'Service-Worker-Allowed': '/'})

@router.get('/offline')
def offline(request: Request): return page(request, 'x_offline.html')

@router.get('/health/deep')
def health_deep():
    try:
        with SessionLocal() as db: users = db.query(func.count(User.id)).scalar(); db.query(XOutbox).count()
        return {'status': 'ok', 'db': 'ok', 'users': users, 'smtp': bool(S.env('SMTP_HOST')), 'razorpay': S.razorpay_enabled(), 'ai': S.ai_enabled(), 'captcha': S.captcha_enabled()}
    except Exception as e: return JSONResponse({'status': 'error', 'db': 'down'}, status_code=503)

# ---------- admin tools ----------
def _admin(request):
    with SessionLocal() as db: return core.must_login(request, db, role=['admin']).id

@router.get('/admin/hub')
def admin_hub(request: Request):
    _admin(request); return page(request, 'x_admin_hub.html')

@router.get('/admin/analytics')
def analytics(request: Request):
    _admin(request); since = datetime.utcnow() - timedelta(days=30)
    with SessionLocal() as db:
        distinct = lambda col, *f: db.query(func.count(func.distinct(col))).filter(*f).scalar() or 0
        steps = [('Unique visitors (30 days)', distinct(core.Visit.visitor, core.Visit.created_at > since)), ('Registered students', db.query(User).filter_by(role='student').count()),
                 ('Completed age & consent step', db.query(XUserFlag).filter(XUserFlag.dob != None).count()), ('Took an assessment', distinct(XAssessAttempt.user_id, XAssessAttempt.done == True)),
                 ('Sent an enquiry', distinct(XEnquiry.user_id)), ('Booked a session / seminar', distinct(Booking.user_id)), ('Paid or on a paid plan', db.query(XProfile).filter(XProfile.plan != 'free').count() + db.query(XPayment).filter_by(status='paid').count())]
        extra = dict(quizzes=db.query(XQuizResult).count(), attempts=db.query(XAssessAttempt).filter_by(done=True).count(), verified=db.query(XUserFlag).filter_by(email_verified=True).count(),
                     minors_pending=db.query(XUserFlag).filter(XUserFlag.guardian_email != '', XUserFlag.guardian_consent == False).count(), outbox=db.query(XOutbox).count())
    top = max(s[1] for s in steps) or 1
    return page(request, 'x_analytics.html', steps=[(n, v, round(v / top * 100)) for n, v in steps], extra=extra)

def _table(request, title, cols, rows, note='', form=None):
    return page(request, 'x_admin_table.html', title=title, cols=cols, rows=rows, note=note, form=form)

@router.get('/admin/audit')
def audit(request: Request):
    _admin(request)
    with SessionLocal() as db: rows = [dict(cells=[a.at.strftime('%d %b %H:%M'), a.user_id, a.method, a.path, a.status]) for a in db.query(XAudit).order_by(XAudit.id.desc()).limit(200)]
    return _table(request, 'Admin audit log', ['When (UTC)', 'User id', 'Method', 'Path', 'Status'], rows, 'Every admin POST action is recorded automatically.')

@router.get('/admin/outbox')
def outbox(request: Request):
    _admin(request)
    with SessionLocal() as db: rows = [dict(cells=[o.created_at.strftime('%d %b %H:%M'), o.to_email, o.subject, o.status, o.body[:140]]) for o in db.query(XOutbox).order_by(XOutbox.id.desc()).limit(100)]
    return _table(request, 'E-mail outbox', ['When', 'To', 'Subject', 'Status', 'Preview'], rows, 'Status "no_smtp" means SMTP is not configured: set SMTP_HOST, SMTP_USER and SMTP_PASSWORD in .env to send real emails.')

def _moderate(request, title, model, cols, make_cells, base, note=''):
    _admin(request)
    with SessionLocal() as db:
        rows = [dict(cells=make_cells(x), forms=([('%s/%d/approve' % (base, x.id), 'Approve', 'btn-dark')] if getattr(x, 'status', None) == 'pending' or getattr(x, 'approved', True) is False else []) +
                 ([('%s/%d/reject' % (base, x.id), 'Reject', 'btn-outline')] if getattr(x, 'status', None) in ('pending', 'approved') or getattr(x, 'approved', None) is False else [])) for x in db.query(model).order_by(model.id.desc()).limit(80)]
    return _table(request, title, cols, rows, note)

@router.get('/admin/internships')
def admin_internships(request: Request):
    return _moderate(request, 'Internship submissions', XInternship, ['Company', 'Title', 'Contact', 'Status'], lambda i: [i.company, i.title, i.contact_email, i.status], '/admin/internships')

@router.post('/admin/internships/{iid}/{action}')
def admin_internship_act(request: Request, iid: int, action: str, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token); _admin(request)
    if action not in ('approve', 'reject'): raise HTTPException(400)
    with SessionLocal() as db:
        i = db.get(XInternship, iid)
        if not i: raise HTTPException(404)
        i.status = 'approved' if action == 'approve' else 'rejected'; db.commit()
        S.send_email(i.contact_email, 'Your internship listing was %s' % i.status, 'Your listing "%s" is now %s on CareerSathi.' % (i.title, i.status))
    return core.redirect('/admin/internships')

@router.get('/admin/stories')
def admin_stories(request: Request):
    return _moderate(request, 'Success stories awaiting review', XTestimonial, ['Label', 'Story', 'Approved'], lambda t: [t.label, t.text[:200], 'yes' if t.approved else 'no'], '/admin/stories', 'Only publish stories that are real and that the author agreed to share.')

@router.post('/admin/stories/{tid}/{action}')
def admin_story_act(request: Request, tid: int, action: str, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token); _admin(request)
    if action not in ('approve', 'reject'): raise HTTPException(400)
    with SessionLocal() as db:
        t = db.get(XTestimonial, tid)
        if not t: raise HTTPException(404)
        t.approved = action == 'approve'; db.commit()
    return core.redirect('/admin/stories')

@router.get('/admin/import')
def import_form(request: Request):
    _admin(request); return page(request, 'x_import.html', report=None)

@router.post('/admin/import')
async def import_run(request: Request, kind: str = Form(...), csrf_token: str = Form(...), file: UploadFile = File(...)):
    core.require_csrf(request, csrf_token); _admin(request)
    if kind not in ('items', 'colleges'): raise HTTPException(400, 'Choose what to import.')
    raw = await file.read(1_000_001)
    if len(raw) > 1_000_000: raise HTTPException(400, 'File is larger than 1 MB.')
    try: rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    except Exception: raise HTTPException(400, 'Could not read the file. Save it as UTF-8 CSV.')
    if len(rows) > 500: raise HTTPException(400, 'Maximum 500 rows per upload.')
    ok, errors = 0, []
    with SessionLocal() as db:
        for n, r in enumerate(rows, start=2):
            try:
                if kind == 'items':
                    k = (r.get('kind') or '').strip().lower()
                    if k not in core.KINDS or not (r.get('title') or '').strip(): raise ValueError('kind/title invalid')
                    when = datetime.fromisoformat(r['starts_at'].strip()) if (r.get('starts_at') or '').strip() else None
                    db.add(Item(kind=k, title=vt(r['title'], 220), subtitle=vt(r.get('subtitle'), 230), description=vt(r.get('description'), 20000), category=vt(r.get('category'), 90), location=vt(r.get('location'), 120),
                                starts_at=when, price=max(0, int(r.get('price') or 0)), capacity=max(0, int(r.get('capacity') or 0)), published=True))
                else:
                    name = vt(r.get('name'), 180)
                    if not name: raise ValueError('name missing')
                    if db.query(XCollege).filter_by(name=name).first(): raise ValueError('already exists')
                    db.add(XCollege(name=name, city=vt(r.get('city'), 80), state=vt(r.get('state'), 80), stream=vt(r.get('stream'), 80), url=vt(r.get('url'), 250)))
                db.commit(); ok += 1                      # commit per row so one bad row never discards good ones
            except Exception as e: db.rollback(); errors.append('Row %d: %s' % (n, e))
    return page(request, 'x_import.html', report=dict(ok=ok, errors=errors[:30], total=len(rows)))

@router.get('/admin/posts')
def admin_posts(request: Request):
    _admin(request); ensure_posts()
    with SessionLocal() as db: rows = [dict(cells=[p.title, p.slug, p.created_at.strftime('%d %b %Y')]) for p in db.query(XPost).order_by(XPost.id.desc())]
    return _table(request, 'Blog posts', ['Title', 'Slug', 'Date'], rows, 'Add a new article below.', form=dict(action='/admin/posts', fields=[('title', 'Title', 'text'), ('summary', 'Short summary', 'text'), ('body', 'Article (blank line between paragraphs)', 'textarea')]))

@router.post('/admin/posts')
def admin_post_add(request: Request, title: str = Form(...), summary: str = Form(''), body: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token); _admin(request)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:110] or 'post'
    with SessionLocal() as db:
        if db.query(XPost).filter_by(slug=slug).first(): slug += '-' + S.new_token(3).lower().replace('_', 'x').replace('-', 'y')
        db.add(XPost(slug=slug, title=vt(title, 200), summary=vt(summary, 300), body=vt(body, 20000))); db.commit()
    core.notice(request, 'Article published.'); return core.redirect('/admin/posts')
