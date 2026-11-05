"""v12 · Safety + onboarding: email verification, password reset, age/guardian consent, login throttle + CAPTCHA,
post-registration flow (/start), assessments and the enquiry form with mentor allotment."""
import json, hashlib, secrets
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import app as core
from .models import XProfile
from .models2 import *
from . import services as S, assess as A, assess_data as AD, data2 as D2, data3 as D3, logic as L
from .routes import page, award, profile_for, SessionLocal, User, StudentJourney, MentorCredentials, JourneyEnquiry, vt

router = APIRouter()
GATED_GRADES = ('8', '9', '10')

# ---------- helpers ----------
def user_grade(db, u):
    j = db.query(StudentJourney).filter_by(user_id=u.id).first()
    return (j.grade if j and j.grade else u.grade) or ''

def age_of(dob, today=None):
    t = today or date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))

def consent_ok(f):
    if not f or not f.dob: return False
    return age_of(f.dob) >= 18 or bool(f.guardian_consent)

def flag_for(db, u):
    f = db.query(XUserFlag).filter_by(user_id=u.id).first()
    if f: return f
    f = XUserFlag(user_id=u.id, verify_token=S.new_token(), verify_sent_at=datetime.utcnow()); db.add(f); db.commit(); db.refresh(f)
    S.send_email(u.email, 'Verify your CareerSathi email', 'Hi %s,\n\nPlease verify your email: %s/verify/%s\n\nIf you did not register, ignore this message.' % (u.name.split()[0], S.site_url(), f.verify_token))
    return f

def student_progress(db, u, f):
    kinds = set(AD.KINDS)
    done = db.query(XAssessAttempt).filter(XAssessAttempt.user_id == u.id, XAssessAttempt.done == True).first() is not None
    enq = db.query(XEnquiry).filter_by(user_id=u.id).first() is not None
    return dict(consent=bool(f.dob), assessment=done, enquiry=enq)

def needs_gate(db, u, f):
    if u.role != 'student' or user_grade(db, u) not in GATED_GRADES: return False
    p = student_progress(db, u, f)
    return not (p['consent'] and p['assessment'])

def need_consent(request, db, u):
    f = flag_for(db, u)
    if not consent_ok(f):
        core.notice(request, 'Please complete age and guardian consent first.')
        raise HTTPException(303, headers={'Location': '/start'})
    return f

def score_info(db, u):
    """Latest finished stream-type assessment: {'overall','pcts','kind','token'} or None."""
    rows = db.query(XAssessAttempt).filter(XAssessAttempt.user_id == u.id, XAssessAttempt.done == True).order_by(XAssessAttempt.id.desc()).all()
    for a in rows:
        try: res = json.loads(a.result or '{}')
        except ValueError: continue
        if 'overall' in res and AD.KINDS.get(a.kind, {}).get('stream'):
            return dict(overall=int(res['overall']), pcts=res.get('pcts', {}), kind=a.kind, token=a.token)
    return None

def science_locked(si, grade_a='', grade_b=''):
    """Class 8-10 students scoring below the threshold do not get Science streams by default."""
    return bool(si) and si['overall'] < D3.THRESHOLD and (grade_a in GATED_GRADES or grade_b in GATED_GRADES)

def need_assessment(request, db, u, form_grade=''):
    """Students in Class 8-10 must finish the stream assessment before the enquiry form (also blocks direct URL access)."""
    if u.role != 'student': return
    if user_grade(db, u) not in GATED_GRADES and form_grade not in GATED_GRADES: return
    if db.query(XAssessAttempt).filter(XAssessAttempt.user_id == u.id, XAssessAttempt.done == True).first(): return
    core.notice(request, 'Please complete your assessment first. It helps us suggest the right stream before you send an enquiry.')
    raise HTTPException(303, headers={'Location': '/start'})

