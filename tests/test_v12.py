"""v12 Launch Pack tests: onboarding, class-wise assessments, enquiry + mentor allotment, security, payments, slots, AI, content."""
import re, json, hmac, hashlib
from datetime import datetime, timedelta, date
import pytest
from fastapi.testclient import TestClient
from conftest import make_user, login, token, core
from extras import assess as A, assess_data as AD, logic as L, services as S
from extras.models import XProfile
from extras.models2 import XUserFlag, XOutbox, XAssessAttempt, XEnquiry, XSlot, XPayment, XReset

def outbox(to, subject_part=''):
    with core.SessionLocal() as db:
        rows = db.query(XOutbox).filter(XOutbox.to_email == to).order_by(XOutbox.id.desc()).all()
        return [r for r in rows if subject_part in r.subject]

def uid(email):
    with core.SessionLocal() as db: return db.query(core.User).filter_by(email=email).first().id

def mentor(email='m1@t.in', university='IIT Delhi'):
    mid = make_user(email, 'mentor', 'Mentor One', verified=True)
    with core.SessionLocal() as db:
        u = db.get(core.User, mid); u.expertise = 'engineering JEE'
        if not db.query(core.MentorCredentials).filter_by(user_id=mid).first():
            db.add(core.MentorCredentials(user_id=mid, university=university, stream='PCM', exam='JEE Main'))
        db.commit()
    return mid

# ---------- pure logic ----------
def test_stream_logic_pcmb_pcm_arts():
    both = A.suggest_streams({'maths': 100, 'science': 100, 'reasoning': 100, 'english': 60, 'social': 50}, {'PCM': 100, 'PCB': 100, 'COM': 0, 'ART': 0})
    assert both[1] is True
    pcm = A.suggest_streams({'maths': 100, 'science': 45, 'reasoning': 90, 'english': 50, 'social': 40}, {'PCM': 100, 'PCB': 20, 'COM': 40, 'ART': 10})
    assert pcm[0][0][0] == 'PCM' and pcm[1] is False
    arts = A.suggest_streams({'maths': 20, 'science': 30, 'reasoning': 50, 'english': 100, 'social': 100, 'gk': 100}, {'PCM': 0, 'PCB': 0, 'COM': 20, 'ART': 100})
    assert arts[0][0][0] == 'ART'

def test_audience_by_class():
    assert A.audience('8') == A.audience('9') == ['foundation']
    assert A.audience('10') == ['class10']
    assert set(A.audience('12')) == {'subject', 'aptitude', 'gk'} and 'class10' not in A.audience('11')

def test_question_bank_integrity():
    for q in AD.BANK.values():
        assert len(q['opts']) == 4 and 0 <= q['a'] < 4 and len(set(q['opts'])) == 4 and q['why']
    for kind in AD.KINDS:
        ids = A.pick_questions(kind, 'seed')
        assert len(ids) == sum(AD.KINDS[kind]['mix'].values()) == len(set(ids))
    assert all(i.startswith('F') for i in A.pick_questions('foundation', 'x'))
    assert not any(i.startswith('F') for i in A.pick_questions('class10', 'x'))
    assert len(A.pick_questions('class10', 'x')) >= 30

def test_crisis_detection():
    assert L.is_crisis('I want to die') and L.is_crisis('mar jana chahta hoon') and not L.is_crisis('which stream is best after 10th')

# ---------- registration -> onboarding hub ----------
def register(email, grade='10', role='student'):
    c = TestClient(core.app, follow_redirects=False)
    r = c.post('/register', data=dict(name='New Student', email=email, password='password1234', role=role, grade=grade, csrf_token=token(c, '/register')))
    assert r.status_code == 303; return c

def test_new_student_is_sent_to_start_hub():
    c = register('new1@t.in', '10')
    r = c.get('/journey'); assert r.status_code == 303 and r.headers['location'] == '/start'
    html = c.get('/start').text
    assert 'Class 10 Stream Readiness Test' in html and 'Finish step 1 first' in html and '/assessments/class10/start' not in html   # locked until consent
    assert c.post('/start/consent', data=dict(dob='2010-03-04', guardian_name='Mom', guardian_email='mom@t.in', accept='yes', csrf_token=token(c, '/start'))).status_code == 303
    assert '/assessments/class10/start' in c.get('/start').text            # unlocked after age + guardian details
    assert outbox('new1@t.in', 'Verify')                                 # verification mail queued
    assert 'Verify your email' in c.get('/start').text

