import re, pytest
from conftest import make_user, login, token, core
from extras import logic as L, data as D
from extras.models import XPoint, XProfile

ALL4 = [4] * 24
# ---------- pure logic ----------
def test_quiz_scoring_and_top_type():
    ans = [1] * 24
    for i, (t, _) in enumerate(D.QUESTIONS):
        if t == 'A': ans[i] = 5
    s = L.score_quiz(ans)
    assert s['A'] == 20 and s['R'] == 4 and L.top_types(s)[0] == 'A'
    assert L.rank_careers(s)[0][0]['slug'] in ('designer', 'journalist-media')

def test_quiz_rejects_bad_input():
    with pytest.raises(ValueError): L.score_quiz([3] * 23)
    with pytest.raises(ValueError): L.score_quiz([9] * 24)

def test_badges_and_names():
    assert L.badge_for(0)[0][1] == 'Explorer' and L.badge_for(160)[0][1] == 'Planner' and L.badge_for(10**6)[1] is None
    assert L.public_name('aarav kumar singh') == 'Aarav S.' and L.public_name('Meera') == 'Meera'

def test_faq_and_matching():
    assert 'NEET' in L.faq_answer('how can i become a doctor after neet')
    assert L.faq_answer('zzzz qqqq') is None
    ms = [dict(id=1, name='A', expertise='coding software', exam='JEE Main', city='Bhopal', stream='CSE'), dict(id=2, name='B', expertise='law', exam='', city='Delhi')]
    res = L.match_mentors(dict(interests='coding', exam='JEE Main', city='Bhopal'), ms)
    assert res[0][0]['id'] == 1 and res[0][1] == 60 and res[1][1] == 0

# ---------- public pages ----------
@pytest.mark.parametrize('p', ['/career-quiz', '/roadmaps', '/roadmaps/doctor', '/match', '/leaderboard', '/assistant', '/faq', '/pricing', '/resume-builder', '/study-abroad', '/partners', '/', '/join/NOPE'])
def test_public_pages(anon, p):
    assert anon.get(p).status_code in (200, 303)

def test_unknown_roadmap_404(anon):
    assert anon.get('/roadmaps/nope').status_code == 404

def test_new_nav_present(anon):
    h = anon.get('/').text
    assert '/career-quiz' in h and 'extras.css' in h and 'xaBtn' in h

# ---------- quiz flow ----------
def quiz_post(c, answers=ALL4, csrf=True):
    data = {'q%d' % i: v for i, v in enumerate(answers)}
    if csrf: data['csrf_token'] = token(c, '/career-quiz')
    return c.post('/career-quiz', data=data)

def test_quiz_requires_csrf(anon):
    anon.get('/career-quiz')
    assert quiz_post(anon, csrf=False).status_code == 403

def test_quiz_anonymous_flow_and_report_locked(anon):
    r = quiz_post(anon); assert r.status_code == 303
    loc = r.headers['location']; assert loc.startswith('/career-quiz/result/')
    assert 'Top career matches' in anon.get(loc).text
    rep = anon.get('/report/' + loc.rsplit('/', 1)[1]).text
    assert 'Unlock the full report' in rep and '30-60-90' not in rep.split('Unlock')[0]

def test_quiz_incomplete_rejected(anon):
    anon.get('/career-quiz'); data = {'q0': 3, 'csrf_token': token(anon, '/career-quiz')}
    assert anon.post('/career-quiz', data=data).status_code == 400

def test_logged_in_points_idempotent_and_leaderboard():
    make_user('s1@t.in', name='Riya Sharma'); c = login('s1@t.in')
    quiz_post(c)
    with core.SessionLocal() as db:
        uid = db.query(core.User).filter_by(email='s1@t.in').first().id
        assert db.query(XPoint).filter_by(user_id=uid, action='quiz').count() == 1
    c.get('/roadmaps/doctor'); c.get('/roadmaps/doctor')
    with core.SessionLocal() as db:
        assert db.query(XPoint).filter_by(user_id=uid, action='roadmap').count() == 1
    assert '40' in c.get('/rewards').text
    assert 'Riya' not in c.get('/leaderboard').text      # hidden by default
    c.post('/rewards/settings', data={'action': 'optin', 'csrf_token': token(c, '/rewards')})
    assert 'Riya S.' in c.get('/leaderboard').text

# ---------- access control ----------
@pytest.mark.parametrize('p', ['/rewards', '/parent', '/feedback', '/admin/growth'])
def test_login_required(anon, p):
    assert anon.get(p).status_code == 401

def test_admin_pages_forbidden_to_students():
    make_user('s2@t.in'); c = login('s2@t.in')
    assert c.get('/admin/growth').status_code == 403
    assert c.get('/parent').status_code == 403

