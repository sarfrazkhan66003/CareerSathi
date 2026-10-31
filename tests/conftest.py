import os, sys, tempfile, re
_db = os.path.join(tempfile.mkdtemp(), 'test.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + _db
os.environ['SECRET_KEY'] = 'test-secret'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from fastapi.testclient import TestClient
import app as core

def make_user(email, role='student', name='Test User', verified=False):
    with core.SessionLocal() as db:
        u = db.query(core.User).filter_by(email=email).first()
        if not u:
            u = core.User(name=name, email=email, password=core.hash_password('password1234'), role=role, verified=verified)
            db.add(u); db.commit(); db.refresh(u)
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