def test_guardian_consent_flow_for_minor():
    c = register('minor1@t.in', '9'); t = token(c, '/start')
    bad = c.post('/start/consent', data=dict(dob='2012-06-01', accept='yes', csrf_token=t)); assert bad.status_code == 400   # guardian missing
    assert c.post('/start/consent', data=dict(dob='2020-01-01', accept='yes', guardian_name='G', guardian_email='g@t.in', csrf_token=t)).status_code == 400  # too young
    ok = c.post('/start/consent', data=dict(dob='2012-06-01', guardian_name='Parent Name', guardian_email='g1@t.in', accept='yes', csrf_token=t)); assert ok.status_code == 303
    mail = outbox('g1@t.in', 'Consent request')[0]; gtoken = re.search(r'/guardian/consent/([\w-]+)', mail.body).group(1)
    g = TestClient(core.app, follow_redirects=False); assert g.get('/guardian/consent/' + gtoken).status_code == 200
    # until the guardian approves, enquiry is locked
    assert c.post('/enquiry', data={'csrf_token': token(c, '/start')}).status_code in (303, 400)
    assert g.post('/guardian/consent/' + gtoken, data=dict(decision='approve', csrf_token=token(g, '/guardian/consent/' + gtoken))).status_code == 200
    with core.SessionLocal() as db: assert db.query(XUserFlag).filter_by(user_id=uid('minor1@t.in')).first().guardian_consent is True
    assert g.get('/guardian/consent/' + gtoken).status_code == 404            # single use

def test_adult_consent_and_enquiry_locked_without_consent():
    make_user('lock1@t.in', onboarded=False, grade='12'); c = login('lock1@t.in')
    r = c.get('/enquiry'); assert r.status_code == 200
    r = c.post('/enquiry', data=dict(grade='12', name='A B', email='a@b.in', purposes=['stream'], csrf_token=token(c, '/enquiry')))
    assert r.status_code == 303 and r.headers['location'] == '/start'
    assert c.post('/start/consent', data=dict(dob='2001-02-03', accept='yes', csrf_token=token(c, '/start'))).status_code == 303
    assert c.post('/enquiry', data=dict(grade='12', name='A B', email='a@b.in', purposes=['stream'], csrf_token=token(c, '/enquiry'))).status_code == 303

# ---------- class-wise assessments ----------
def take(c, kind, answer_right=True):
    r = c.post('/assessments/%s/start' % kind, data={'csrf_token': token(c, '/assessments')}); assert r.status_code == 303
    tok = r.headers['location'].rsplit('/', 1)[1]
    with core.SessionLocal() as db: ids = db.query(XAssessAttempt).filter_by(token=tok).first().qids.split(',')
    form = {'q_' + i: (AD.BANK[i]['a'] if answer_right else (AD.BANK[i]['a'] + 1) % 4) for i in ids}
    form.update({'i%d' % n: 5 for n in range(len(AD.INTEREST))}); form['csrf_token'] = token(c, '/assessments/run/' + tok)
    assert c.get('/assessments/run/' + tok).status_code == 200
    assert c.post('/assessments/run/' + tok, data=form).status_code == 303
    return tok, ids

def test_class10_assessment_is_hard_mcq_with_reasoning_and_gk():
    make_user('c10@t.in', grade='10'); c = login('c10@t.in')
    html = c.get('/assessments').text; assert 'Class 10 Stream Readiness Test' in html and 'Stream Finder' not in html
    tok, ids = take(c, 'class10')
    secs = {AD.BANK[i]['sec'] for i in ids}; assert {'reasoning', 'gk', 'maths', 'science'} <= secs and len(ids) == 30
    res = c.get('/assessments/result/' + tok); assert res.status_code == 200 and 'Excellent' in res.text
    tok2, _ = take(c, 'class10', answer_right=False); assert 'Needs practice' in c.get('/assessments/result/' + tok2).text

def test_foundation_for_class_8_and_blocked_kinds():
    make_user('c8@t.in', grade='8'); c = login('c8@t.in')
    tok, ids = take(c, 'foundation'); assert all(i.startswith('F') for i in ids)
    assert c.post('/assessments/class10/start', data={'csrf_token': token(c, '/assessments')}).status_code == 403
    make_user('c12@t.in', grade='12'); d = login('c12@t.in'); page = d.get('/assessments').text
    for k in ('Subject Readiness Check', 'Aptitude &amp; Reasoning', 'General Knowledge Booster'): assert k in page
    assert d.post('/assessments/class10/start', data={'csrf_token': token(d, '/assessments')}).status_code == 403
    take(d, 'aptitude')