# ---------- parent link ----------
def test_parent_link_flow():
    make_user('kid@t.in', name='Kabir Rao'); make_user('par@t.in', 'parent', 'Parent One')
    k = login('kid@t.in'); k.get('/rewards')
    with core.SessionLocal() as db:
        code = db.query(XProfile).join(core.User, core.User.id == XProfile.user_id).filter(core.User.email == 'kid@t.in').first().link_code
    p = login('par@t.in')
    bad = p.post('/parent/link', data={'code': 'WRONGCODE', 'csrf_token': token(p, '/parent')}); assert bad.status_code == 400
    assert p.post('/parent/link', data={'code': code.lower(), 'csrf_token': token(p, '/parent')}).status_code == 303
    assert 'Kabir R.' in p.get('/parent').text

# ---------- referral ----------
def test_referral_awards_both():
    make_user('ref1@t.in', name='Ref One'); a = login('ref1@t.in'); a.get('/rewards')
    with core.SessionLocal() as db:
        code = db.query(XProfile).join(core.User, core.User.id == XProfile.user_id).filter(core.User.email == 'ref1@t.in').first().referral_code
    new = make_user('ref2@t.in', name='Ref Two')
    from fastapi.testclient import TestClient
    c = TestClient(core.app, follow_redirects=False); assert c.get('/join/' + code).status_code == 303
    r = c.post('/login', data={'email': 'ref2@t.in', 'password': 'password1234', 'csrf_token': token(c)}); assert r.status_code == 303
    c.get('/rewards')
    with core.SessionLocal() as db:
        assert db.query(XPoint).filter_by(action='referral').count() >= 1 and db.query(XPoint).filter_by(user_id=new, action='referred').count() == 1

# ---------- plans ----------
def test_plan_request_activate_unlocks_report():
    make_user('buy@t.in', name='Buyer B'); make_user('adm@t.in', 'admin', 'Admin')
    u = login('buy@t.in'); quiz_post(u)
    tok = re.search(r'/career-quiz/result/([\w-]+)', u.get('/dashboard').text or '') if False else None
    with core.SessionLocal() as db:
        from extras.models import XQuizResult, XPlanRequest
        tokn = db.query(XQuizResult).join(core.User, core.User.id == XQuizResult.user_id).filter(core.User.email == 'buy@t.in').first().token
    assert 'Unlock the full report' in u.get('/report/' + tokn).text
    assert u.post('/pricing/request', data={'plan': 'bogus', 'csrf_token': token(u, '/pricing')}).status_code == 400
    assert u.post('/pricing/request', data={'plan': 'plus', 'csrf_token': token(u, '/pricing')}).status_code == 303
    assert u.post('/pricing/request', data={'plan': 'pro', 'csrf_token': token(u, '/pricing')}).status_code == 400  # one pending
    a = login('adm@t.in'); assert a.get('/admin/growth').status_code == 200
    with core.SessionLocal() as db: rid = db.query(XPlanRequest).filter_by(status='requested').first().id
    assert a.post('/admin/growth/plan/%d/activate' % rid, data={'csrf_token': token(a, '/admin/growth')}).status_code == 303
    assert '30-60-90' in u.get('/report/' + tokn).text and 'Unlock the full report' not in u.get('/report/' + tokn).text

# ---------- misc posts ----------
def test_assistant_api(anon):
    anon.get('/faq'); csrf = token(anon, '/career-quiz')
    assert anon.post('/assistant/ask', json={'q': 'cost'}).status_code == 403
    r = anon.post('/assistant/ask', json={'q': 'how much does it cost per year'}, headers={'X-CSRF': csrf}); assert r.status_code == 200 and '₹99' in r.json()['answer']

def test_resume_escapes_html(anon):
    anon.get('/resume-builder')
    r = anon.post('/resume-builder', data={'name': '<script>alert(1)</script>', 'skills': 'a,b', 'csrf_token': token(anon, '/resume-builder')})
    assert r.status_code == 200 and '<script>alert(1)' not in r.text and '&lt;script&gt;' in r.text

def test_partner_and_feedback():
    c = TestClient_anon = login(make_email := (make_user('fb@t.in', name='Feed Back') and 'fb@t.in'))
    assert c.post('/feedback', data={'rating': 5, 'message': 'Very helpful platform!', 'csrf_token': token(c, '/feedback')}).status_code == 303
    assert c.post('/feedback', data={'rating': 9, 'message': 'x', 'csrf_token': token(c, '/feedback')}).status_code == 400
    a = c; tk = token(a, '/partners')
    assert a.post('/partners', data={'org_type': 'School', 'org_name': 'ABC', 'contact_name': 'P', 'email': 'p@abc.in', 'message': 'We want seminars', 'csrf_token': tk}).status_code == 303
    assert a.post('/partners', data={'org_type': 'Hacker', 'org_name': 'x', 'contact_name': 'P', 'email': 'p@abc.in', 'message': 'We want seminars', 'csrf_token': tk}).status_code == 400

def test_existing_routes_still_work(anon):
    for p in ['/about', '/login', '/register', '/explore/seminar', '/colleges', '/contact', '/assessment', '/health']:
        assert anon.get(p).status_code == 200, p