# ---------- middleware (innermost: sees the session) ----------
class V12Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path, uid = request.url.path, request.session.get('uid')
        if request.method == 'GET' and uid and not path.startswith(('/static', '/health', '/sw.js', '/offline')):
            try:
                with SessionLocal() as db:
                    u = db.get(User, uid)
                    if u and u.active:
                        f = flag_for(db, u); request.state.x_unverified = not f.email_verified
                        if path in ('/dashboard', '/journey') and needs_gate(db, u, f):
                            return RedirectResponse('/start', 303)
            except Exception as e: S.log.error('v12 middleware: %s', e)
        resp = await call_next(request)
        if request.method == 'POST' and path.startswith('/admin'):
            try:
                with SessionLocal() as db: db.add(XAudit(user_id=uid, method='POST', path=path[:200], status=resp.status_code)); db.commit()
            except Exception: pass
        return resp

# ---------- email verification ----------
@router.get('/verify/{token}')
def verify(request: Request, token: str):
    with SessionLocal() as db:
        f = db.query(XUserFlag).filter_by(verify_token=token[:60]).first()
        if not f: raise HTTPException(404, 'This verification link is invalid or already used.')
        f.email_verified, f.verify_token = True, None; db.commit()
    core.notice(request, 'Email verified. Thank you!'); return core.redirect('/dashboard')

@router.post('/verify/resend')
def verify_resend(request: Request, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db); f = flag_for(db, u)
        if f.email_verified: return core.redirect('/dashboard')
        if f.verify_sent_at and datetime.utcnow() - f.verify_sent_at < timedelta(minutes=2): raise HTTPException(429, 'Please wait two minutes before requesting another email.')
        f.verify_token, f.verify_sent_at = S.new_token(), datetime.utcnow(); db.commit()
        S.send_email(u.email, 'Verify your CareerSathi email', 'Verify here: %s/verify/%s' % (S.site_url(), f.verify_token))
    core.notice(request, 'Verification email sent.'); return core.redirect(request.headers.get('referer', '/dashboard') if (request.headers.get('referer', '') or '').startswith(S.site_url()) else '/dashboard')

# ---------- password reset ----------
@router.get('/forgot-password')
def forgot_page(request: Request): return page(request, 'x_forgot.html')

