"""Run isolated HTTP smoke tests: python smoke_test.py"""
import os,tempfile,asyncio,re
from pathlib import Path
_tmp=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(_tmp.name)/'test.db')
os.environ['SECRET_KEY']='test-only-fixed-secret-not-for-production'
import httpx
from app import app,SessionLocal,User,hash_password
async def main():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver',follow_redirects=True) as c:
        for path in ['/','/about','/register','/login','/mentors','/explore/seminar','/explore/tour','/explore/course','/explore/internship','/assessment','/contact','/colleges','/privacy','/health']:
            r=await c.get(path)
            assert r.status_code==200,(path,r.status_code)
        r=await c.get('/register');token=re.search(r'name="csrf_token" value="([^"]+)',r.text).group(1)
        r=await c.post('/register',data={'name':'Test Student','email':'student@example.org','password':'ValidLongPass123','role':'student','csrf_token':token})
        assert r.status_code==200 and str(r.url).endswith('/journey')
        assert (await c.get('/admin/dashboard')).status_code==403
        assert 'Your future' in (await c.get('/journey')).text
        r=await c.get('/journey');token=re.search(r'name="csrf_token" value="([^"]+)',r.text).group(1)
        r=await c.post('/journey/profile',data={'school':'Test Public School','grade':'10','percentage':'84.5','state':'Bihar','city':'Sitamarhi','csrf_token':token});assert r.status_code==200
        r=await c.post('/journey/assessment',data={'interests':['math','coding','research'],'work_style':'analytical','favorite_subject':'Mathematics','csrf_token':token});assert r.status_code==200
        r=await c.post('/journey/enquiry',data={'subject':'Science PCM','institute_type':'Government','location':'Patna','budget':'₹50000','note':'Seeking academic guidance','csrf_token':token});assert r.status_code==200
        assert (await c.post('/contact',data={'csrf_token':'wrong','name':'A','email':'a@example.org','message':'Important enquiry'})).status_code==403
        with SessionLocal() as db:
            db.add(User(name='Admin Test',email='admin@example.org',password=hash_password('AdminLongPass123'),role='admin',active=True));db.commit()
        await c.get('/login');token=c.cookies.get('session')
        # Use the current session's actual CSRF token from the HTML page
        r=await c.get('/login');csrf=re.search(r'name="csrf_token" value="([^"]+)',r.text).group(1)
        r=await c.post('/login',data={'email':'admin@example.org','password':'AdminLongPass123','csrf_token':csrf})
        assert r.status_code==200
        r=await c.get('/admin/dashboard');assert r.status_code==200
        csrf=re.search(r'name="csrf_token" value="([^"]+)',r.text).group(1)
        r=await c.post('/admin/item',data={'title':'Career options seminar','kind':'seminar','description':'Explore careers','csrf_token':csrf})
        assert r.status_code==200
        assert 'Career options seminar' in (await c.get('/explore/seminar')).text
        print('PASS — 14 public routes, signup, login, role isolation, CSRF rejection, admin and content publishing')
asyncio.run(main())
_tmp.cleanup()