def test_other_students_cannot_open_my_result():
    make_user('own@t.in', grade='10'); make_user('oth@t.in', grade='10')
    tok, _ = take(login('own@t.in'), 'class10')
    assert login('oth@t.in').get('/assessments/result/' + tok).status_code == 404

# ---------- enquiry form + mentor allotment ----------
def enq_data(**kw):
    d = dict(grade='12', name='Asha Verma', email='asha@t.in', phone='9999999999', marks='88.5', exam='JEE Main', exam_score='96 percentile', stream='PCMB',
             purposes=['stream', 'roadmap', 'skills'], career_goal='Biotech engineer', colleges=['IIT Delhi', 'NIT Trichy', 'BITS Pilani', 'DTU', 'IIIT Hyderabad'], comment='Confused between PCM and PCB')
    d.update(kw); return d

def test_enquiry_validation():
    make_user('e1@t.in', grade='12'); c = login('e1@t.in'); assert 'Colleges (up to 5)' in c.get('/enquiry').text
    t = lambda: token(c, '/enquiry')
    assert c.post('/enquiry', data=enq_data(colleges=['A', 'B', 'C', 'D', 'E', 'F'], csrf_token=t())).status_code == 400
    assert c.post('/enquiry', data=enq_data(purposes=[], csrf_token=t())).status_code == 400
    assert c.post('/enquiry', data=enq_data(stream='XYZ', csrf_token=t())).status_code == 400
    assert c.post('/enquiry', data=enq_data(marks='120', csrf_token=t())).status_code == 400
    assert c.post('/enquiry', data=enq_data(exam='Fake Exam', csrf_token=t())).status_code == 400
    assert c.post('/enquiry', data=enq_data(grade='99', csrf_token=t())).status_code == 400
    assert c.post('/enquiry', data=enq_data()).status_code == 403          # CSRF

@pytest.mark.parametrize('grade,stream', [('8', 'PCM'), ('9', 'ART'), ('10', 'COM'), ('11', 'PCB'), ('12', 'PCMB'), ('12', 'ART'), ('12', 'COM'), ('college', 'PCM')])
def test_enquiry_all_classes_and_streams(grade, stream):
    em = ('eq_%s_%s@t.in' % (grade, stream)).lower(); make_user(em, grade=grade); c = login(em)
    r = c.post('/enquiry', data=enq_data(grade=grade, stream=stream, email=em, csrf_token=token(c, '/enquiry')))
    assert r.status_code == 303 and r.headers['location'].endswith('/mentor')
    with core.SessionLocal() as db:
        e = db.query(XEnquiry).filter_by(user_id=uid(em)).first()
        assert e.grade == grade and e.stream == stream and len(json.loads(e.colleges)) == 5

def test_mentor_choice_and_admin_allotment():
    mid = mentor(); make_user('adm2@t.in', 'admin', 'Admin'); make_user('e2@t.in', grade='12'); c = login('e2@t.in')
    r = c.post('/enquiry', data=enq_data(email='e2@t.in', csrf_token=token(c, '/enquiry'))); loc = r.headers['location']; eid = int(loc.split('/')[2])
    assert 'Mentor One' in c.get(loc).text                                  # suggested after colleges chosen (IIT Delhi match)
    assert c.post(loc, data=dict(mentor_id=str(mid), csrf_token=token(c, loc))).status_code == 303
    assert outbox('m1@t.in', 'New mentee request')
    assert c.post(loc, data=dict(mentor_id='999999', csrf_token=token(c, loc))).status_code == 400
    assert 'Mentor One' in c.get('/enquiries').text
    other = login('e1@t.in'); assert other.get(loc).status_code == 404         # not someone else's enquiry
    a = login('adm2@t.in'); assert a.get('/admin/enquiries').status_code == 200
    assert a.post('/admin/enquiries/%d/allot' % eid, data=dict(mentor_id=mid, csrf_token=token(a, '/admin/enquiries'))).status_code == 303
    with core.SessionLocal() as db: assert db.get(XEnquiry, eid).mentor_status == 'allotted'
    assert outbox('e2@t.in', 'mentor is allotted')
    assert c.get('/admin/enquiries').status_code == 403