@router.post('/forgot-password')
def forgot(request: Request, email: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = db.query(User).filter(User.email == email.lower().strip()[:230]).first()
        if u and u.active:
            recent = db.query(XReset).filter(XReset.user_id == u.id, XReset.expires_at > datetime.utcnow() + timedelta(minutes=55)).count()
            if recent < 3:
                tok = S.new_token(); db.add(XReset(user_id=u.id, token_hash=hashlib.sha256(tok.encode()).hexdigest(), expires_at=datetime.utcnow() + timedelta(hours=1))); db.commit()
                S.send_email(u.email, 'Reset your CareerSathi password', 'Reset link (valid for 1 hour): %s/reset-password/%s\n\nIf you did not ask for this, ignore this email.' % (S.site_url(), tok))
    core.notice(request, 'If that email is registered, a reset link has been sent.'); return core.redirect('/login')

def _reset_row(db, token):
    r = db.query(XReset).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not r or r.used or r.expires_at < datetime.utcnow(): raise HTTPException(400, 'This reset link is invalid or has expired. Request a new one.')
    return r

@router.get('/reset-password/{token}')
def reset_page(request: Request, token: str):
    with SessionLocal() as db: _reset_row(db, token)
    return page(request, 'x_reset.html', token=token)

@router.post('/reset-password/{token}')
def reset(request: Request, token: str, password: str = Form(...), confirm: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if len(password) < 10 or password != confirm: raise HTTPException(400, 'Passwords must match and be at least 10 characters.')
    with SessionLocal() as db:
        r = _reset_row(db, token); u = db.get(User, r.user_id)
        u.password = core.hash_password(password); r.used = True
        db.query(XReset).filter(XReset.user_id == u.id).update({'used': True}); db.commit()
        S.send_email(u.email, 'Your CareerSathi password was changed', 'If this was not you, contact us immediately.')
    core.notice(request, 'Password updated. Please log in.'); return core.redirect('/login')

# ---------- login throttle + CAPTCHA (wraps the existing login) ----------
@router.post('/login')
def login_guarded(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...), cf: str = Form('', alias='cf-turnstile-response')):
    ip = (request.client.host if request.client else 'unknown')[:60]; em = email.lower().strip()[:230]; since = datetime.utcnow() - timedelta(minutes=15)
    with SessionLocal() as db:
        bad_pair = db.query(XLoginAttempt).filter(XLoginAttempt.ip == ip, XLoginAttempt.email == em, XLoginAttempt.ok == False, XLoginAttempt.at > since).count()
        bad_ip = db.query(XLoginAttempt).filter(XLoginAttempt.ip == ip, XLoginAttempt.ok == False, XLoginAttempt.at > since).count()
    if bad_pair >= 5 or bad_ip >= 30: raise HTTPException(429, 'Too many failed attempts. Please try again in 15 minutes or reset your password.')
    if not S.captcha_ok(cf, ip): raise HTTPException(400, 'CAPTCHA check failed. Please try again.')
    try:
        resp = core.login(request, email, password, csrf_token)
    except HTTPException as e:
        if e.status_code == 401:
            with SessionLocal() as db: db.add(XLoginAttempt(ip=ip, email=em, ok=False)); db.commit()
        raise
    with SessionLocal() as db: db.add(XLoginAttempt(ip=ip, email=em, ok=True)); db.commit()
    return resp

@router.get('/journey')
def journey_gate(request: Request):
    """Same page as before; new students go through /start first (see V12Middleware)."""
    return core.journey_page(request)

# ---------- onboarding hub ----------
@router.get('/start')
def start(request: Request):
    with SessionLocal() as db:
        u = core.must_login(request, db)
        if u.role != 'student': return core.redirect('/dashboard')
        f = flag_for(db, u); g = user_grade(db, u); prog = student_progress(db, u, f)
        kinds = [(k, AD.KINDS[k]) for k in A.audience(g)]
        data = dict(grade=g, prog=prog, kinds=kinds, gated=g in GATED_GRADES, minor=bool(f.dob and age_of(f.dob) < 18), approved=bool(f.guardian_consent),
                    dob=f.dob, gname=f.guardian_name, gemail=f.guardian_email, verified=f.email_verified)
    return page(request, 'x_start.html', **data)

@router.post('/start/consent')
def start_consent(request: Request, dob: str = Form(...), guardian_name: str = Form(''), guardian_email: str = Form(''), accept: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    try: d = date.fromisoformat(dob)
    except ValueError: raise HTTPException(400, 'Enter a valid date of birth.')
    if not 8 <= age_of(d) <= 80 or d > date.today(): raise HTTPException(400, 'Enter a valid date of birth.')
    if accept != 'yes': raise HTTPException(400, 'Please accept the privacy and terms checkbox.')
    minor = age_of(d) < 18; gm = guardian_email.strip().lower()[:230]
    if minor and (len(guardian_name.strip()) < 2 or '@' not in gm): raise HTTPException(400, "Guardian's name and email are required for students under 18.")
    with SessionLocal() as db:
        u = core.must_login(request, db); f = flag_for(db, u)
        f.dob, f.guardian_name, f.guardian_email = d, vt(guardian_name, 130), gm if minor else ''
        if minor:
            f.guardian_token, f.guardian_consent = S.new_token(), False
            S.send_email(gm, 'Consent request for %s on CareerSathi' % u.name.split()[0],
                         'Hello %s,\n\n%s has registered on CareerSathi (career guidance for students). Because they are under 18 we need your permission to store their profile, test results and enquiries.\n\nReview and respond: %s/guardian/consent/%s\n\nYou can withdraw consent at any time by contacting us.' % (vt(guardian_name, 130), u.name, S.site_url(), f.guardian_token))
        else: f.guardian_consent, f.consent_at = False, datetime.utcnow()
        db.commit()
        if not minor: award(db, u.id, 'consent', 'adult')
    core.notice(request, 'Saved.' + (" We emailed your guardian for approval. You can start the assessment now." if minor else '')); return core.redirect('/start')

@router.get('/guardian/consent/{token}')
def guardian_page(request: Request, token: str):
    with SessionLocal() as db:
        f = db.query(XUserFlag).filter_by(guardian_token=token[:60]).first()
        if not f: raise HTTPException(404, 'This consent link is invalid or has already been answered.')
        u = db.get(User, f.user_id); name = u.name
    return page(request, 'x_guardian.html', token=token, student=name)

@router.post('/guardian/consent/{token}')
def guardian_answer(request: Request, token: str, decision: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        f = db.query(XUserFlag).filter_by(guardian_token=token[:60]).first()
        if not f: raise HTTPException(404, 'This consent link is invalid or has already been answered.')
        u = db.get(User, f.user_id); ok = decision == 'approve'
        f.guardian_consent, f.guardian_token = ok, None; f.consent_at = datetime.utcnow() if ok else None; db.commit()
        if ok: award(db, u.id, 'consent', 'guardian')
        S.send_email(u.email, 'Guardian consent ' + ('approved' if ok else 'declined'), 'Your guardian has %s consent. %s' % ('approved' if ok else 'declined', 'You can now send enquiries and book sessions.' if ok else 'Some features stay locked until consent is given.'))
    return page(request, 'x_guardian_done.html', ok=ok)

# ---------- assessments ----------
def grade_kinds(db, u):
    g = user_grade(db, u)
    return g, ([k for k in AD.KINDS] if u.role == 'admin' else A.audience(g))

@router.get('/assessments')
def assessments(request: Request):
    with SessionLocal() as db:
        u = core.current_user(request, db); g, ks = grade_kinds(db, u) if u else ('', list(AD.KINDS))
        past = db.query(XAssessAttempt).filter_by(user_id=u.id, done=True).order_by(XAssessAttempt.created_at.desc()).limit(8).all() if u else []
        past = [(a.token, AD.KINDS[a.kind]['title'], a.created_at, json.loads(a.result or '{}').get('overall')) for a in past]
    return page(request, 'x_assessments.html', kinds=[(k, AD.KINDS[k]) for k in ks], grade=g, past=past)

@router.post('/assessments/{kind}/start')
def assessment_start(request: Request, kind: str, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if kind not in AD.KINDS: raise HTTPException(404, 'Unknown assessment')
    with SessionLocal() as db:
        u = core.must_login(request, db); g, ks = grade_kinds(db, u)
        if kind not in ks: raise HTTPException(403, 'This assessment is not meant for your class.')
        tok = secrets.token_urlsafe(10); ids = A.pick_questions(kind, tok)
        db.add(XAssessAttempt(token=tok, user_id=u.id, kind=kind, qids=','.join(ids))); db.commit()
    return core.redirect('/assessments/run/' + tok)

def _attempt(db, u, token, owner_only=True):
    a = db.query(XAssessAttempt).filter_by(token=token[:40]).first()
    if not a or (owner_only and a.user_id != u.id and u.role != 'admin'): raise HTTPException(404, 'Assessment not found')
    return a

def _run_page(request, a, token, prefill=None, incomplete='', status=200):
    qs = [AD.BANK[i] for i in a.qids.split(',')]; cfg = AD.KINDS[a.kind]
    resp = page(request, 'x_assess_run.html', token=token, qs=[(q['id'], q['sec'], q['q'], q['opts']) for q in qs], cfg=cfg,
                interest=AD.INTEREST if cfg['interest'] else [], SEC=AD.SECTIONS, prefill=prefill or {}, incomplete=incomplete)
    resp.status_code = status
    return resp

@router.get('/assessments/run/{token}')
def assessment_run(request: Request, token: str):
    with SessionLocal() as db:
        u = core.must_login(request, db); a = _attempt(db, u, token)
        if a.done: return core.redirect('/assessments/result/' + token)
        return _run_page(request, a, token)

@router.post('/assessments/run/{token}')
async def assessment_submit(request: Request, token: str):
    form = await request.form(); core.require_csrf(request, form.get('csrf_token'))
    with SessionLocal() as db:
        u = core.must_login(request, db); a = _attempt(db, u, token, owner_only=True)
        if a.done: return core.redirect('/assessments/result/' + token)
        ids = a.qids.split(',')
        answers = {}
        for i in ids:
            try:
                v = int(form.get('q_' + i, -1))
                if 0 <= v <= 3: answers[i] = v
            except ValueError: pass
        likert = []
        if AD.KINDS[a.kind]['interest']:
            for n in range(len(AD.INTEREST)):
                try:
                    v = int(form.get('i%d' % n, 0))
                    if 1 <= v <= 5: likert.append(v)
                except ValueError: pass
        missing = (len(ids) - len(answers)) + ((len(AD.INTEREST) - len(likert)) if AD.KINDS[a.kind]['interest'] else 0)
        if missing:   # no skipping: every question must be answered before a score or stream is shown
            # no skipping: show the test again with the answers already given, never a raw error
            return _run_page(request, a, token, prefill={k: str(v) for k, v in form.items() if k[:2] in ('q_',) or (k[:1] == 'i' and k[1:].isdigit())}, status=400,
                             incomplete='%d question%s still unanswered. Your score and stream are shown only after every question is answered. We took you to the first one you missed.' % (missing, '' if missing == 1 else 's'))
        sec, _ = A.grade(ids, answers); res = A.result_payload(a.kind, sec, likert); res['answers'] = answers
        a.sections, a.result, a.done = json.dumps(sec), json.dumps(res), True; db.commit()
        award(db, u.id, 'assess', token)
        f = flag_for(db, u)
        if f.step in ('consent', 'assessment'): f.step = 'enquiry'; db.commit()
    return core.redirect('/assessments/result/' + token)

@router.get('/assessments/result/{token}')
def assessment_result(request: Request, token: str):
    with SessionLocal() as db:
        u = core.must_login(request, db); a = _attempt(db, u, token)
        if not a.done: return core.redirect('/assessments/run/' + token)
        res = json.loads(a.result); kind = a.kind; ids = a.qids.split(',')
    _, review = A.grade(ids, {k: v for k, v in res.get('answers', {}).items()})
    allst = [(c, s, A.STREAM_NAMES[c], A.stream_advice(c, res.get('pcmb'))) for c, s in res.get('streams', [])]
    low = bool(allst) and res.get('overall', 100) < D3.THRESHOLD       # below 50%: Science is not recommended, it needs preparation
    streams = [x for x in allst if not (low and x[0] in D3.SCIENCE)]
    prep = [x for x in allst if low and x[0] in D3.SCIENCE]
    top = streams[0][0] if streams else ''
    if not low and res.get('pcmb') and top in ('PCM', 'PCB'): top = 'PCMB'
    weak = [(k, AD.SECTIONS[k], D3.SECTION_TIPS[k]) for k, v in res.get('pcts', {}).items() if v < D3.THRESHOLD and k in D3.SECTION_TIPS]
    return page(request, 'x_assess_result.html', top_name=A.STREAM_NAMES.get(top, top), res=res, cfg=AD.KINDS[kind], streams=streams, prep=prep, low=low, weak=weak, threshold=D3.THRESHOLD,
                review=review, SEC=AD.SECTIONS, token=token, top=top)

# ---------- enquiry form ----------
def college_names(db):
    names = [c[0] if isinstance(c, (list, tuple)) else (c.get('name') if isinstance(c, dict) else str(c)) for c in core.COLLEGE_DIRECTORY]
    names += [r.name for r in db.query(XCollege).all()]
    return sorted({n for n in names if n})

@router.get('/enquiry')
def enquiry_form(request: Request, stream: str = ''):
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['student', 'parent', 'admin'])
        need_assessment(request, db, u)
        j = db.query(StudentJourney).filter_by(user_id=u.id).first(); f = flag_for(db, u)
        pre = dict(name=u.name, email=u.email, phone=u.phone, grade=(j.grade if j and j.grade else u.grade), marks=(j.percentage if j else ''), exam=(j.exam if j else ''), exam_score=(j.exam_score if j else ''), stream=stream if stream in dict(D2.STREAM_OPTS) else '')
        names = college_names(db); ok = consent_ok(f)
        si = score_info(db, u) if u.role == 'student' else None
        pg = user_grade(db, u)
        lock = science_locked(si, pg, pre['grade'])
    streams = [x for x in D2.STREAM_OPTS if not (lock and x[0] in D3.SCIENCE)]
    sci = [x for x in D2.STREAM_OPTS if x[0] in D3.SCIENCE]
    return page(request, 'x_enquiry.html', pre=pre, grades=D2.GRADES, streams=streams, sci_streams=sci, exams=D2.EXAMS, purposes=D2.PURPOSES, colleges=names, consent=ok,
                si=si, lock=lock, pgrade=pg, threshold=D3.THRESHOLD)

@router.post('/enquiry')
async def enquiry_submit(request: Request):
    form = await request.form(); core.require_csrf(request, form.get('csrf_token'))
    g = (form.get('grade') or '').strip()
    if g not in dict(D2.GRADES): raise HTTPException(400, 'Select your class.')
    name, email = vt(form.get('name'), 130), vt(form.get('email'), 230).lower()
    if len(name) < 2 or '@' not in email: raise HTTPException(400, 'Name and a valid email are required.')
    marks = vt(form.get('marks'), 15)
    if marks:
        try:
            if not 0 <= float(marks) <= 100: raise ValueError
        except ValueError: raise HTTPException(400, 'Marks must be a percentage between 0 and 100.')
    stream = vt(form.get('stream'), 10)
    if stream and stream not in dict(D2.STREAM_OPTS) and stream != 'UNSURE': raise HTTPException(400, 'Invalid stream choice.')
    exam = vt(form.get('exam'), 60)
    if exam and exam not in D2.EXAMS: raise HTTPException(400, 'Invalid entrance exam choice.')
    purposes = [p for p in form.getlist('purposes') if p in dict(D2.PURPOSES)]
    if not purposes: raise HTTPException(400, 'Tell us what you need help with (select at least one).')
    cols = []
    for c in form.getlist('colleges'):
        c = vt(c, 120)
        if c and c.lower() not in [x.lower() for x in cols]: cols.append(c)
    if len(cols) > 5: raise HTTPException(400, 'You can choose at most 5 colleges.')
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['student', 'parent', 'admin']); need_consent(request, db, u); need_assessment(request, db, u, g)
        comment = vt(form.get('comment'), 1700); si = score_info(db, u) if u.role == 'student' else None
        if si and si['overall'] < D3.THRESHOLD and stream in D3.SCIENCE:
            if science_locked(si, user_grade(db, u), g):
                if form.get('prep_ack') != 'yes':
                    raise HTTPException(400, 'Your assessment score is %d%%, below %d%%. Science streams need serious preparation. Please tick the confirmation after reading the stream roadmap, or choose Commerce or Arts.' % (si['overall'], D3.THRESHOLD))
                comment += '\n[Auto-note: assessment score %d%%, below %d%%. Student chose %s and confirmed they will prepare. Mentor, please review the preparation plan.]' % (si['overall'], D3.THRESHOLD, stream)
            else:
                comment += '\n[Auto-note: latest assessment score %d%%; reported stream %s. Review preparation level.]' % (si['overall'], stream)
        e = XEnquiry(user_id=u.id, name=name, email=email, phone=vt(form.get('phone'), 30), grade=g, marks=marks, exam=exam, exam_score=vt(form.get('exam_score'), 60),
                     stream=stream, purposes=','.join(purposes), career_goal=vt(form.get('career_goal'), 200), colleges=json.dumps(cols), comment=comment)
        db.add(e); db.add(JourneyEnquiry(user_id=u.id, subject='Mentorship' if 'stream' not in purposes else 'Stream guidance', institute_type='', location='', budget='',
                                           note=vt('Class %s · %s · Colleges: %s · %s' % (g, stream or 'stream n/a', ', '.join(cols) or 'none', comment), 900)))
        db.commit(); eid = e.id
        f = flag_for(db, u); f.step = 'done'; db.commit(); award(db, u.id, 'enquiry', 'first')
    S.send_email(email, 'We received your CareerSathi enquiry', 'Hi %s,\n\nThank you. Your enquiry #%d is saved. Next, choose a mentor: %s/enquiry/%d/mentor' % (name.split()[0], eid, S.site_url(), eid))
    return core.redirect('/enquiry/%d/mentor' % eid)

def _enq(db, u, eid):
    e = db.get(XEnquiry, eid)
    if not e or (e.user_id != u.id and u.role != 'admin'): raise HTTPException(404, 'Enquiry not found')
    return e

@router.get('/enquiry/{eid}/mentor')
def enquiry_mentor(request: Request, eid: int):
    with SessionLocal() as db:
        u = core.must_login(request, db); e = _enq(db, u, eid); cols = json.loads(e.colleges or '[]')
        rows = db.query(User, MentorCredentials).outerjoin(MentorCredentials, MentorCredentials.user_id == User.id).filter(User.role == 'mentor', User.verified == True, User.active == True).all()
        mentors = [dict(id=m.id, name=m.name, expertise=m.expertise, bio=m.bio, city=m.city, stream=(c.stream if c else ''), university=(c.university if c else ''), exam=(c.exam if c else ''), degree=(c.degree if c else ''), company=(c.company if c else '')) for m, c in rows]
        prof = dict(interests=' '.join(cols + [e.stream, e.career_goal]), exam=e.exam, goal=e.career_goal)
        results = L.match_mentors(prof, mentors)[:6]
        view = dict(id=e.id, status=e.mentor_status, cols=cols, stream=e.stream)
    return page(request, 'x_enq_mentor.html', e=view, results=results)

@router.post('/enquiry/{eid}/mentor')
def enquiry_mentor_choose(request: Request, eid: int, mentor_id: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db); e = _enq(db, u, eid)
        if mentor_id == 'auto': e.mentor_status, e.mentor_id = 'auto', None
        else:
            m = db.get(User, int(mentor_id)) if mentor_id.isdigit() else None
            if not m or m.role != 'mentor' or not m.verified or not m.active: raise HTTPException(400, 'Choose a verified mentor.')
            e.mentor_id, e.mentor_status = m.id, 'requested'
            S.send_email(m.email, 'New mentee request on CareerSathi', 'A student (class %s, stream %s) asked for your guidance. Open your dashboard to respond.' % (e.grade, e.stream or 'n/a'))
        db.commit()
    core.notice(request, 'Mentor preference saved. Our team will confirm the allotment.'); return core.redirect('/enquiries')

@router.get('/enquiries')
def my_enquiries(request: Request):
    with SessionLocal() as db:
        u = core.must_login(request, db)
        rows = db.query(XEnquiry).filter_by(user_id=u.id).order_by(XEnquiry.created_at.desc()).all()
        out = []
        for e in rows:
            m = db.get(User, e.mentor_id) if e.mentor_id else None
            out.append(dict(id=e.id, at=e.created_at, grade=e.grade, stream=e.stream, cols=json.loads(e.colleges or '[]'), status=e.status, ms=e.mentor_status, mentor=m.name if m else '', purposes=e.purposes.split(',')))
    return page(request, 'x_enquiries.html', rows=out, PUR=dict(D2.PURPOSES))

@router.get('/admin/enquiries')
def admin_enquiries(request: Request):
    with SessionLocal() as db:
        core.must_login(request, db, role=['admin'])
        rows = db.query(XEnquiry).order_by(XEnquiry.created_at.desc()).limit(100).all(); out = []
        for e in rows:
            m = db.get(User, e.mentor_id) if e.mentor_id else None
            out.append(dict(id=e.id, name=e.name, email=e.email, grade=e.grade, marks=e.marks, exam='%s %s' % (e.exam, e.exam_score), stream=e.stream, cols=json.loads(e.colleges or '[]'), purposes=e.purposes, goal=e.career_goal, comment=e.comment, status=e.status, ms=e.mentor_status, mentor=m.name if m else ''))
        mentors = [(m.id, m.name) for m in db.query(User).filter_by(role='mentor', verified=True, active=True).all()]
    return page(request, 'x_admin_enq.html', rows=out, mentors=mentors, PUR=dict(D2.PURPOSES))

@router.post('/admin/enquiries/{eid}/allot')
def admin_allot(request: Request, eid: int, mentor_id: int = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        core.must_login(request, db, role=['admin']); e = db.get(XEnquiry, eid); m = db.get(User, mentor_id)
        if not e or not m or m.role != 'mentor' or not m.verified: raise HTTPException(400, 'Choose a verified mentor.')
        e.mentor_id, e.mentor_status, e.status = m.id, 'allotted', 'allotted'; db.commit()
        S.send_email(e.email, 'Your CareerSathi mentor is allotted', 'Mentor %s has been allotted for enquiry #%d. Open My enquiries to continue.' % (m.name, e.id))
        S.send_email(m.email, 'Mentee allotted on CareerSathi', 'You have been allotted a student (class %s). Details are in your dashboard.' % e.grade)
    core.notice(request, 'Mentor allotted and both parties emailed.'); return core.redirect('/admin/enquiries')


# ---------- v12.1: stream roadmap pages + /admin shortcut ----------
@router.get('/stream-roadmap/{code}')
def stream_roadmap(request: Request, code: str):
    code = code.upper()
    r = D3.STREAM_ROADMAPS.get(code)
    if not r: raise HTTPException(404, 'Roadmap not found')
    si = None
    with SessionLocal() as db:
        u = core.current_user(request, db)
        if u and u.role == 'student': si = score_info(db, u)
    keys = [(k, AD.SECTIONS[k], si['pcts'].get(k)) for k in D3.KEY_SECTIONS[code] if si and k in si['pcts']]
    weak = [(AD.SECTIONS[k], D3.SECTION_TIPS[k]) for k, _, v in keys if v is not None and v < D3.THRESHOLD]
    need_prep = code in D3.SCIENCE and si is not None and si['overall'] < D3.THRESHOLD
    return page(request, 'x_stream_roadmap.html', code=code, r=r, si=si, keys=keys, weak=weak, need_prep=need_prep, catchup=D3.CATCHUP, threshold=D3.THRESHOLD, others=list(D3.STREAM_ROADMAPS.items()))

@router.get('/admin')
def admin_entry(request: Request):
    """Admin reaches the console by typing /admin (no public link anywhere in the site)."""
    with SessionLocal() as db:
        u = core.current_user(request, db)
        if u and u.role == 'admin': return core.redirect('/admin/dashboard')
        if u: return core.redirect('/dashboard')
    core.notice(request, 'Please log in with your administrator account.')
    return core.redirect('/login')

# ---------- v12.2: guards for the legacy /journey forms (no bypass of the Class 8-10 assessment or the score rule) ----------
def _legacy_gate(request, subject=''):
    with SessionLocal() as db:
        u = core.current_user(request, db)
        if not u or u.role != 'student': return None
        f = flag_for(db, u)
        if user_grade(db, u) in GATED_GRADES:
            if not (student_progress(db, u, f)['assessment'] and consent_ok(f)):
                core.notice(request, 'Please complete your assessment first. You cannot move ahead without it.')
                raise HTTPException(303, headers={'Location': '/start'})
            si = score_info(db, u)
            if subject in ('Science PCM', 'Science PCB') and science_locked(si, user_grade(db, u)):
                raise HTTPException(400, 'Your assessment score is %d%%, below %d%%, so Science is not offered here. Use the main enquiry form (/enquiry) to see the preparation roadmap, or choose Commerce or Arts.' % (si['overall'], D3.THRESHOLD))
        return u.id

def journey_enquiry_guarded(request: Request, subject: str = Form(...), institute_type: str = Form(''), location: str = Form(''), budget: str = Form(''), note: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token); _legacy_gate(request, subject)
    return core.journey_enquiry(request, subject, institute_type, location, budget, note, csrf_token)

def journey_assessment_guarded(request: Request, interests: list[str] = Form([]), work_style: str = Form(...), favorite_subject: str = Form(...), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token); uid = _legacy_gate(request)
    resp = core.journey_assessment(request, interests, work_style, favorite_subject, csrf_token)
    if uid:   # a low score must not be contradicted by the old quiz: hide Science from its recommendation
        with SessionLocal() as db:
            u = db.get(User, uid); si = score_info(db, u)
            if science_locked(si, user_grade(db, u)):
                a = db.query(core.Assessment).filter_by(user_id=uid).order_by(core.Assessment.id.desc()).first()
                if a: a.recommendation = 'Possible streams to explore: Commerce, Arts / Humanities (Science needs a stronger assessment score first)'; db.commit()
    return resp
