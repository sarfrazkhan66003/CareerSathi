import os, sys, tempfile, re
_db = os.path.join(tempfile.mkdtemp(), 'test.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + _db
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['DISABLE_SCHEDULER'] = '1'
for _k in ('SMTP_HOST','RAZORPAY_KEY_ID','RAZORPAY_KEY_SECRET','ANTHROPIC_API_KEY','TURNSTILE_SITE_KEY'): os.environ.pop(_k, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from fastapi.testclient import TestClient
import app as core

def make_user(email, role='student', name='Test User', verified=False, grade='', onboarded=True, assessed=True):
    """Creates a user; by default already email-verified and adult-consented so feature tests are not blocked by onboarding."""
    from datetime import date
    from extras.models2 import XUserFlag
    with core.SessionLocal() as db:
        u = db.query(core.User).filter_by(email=email).first()
        if not u:
            u = core.User(name=name, email=email, password=core.hash_password('password1234'), role=role, verified=verified, grade=grade)
            db.add(u); db.commit(); db.refresh(u)
            if onboarded:
                db.add(XUserFlag(user_id=u.id, dob=date(2000, 1, 1), email_verified=True, step='enquiry'))
                if assessed:
                    from extras.models2 import XAssessAttempt
                    db.add(XAssessAttempt(token='t%d' % u.id, user_id=u.id, kind='class10', done=True, result='{"overall": 80, "pcts": {"maths": 80, "science": 80}}'))
                db.commit()
        return u.id

def token(client, path='/login'):
    html = client.get(path).text
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

def login(email):
    c = TestClient(core.app, follow_redirects=False)
    r = c.post('/login', data={'email': email, 'password': 'password1234', 'csrf_token': token(c)})
    assert r.status_code == 303
    return c

@pytest.fixture
def anon():
    return TestClient(core.app, follow_redirects=False)