# ---------- email verification, reset, lockout ----------
def test_verify_email_and_password_reset():
    make_user('v1@t.in', onboarded=False); c = login('v1@t.in'); c.get('/start')
    with core.SessionLocal() as db: tk = db.query(XUserFlag).filter_by(user_id=uid('v1@t.in')).first().verify_token
    assert c.get('/verify/' + tk).status_code in (200, 303)
    with core.SessionLocal() as db: assert db.query(XUserFlag).filter_by(user_id=uid('v1@t.in')).first().email_verified
    a = TestClient(core.app, follow_redirects=False)
    r1 = a.post('/forgot-password', data=dict(email='v1@t.in', csrf_token=token(a, '/forgot-password')))
    r2 = a.post('/forgot-password', data=dict(email='nobody@t.in', csrf_token=token(a, '/forgot-password')))
    assert r1.status_code == r2.status_code                                  # no account enumeration
    rt = re.search(r'/reset-password/([\w-]+)', outbox('v1@t.in', 'Reset')[0].body).group(1)
    assert a.get('/reset-password/' + rt).status_code == 200
    assert a.post('/reset-password/' + rt, data=dict(password='short', confirm='short', csrf_token=token(a, '/reset-password/' + rt))).status_code == 400
    assert a.post('/reset-password/' + rt, data=dict(password='brandNewPass99', confirm='brandNewPass99', csrf_token=token(a, '/reset-password/' + rt))).status_code == 303
    assert a.get('/reset-password/' + rt).status_code in (400, 404, 410)    # single use
    b = TestClient(core.app, follow_redirects=False)
    assert b.post('/login', data=dict(email='v1@t.in', password='password1234', csrf_token=token(b))).status_code == 401
    assert b.post('/login', data=dict(email='v1@t.in', password='brandNewPass99', csrf_token=token(b))).status_code == 303

def test_login_lockout_after_failures():
    make_user('lk@t.in'); c = TestClient(core.app, follow_redirects=False); t = token(c)
    for _ in range(5): assert c.post('/login', data=dict(email='lk@t.in', password='wrongwrong', csrf_token=t)).status_code == 401
    assert c.post('/login', data=dict(email='lk@t.in', password='password1234', csrf_token=t)).status_code == 429

# ---------- payments ----------
def test_razorpay_signature_and_plan_activation(monkeypatch):
    monkeypatch.setenv('RAZORPAY_KEY_ID', 'rzp_test_x'); monkeypatch.setenv('RAZORPAY_KEY_SECRET', 'secret123'); monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET', 'whsec')
    make_user('pay1@t.in'); c = login('pay1@t.in')
    monkeypatch.setattr(S, 'razorpay_create_order', lambda amt, rcpt, notes=None: {'id': 'order_ABC'})
    page = c.get('/pay/plan/plus'); assert page.status_code == 200 and 'order_ABC' in page.text and '99' in page.text
    sig = lambda o, p: hmac.new(b'secret123', ('%s|%s' % (o, p)).encode(), hashlib.sha256).hexdigest()
    H = {'X-CSRF': token(c, '/pricing')}
    bad = c.post('/pay/verify', json=dict(order_id='order_ABC', payment_id='pay_1', signature='forged'), headers=H); assert bad.status_code == 400
    assert c.post('/pay/verify', json=dict(order_id='order_ABC', payment_id='pay_1', signature=sig('order_ABC', 'pay_1'))).status_code == 403   # no CSRF header
    ok = c.post('/pay/verify', json=dict(order_id='order_ABC', payment_id='pay_1', signature=sig('order_ABC', 'pay_1')), headers=H); assert ok.status_code == 200 and ok.json()['ok']
    with core.SessionLocal() as db:
        assert db.query(XProfile).filter_by(user_id=uid('pay1@t.in')).first().plan == 'plus'
        assert db.query(XPayment).filter_by(order_id='order_ABC').first().status == 'paid'
    # webhook path
    make_user('pay2@t.in'); c2 = login('pay2@t.in'); monkeypatch.setattr(S, 'razorpay_create_order', lambda *a, **k: {'id': 'order_WH'}); c2.get('/pay/plan/pro')
    body = json.dumps({'event': 'payment.captured', 'payload': {'payment': {'entity': {'id': 'pay_9', 'order_id': 'order_WH'}}}}).encode()
    w = TestClient(core.app)
    assert w.post('/pay/webhook', content=body, headers={'x-razorpay-signature': 'nope'}).status_code == 400
    good = hmac.new(b'whsec', body, hashlib.sha256).hexdigest()
    assert w.post('/pay/webhook', content=body, headers={'x-razorpay-signature': good}).status_code == 200
    with core.SessionLocal() as db: assert db.query(XProfile).filter_by(user_id=uid('pay2@t.in')).first().plan == 'pro'

def test_pay_page_without_keys_explains_manual_flow():
    make_user('pay3@t.in'); c = login('pay3@t.in'); r = c.get('/pay/plan/plus'); assert r.status_code == 200 and 'order_' not in r.text
    assert c.get('/pay/plan/gold').status_code == 404

# ---------- mentor slots, video link, notifications ----------
def test_slot_booking_confirmation_sends_video_link():
    mid = mentor('m2@t.in', 'DU'); m = login('m2@t.in'); when = (datetime.utcnow() + timedelta(days=2)).replace(microsecond=0, second=0).isoformat(timespec='minutes')
    assert m.post('/my/slots/add', data=dict(starts_at=when, minutes=30, csrf_token=token(m, '/my/slots'))).status_code == 303
    assert m.post('/my/slots/add', data=dict(starts_at=when, minutes=30, csrf_token=token(m, '/my/slots'))).status_code == 400    # duplicate
    assert m.post('/my/slots/add', data=dict(starts_at='2001-01-01T10:00', minutes=30, csrf_token=token(m, '/my/slots'))).status_code == 400  # past
    make_user('stu_s@t.in', grade='11'); s = login('stu_s@t.in'); assert s.get('/mentors/%d/slots' % mid).status_code == 200
    with core.SessionLocal() as db: sid = db.query(XSlot).filter_by(mentor_id=mid).first().id
    assert s.post('/slots/%d/book' % sid, data=dict(note='Doubt about JEE', csrf_token=token(s, '/my-sessions'))).status_code == 303
    assert s.post('/slots/%d/book' % sid, data=dict(note='again', csrf_token=token(s, '/my-sessions'))).status_code == 409           # no double booking
    assert m.post('/my/slots/%d/delete' % sid, data=dict(csrf_token=token(m, '/my/slots'))).status_code in (400, 409)                  # cannot delete a booked slot
    with core.SessionLocal() as db: bid = db.query(core.Booking).filter_by(mentor_id=mid, user_id=uid('stu_s@t.in')).first().id
    assert outbox('stu_s@t.in', 'Booking request received') and outbox('m2@t.in', 'New session request')
    assert m.post('/booking/%d/confirm' % bid, data=dict(csrf_token=token(m, '/my-sessions'))).status_code == 303
    mail = outbox('stu_s@t.in', 'Booking confirmed')[0]; assert 'https://' in mail.body and 'Video link' in mail.body
    assert 'https://' in s.get('/my-sessions').text

# ---------- AI counsellor ----------
def test_assistant_faq_ai_and_crisis(monkeypatch):
    c = TestClient(core.app); H = {'X-CSRF': token(c, '/career-quiz')}
    assert c.post('/assistant/ask', json={'q': 'cost'}).status_code == 403
    assert '₹99' in c.post('/assistant/ask', json={'q': 'how much does it cost per year'}, headers=H).json()['answer']
    assert c.post('/assistant/ask', json={'q': 'zzz qqq xxx'}, headers=H).json()['found'] is False                   # no key: honest fallback
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-test'); monkeypatch.setattr(S, 'ai_answer', lambda q, ctx='': 'Aap PCM lekar engineering dekh sakte ho.')
    r = c.post('/assistant/ask', json={'q': 'mujhe maths pasand hai kya karun'}, headers=H).json(); assert r['ai'] is True and 'PCM' in r['answer']
    monkeypatch.setattr(S, 'ai_answer', lambda *a, **k: (_ for _ in ()).throw(AssertionError('AI must not answer crisis messages')))
    cr = c.post('/assistant/ask', json={'q': 'I want to die'}, headers=H).json(); assert cr['crisis'] and '14416' in cr['answer']

# ---------- content, SEO, PWA, language ----------
def test_blog_sitemap_pwa_language_and_scholarships():
    c = TestClient(core.app)
    blog = c.get('/blog'); assert blog.status_code == 200
    slug = re.search(r'href="/blog/([\w-]+)"', blog.text).group(1); assert c.get('/blog/' + slug).status_code == 200 and c.get('/blog/nope').status_code == 404
    sm = c.get('/sitemap.xml'); assert '<urlset' in sm.text and '/roadmaps/doctor' in sm.text and '/blog/' + slug in sm.text
    assert 'Sitemap' in c.get('/robots.txt').text and '/admin' in c.get('/robots.txt').text
    sw = c.get('/sw.js'); assert sw.status_code == 200 and 'javascript' in sw.headers['content-type']
    assert c.get('/offline').status_code == 200 and 'manifest' in c.get('/').text
    assert c.get('/scholarships?category=SC').status_code == 200 and 'official' in c.get('/scholarships').text.lower()
    hi = TestClient(core.app, follow_redirects=False); assert hi.get('/lang/hi').status_code == 303
    from extras.data2 import HI
    h = TestClient(core.app, cookies={'lang': 'hi'}).get('/').text
    assert any(v in h for v in HI.values())
    assert c.get('/health/deep').status_code in (200, 503)

def test_internship_board_lifecycle_and_import():
    make_user('adm3@t.in', 'admin', 'Admin'); a = login('adm3@t.in'); co = TestClient(core.app, follow_redirects=False)
    assert co.post('/internships/post', data=dict(company='Acme Pvt Ltd', contact_name='HR', contact_email='hr@acme.in', title='Web intern', description='Work with our team on a real website for ten weeks, mentored by engineers.', csrf_token=token(co, '/internships/post'))).status_code == 303
    assert 'Web intern' not in co.get('/internships').text                       # hidden until approved
    with core.SessionLocal() as db:
        from extras.models2 import XInternship; iid = db.query(XInternship).filter_by(title='Web intern').first().id
    assert a.post('/admin/internships/%d/approve' % iid, data=dict(csrf_token=token(a, '/admin/internships'))).status_code == 303
    assert 'Web intern' in co.get('/internships').text
    make_user('stu_i@t.in', grade='12'); s = login('stu_i@t.in')
    assert s.post('/internships/%d/apply' % iid, data=dict(message='I love web', csrf_token=token(s, '/internships/%d' % iid))).status_code == 303
    csvdata = b'kind,title,subtitle,description,category,location,starts_at,price\nseminar,Test Seminar,,Desc,Career,Patna,2027-01-10T10:00,0\nbadkind,x,,,,,,\n'
    r = a.post('/admin/import', data=dict(kind='items', csrf_token=token(a, '/admin/import')), files={'file': ('i.csv', csvdata, 'text/csv')})
    assert r.status_code == 200 and 'Row 3' in r.text
    with core.SessionLocal() as db: assert db.query(core.Item).filter_by(title='Test Seminar').count() == 1
    assert s.get('/admin/import').status_code == 403

def test_streak_checkin_once_per_day_and_audit_log():
    make_user('streak@t.in'); c = login('streak@t.in')
    for _ in range(2): c.post('/rewards/checkin', data=dict(csrf_token=token(c, '/rewards')))
    from extras.models import XPoint
    with core.SessionLocal() as db: assert db.query(XPoint).filter_by(user_id=uid('streak@t.in'), action='checkin').count() == 1
    make_user('adm4@t.in', 'admin', 'Admin'); a = login('adm4@t.in')
    for p in ('/admin/audit', '/admin/analytics', '/admin/outbox', '/admin/hub'): assert a.get(p).status_code == 200, p


# ---------- enquiry gate: Class 8-10 must finish the assessment first ----------
@pytest.mark.parametrize('grade', ['8', '9', '10'])
def test_enquiry_blocked_until_assessment_for_class_8_to_10(grade):
    em = 'gate%s@t.in' % grade; make_user(em, grade=grade, assessed=False); c = login(em)
    r = c.get('/enquiry'); assert r.status_code == 303 and r.headers['location'] == '/start'
    r = c.post('/enquiry', data=enq_data(grade=grade, email=em, csrf_token=token(c, '/start')))
    assert r.status_code == 303 and r.headers['location'] == '/start'
    with core.SessionLocal() as db: assert db.query(XEnquiry).filter_by(user_id=uid(em)).count() == 0

def test_class_11_12_can_enquire_without_assessment():
    make_user('free12@t.in', grade='12', assessed=False); c = login('free12@t.in')
    assert c.get('/enquiry').status_code == 200


# ---------- v12.1/12.2: score-based streams, no skipping, /admin shortcut, contact ----------
def sel(html):                      # the visible <select id="st"> options only (not the hidden <template>)
    return html.split('<select id="st"')[1].split('</select>')[0]

def test_assessment_cannot_be_submitted_incomplete():
    make_user('inc@t.in', grade='10', assessed=False); c = login('inc@t.in')
    r = c.post('/assessments/class10/start', data={'csrf_token': token(c, '/assessments')}); tok = r.headers['location'].rsplit('/', 1)[1]
    with core.SessionLocal() as db: ids = db.query(XAssessAttempt).filter_by(token=tok).first().qids.split(',')
    form = {'q_' + i: AD.BANK[i]['a'] for i in ids[:-1]}                         # one question left blank
    form.update({'i%d' % n: 5 for n in range(len(AD.INTEREST))}); form['csrf_token'] = token(c, '/assessments/run/' + tok)
    r = c.post('/assessments/run/' + tok, data=form); assert r.status_code == 400
    assert c.get('/assessments/result/' + tok).status_code in (302, 303, 400, 403, 404)   # no score without finishing
    assert c.get('/enquiry').headers['location'] == '/start'

def test_low_score_hides_science_and_needs_acknowledgement():
    make_user('low@t.in', grade='10', assessed=False); c = login('low@t.in')
    tok, _ = take(c, 'class10', answer_right=False)
    res = c.get('/assessments/result/' + tok).text
    assert 'Commerce' in res and 'Arts' in res and 'roadmap' in res.lower()
    html = c.get('/enquiry').text; s = sel(html)
    assert 'value="COM"' in s and 'value="ART"' in s and 'value="PCM"' not in s and 'value="PCB"' not in s and 'value="PCMB"' not in s
    assert 'I still want a Science stream' in html and 'Preparation needed' in html
    t = lambda: token(c, '/enquiry')
    r = c.post('/enquiry', data=enq_data(grade='10', email='low@t.in', stream='PCM', csrf_token=t())); assert r.status_code == 400 and 'preparation' in r.text.lower()
    r = c.post('/enquiry', data=enq_data(grade='10', email='low@t.in', stream='PCM', prep_ack='yes', csrf_token=t())); assert r.status_code == 303
    with core.SessionLocal() as db: e = db.query(XEnquiry).filter_by(user_id=uid('low@t.in')).first()
    assert e.stream == 'PCM' and 'Auto-note' in e.comment
    assert c.post('/enquiry', data=enq_data(grade='10', email='low@t.in', stream='COM', csrf_token=t())).status_code == 303

def test_high_score_shows_all_streams():
    make_user('high@t.in', grade='9', assessed=False); c = login('high@t.in')
    take(c, 'foundation', answer_right=True)
    s = sel(c.get('/enquiry').text)
    assert all('value="%s"' % v in s for v in ('PCM', 'PCB', 'PCMB', 'COM', 'ART'))
    assert c.post('/enquiry', data=enq_data(grade='9', email='high@t.in', stream='PCM', csrf_token=token(c, '/enquiry'))).status_code == 303

def test_class_12_low_score_is_advisory_not_blocked():
    make_user('l12@t.in', grade='12', assessed=False); c = login('l12@t.in')
    take(c, 'subject', answer_right=False)
    assert c.post('/enquiry', data=enq_data(grade='12', email='l12@t.in', stream='PCM', csrf_token=token(c, '/enquiry'))).status_code == 303   # reports the stream studied

def test_stream_roadmaps_for_every_stream():
    c = TestClient(core.app, follow_redirects=False)
    for code in ('PCM', 'PCB', 'PCMB', 'COM', 'ART'):
        r = c.get('/stream-roadmap/' + code); assert r.status_code == 200 and 'Class 11' in r.text, code
    assert c.get('/stream-roadmap/XYZ').status_code == 404

@pytest.mark.parametrize('grade', ['8', '9', '10'])
def test_classic_bypass_and_legacy_forms_are_closed(grade):
    em = 'cl%s@t.in' % grade; make_user(em, grade=grade, assessed=False); c = login(em)
    assert c.get('/journey?classic=1').headers['location'] == '/start'
    assert c.get('/dashboard').headers['location'] == '/start'
    r = c.post('/journey/enquiry', data=dict(subject='Commerce', csrf_token=token(c, '/start'))); assert r.status_code == 303 and r.headers['location'] == '/start'
    r = c.post('/journey/assessment', data=dict(work_style='practical', favorite_subject='x', interests=['math'], csrf_token=token(c, '/start'))); assert r.status_code == 303 and r.headers['location'] == '/start'

def test_legacy_enquiry_respects_low_score():
    make_user('leg@t.in', grade='10', assessed=False); c = login('leg@t.in'); take(c, 'class10', answer_right=False)
    t = lambda: token(c, '/start')
    assert c.post('/journey/enquiry', data=dict(subject='Science PCM', csrf_token=t())).status_code == 400
    assert c.post('/journey/assessment', data=dict(work_style='analytical', favorite_subject='Maths', interests=['math', 'coding'], csrf_token=t())).status_code == 303
    with core.SessionLocal() as db: rec = db.query(core.Assessment).filter_by(user_id=uid('leg@t.in')).first().recommendation
    assert 'Commerce' in rec and 'Science (PCM)' not in rec.split('(Science needs')[0]        # old quiz cannot recommend Science after a low score
    assert c.post('/journey/enquiry', data=dict(subject='Commerce', csrf_token=t())).status_code == 303

def test_admin_has_no_public_link_but_slash_admin_works():
    anon = TestClient(core.app, follow_redirects=False)
    for p in ('/', '/login', '/contact', '/about', '/pricing'):
        html = anon.get(p).text; assert 'href="/admin' not in html and 'Admin login' not in html, p
    r = anon.get('/admin'); assert r.status_code == 303 and r.headers['location'] == '/login'
    make_user('adm9@t.in', 'admin', 'Admin'); a = login('adm9@t.in')
    assert a.get('/admin').headers['location'] == '/admin/dashboard' and 'href="/admin' not in a.get('/').text
    make_user('st9@t.in'); s = login('st9@t.in'); assert s.get('/admin').headers['location'] == '/dashboard'
    assert s.get('/admin/dashboard').status_code == 403

def test_contact_shows_official_email_and_instagram():
    anon = TestClient(core.app, follow_redirects=False)
    for p in ('/contact', '/'):
        h = anon.get(p).text
        assert 'officialcareersathi@gmail.com' in h and 'instagram.com/officialcareersathi' in h, p

def test_navbar_keeps_every_option():
    h = TestClient(core.app).get('/').text
    for label in ('Home', 'Seminars', 'Mentors', 'College tours', 'Courses', 'Career Compass', 'Roadmaps', 'Plans', 'About', 'Log in', 'Get started'):
        assert label in h, label
    make_user('nav1@t.in', grade='11'); c = login('nav1@t.in'); h = c.get('/').text
    for label in ('Dashboard', 'Start here', 'Rewards', 'Log out'): assert label in h, label


# ---------- v12.3: stale-cache-proof navbar, friendly errors, assessment UX ----------
def test_assets_are_versioned_and_navbar_css_is_inline():
    h = TestClient(core.app).get('/').text
    for f in ('style.css', 'extras.css', 'main.js', 'extras.js'): assert re.search(r'%s\?v=\w+' % re.escape(f), h), f
    assert '<style id="nav-css">' in h and 'a.only-mobile{display:none}' in h        # mobile-only items never show on desktop, even with stale CSS
    assert 'skip-link{position:absolute' in h

def test_incomplete_assessment_shows_page_not_json_and_keeps_answers():
    make_user('uxa@t.in', grade='10', assessed=False); c = login('uxa@t.in')
    r = c.post('/assessments/class10/start', data={'csrf_token': token(c, '/assessments')}); tok = r.headers['location'].rsplit('/', 1)[1]
    with core.SessionLocal() as db: ids = db.query(XAssessAttempt).filter_by(token=tok).first().qids.split(',')
    form = {'q_' + ids[0]: AD.BANK[ids[0]]['a'], 'csrf_token': token(c, '/assessments/run/' + tok)}
    r = c.post('/assessments/run/' + tok, data=form, headers={'Accept': 'text/html'})
    assert r.status_code == 400 and r.headers['content-type'].startswith('text/html') and not r.text.lstrip().startswith('{')
    assert 'still unanswered' in r.text and 'id="awNext"' in r.text and 'disabled' in r.text and r.text.count(' checked') >= 1   # answer kept
    # API clients still get JSON
    r = c.post('/assessments/run/' + tok, data=form); assert r.status_code == 400
    assert c.get('/assessments/result/' + tok, headers={'Accept': 'text/html'}).status_code in (302, 303, 400, 403, 404)

def test_browsers_get_a_friendly_error_page_and_api_gets_json():
    make_user('err1@t.in', grade='11'); c = login('err1@t.in')
    r = c.post('/pricing/request', data={'plan': 'bogus', 'csrf_token': token(c, '/pricing')}, headers={'Accept': 'text/html'})
    assert r.status_code == 400 and 'text/html' in r.headers['content-type'] and '"detail"' not in r.text and 'Please check and try again' in r.text
    r = c.post('/pricing/request', data={'plan': 'bogus', 'csrf_token': token(c, '/pricing')}); assert r.json()['detail']

def test_result_page_names_the_stream_in_full():
    make_user('nm@t.in', grade='10', assessed=False); c = login('nm@t.in'); tok, _ = take(c, 'class10', answer_right=False)
    h = c.get('/assessments/result/' + tok).text; assert 'Suggested stream: Commerce' in h or 'Suggested stream: Arts' in h
