import os, secrets, hashlib, hmac, csv, io, json, urllib.request, urllib.error, re
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

BASE = os.path.dirname(os.path.abspath(__file__))
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(BASE, 'careersathi.db'))
if DB_URL.startswith('postgres://'): DB_URL = DB_URL.replace('postgres://', 'postgresql://', 1)
engine = create_engine(DB_URL, connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
now = datetime.utcnow

class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True); name=Column(String(130),nullable=False); email=Column(String(230),unique=True,nullable=False,index=True); password=Column(String(250),nullable=False)
    role=Column(String(25),nullable=False,default='student'); phone=Column(String(30),default=''); grade=Column(String(30),default=''); city=Column(String(90),default=''); bio=Column(Text,default=''); expertise=Column(String(150),default=''); institution=Column(String(150),default=''); active=Column(Boolean,default=True); verified=Column(Boolean,default=False); created_at=Column(DateTime,default=now)
class Item(Base):
    __tablename__='items'
    id=Column(Integer,primary_key=True); kind=Column(String(25),index=True); title=Column(String(220),nullable=False); subtitle=Column(String(230),default=''); description=Column(Text,default=''); category=Column(String(90),default=''); location=Column(String(120),default=''); starts_at=Column(DateTime,nullable=True); price=Column(Integer,default=0); capacity=Column(Integer,default=0); published=Column(Boolean,default=True); mentor_id=Column(Integer,ForeignKey('users.id'),nullable=True); created_at=Column(DateTime,default=now)
class Booking(Base):
    __tablename__='bookings'
    id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id'),nullable=False); item_id=Column(Integer,ForeignKey('items.id'),nullable=True); mentor_id=Column(Integer,ForeignKey('users.id'),nullable=True); kind=Column(String(30),nullable=False); scheduled_at=Column(DateTime,nullable=True); note=Column(Text,default=''); status=Column(String(30),default='pending'); payment_status=Column(String(30),default='not_required'); created_at=Column(DateTime,default=now)
class Review(Base):
    __tablename__='reviews'
    id=Column(Integer,primary_key=True); author_id=Column(Integer,ForeignKey('users.id')); college=Column(String(180),nullable=False); rating=Column(Integer,default=5); text=Column(Text,nullable=False); approved=Column(Boolean,default=False); created_at=Column(DateTime,default=now)
class Inquiry(Base):
    __tablename__='inquiries'
    id=Column(Integer,primary_key=True); name=Column(String(130)); email=Column(String(230)); topic=Column(String(120)); message=Column(Text); resolved=Column(Boolean,default=False); created_at=Column(DateTime,default=now)
class Visit(Base):
    __tablename__='visits'
    id=Column(Integer,primary_key=True); visitor=Column(String(70),index=True); path=Column(String(230)); created_at=Column(DateTime,default=now)
class Assessment(Base):
    __tablename__='assessments'
    id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id')); interest=Column(String(60)); style=Column(String(60)); recommendation=Column(String(140)); created_at=Column(DateTime,default=now)
class StudentJourney(Base):
    __tablename__='student_journeys'
    id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id'),unique=True,index=True,nullable=False)
    school=Column(String(180),default=''); grade=Column(String(30),default=''); percentage=Column(String(15),default=''); state=Column(String(70),default=''); city=Column(String(100),default='')
    exam=Column(String(60),default=''); exam_score=Column(String(35),default=''); aim=Column(String(100),default=''); interests=Column(String(250),default=''); stage=Column(String(40),default='registered'); updated_at=Column(DateTime,default=now,onupdate=now)
class MentorCredentials(Base):
    __tablename__='mentor_credentials'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),unique=True,index=True,nullable=False)
    marks10=Column(String(20),default=''); marks12=Column(String(20),default='')
    exam=Column(String(50),default=''); exam_score=Column(String(60),default='')
    university=Column(String(180),default=''); degree=Column(String(140),default='')
    stream=Column(String(120),default=''); cgpa=Column(String(35),default='')
    placement_status=Column(String(50),default=''); company=Column(String(150),default='')
    graduation_year=Column(String(10),default=''); linkedin=Column(String(250),default='')
    updated_at=Column(DateTime,default=now,onupdate=now)

class JourneyEnquiry(Base):
    __tablename__='journey_enquiries'
    id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id'),nullable=False); subject=Column(String(120)); institute_type=Column(String(80)); location=Column(String(160)); budget=Column(String(60)); note=Column(Text); created_at=Column(DateTime,default=now)

class Feedback(Base):
    __tablename__='feedback'
    id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id')); booking_id=Column(Integer,ForeignKey('bookings.id')); rating=Column(Integer); message=Column(Text); created_at=Column(DateTime,default=now)

Base.metadata.create_all(bind=engine)
app=FastAPI(title='CareerSathi', docs_url=None if os.getenv('APP_ENV')=='production' else '/api/docs')
app.add_middleware(SessionMiddleware,secret_key=os.getenv('SECRET_KEY',secrets.token_urlsafe(45)),same_site='lax',https_only=os.getenv('APP_ENV')=='production')
app.mount('/static',StaticFiles(directory=os.path.join(BASE,'static')),name='static')
tpl=Jinja2Templates(directory=os.path.join(BASE,'templates'))
KINDS={'seminar':'Seminars & workshops','tour':'College tours','course':'Skill development','internship':'Internships','resource':'Career resources'}


# Public reference directory. These are NOT CareerSathi partners or scheduled tours.
REGIONS = [
'Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal','Andaman and Nicobar Islands','Chandigarh','Dadra and Nagar Haveli and Daman and Diu','Delhi','Jammu and Kashmir','Ladakh','Lakshadweep','Puducherry']
COLLEGE_DIRECTORY = [
('Indian Institute of Technology Madras','Chennai','Tamil Nadu','Engineering','https://www.iitm.ac.in/'),
('Indian Institute of Technology Delhi','New Delhi','Delhi','Engineering','https://home.iitd.ac.in/'),
('Indian Institute of Technology Bombay','Mumbai','Maharashtra','Engineering','https://www.iitb.ac.in/'),
('Indian Institute of Technology Kanpur','Kanpur','Uttar Pradesh','Engineering','https://www.iitk.ac.in/'),
('Indian Institute of Technology Kharagpur','Kharagpur','West Bengal','Engineering','https://www.iitkgp.ac.in/'),
('Indian Institute of Technology Roorkee','Roorkee','Uttarakhand','Engineering','https://www.iitr.ac.in/'),
('Indian Institute of Technology Hyderabad','Hyderabad','Telangana','Engineering','https://www.iith.ac.in/'),
('Indian Institute of Technology Guwahati','Guwahati','Assam','Engineering','https://www.iitg.ac.in/'),
('National Institute of Technology Tiruchirappalli','Tiruchirappalli','Tamil Nadu','Engineering','https://www.nitt.edu/'),
('National Institute of Technology Warangal','Warangal','Telangana','Engineering','https://www.nitw.ac.in/'),
('Delhi Technological University','New Delhi','Delhi','Engineering','https://dtu.ac.in/'),
('Thapar Institute of Engineering and Technology','Patiala','Punjab','Engineering','https://www.thapar.edu/'),
('National Institute of Technology Patna','Patna','Bihar','Engineering','https://www.nitp.ac.in/'),
('National Institute of Technology Raipur','Raipur','Chhattisgarh','Engineering','https://www.nitrr.ac.in/'),
('Sardar Vallabhbhai National Institute of Technology','Surat','Gujarat','Engineering','https://www.svnit.ac.in/'),
('National Institute of Technology Kurukshetra','Kurukshetra','Haryana','Engineering','https://nitkkr.ac.in/'),
('PSG College of Technology','Coimbatore','Tamil Nadu','Engineering','https://www.psgtech.edu/'),
('COEP Technological University','Pune','Maharashtra','Engineering','https://www.coeptech.ac.in/'),
('Indian Institute of Technology Jodhpur','Jodhpur','Rajasthan','Engineering','https://iitj.ac.in/'),
('Indian Institute of Technology Mandi','Mandi','Himachal Pradesh','Engineering','https://www.iitmandi.ac.in/'),
('Indian Institute of Technology Jammu','Jammu','Jammu and Kashmir','Engineering','https://www.iitjammu.ac.in/'),
('Indian Institute of Technology Tirupati','Tirupati','Andhra Pradesh','Engineering','https://www.iittp.ac.in/'),
('Indian Institute of Technology Palakkad','Palakkad','Kerala','Engineering','https://iitpkd.ac.in/'),
('Indian Institute of Technology Ropar','Rupnagar','Punjab','Engineering','https://www.iitrpr.ac.in/'),
('National Institute of Technology Meghalaya','Shillong','Meghalaya','Engineering','https://nitm.ac.in/'),
('Indian Institute of Technology Bhubaneswar','Bhubaneswar','Odisha','Engineering','https://www.iitbbs.ac.in/'),
('Indian Institute of Technology Indore','Indore','Madhya Pradesh','Engineering','https://www.iiti.ac.in/'),
('Indian Institute of Technology Gandhinagar','Gandhinagar','Gujarat','Engineering','https://iitgn.ac.in/'),
('Indian Institute of Technology (BHU)','Varanasi','Uttar Pradesh','Engineering','https://www.iitbhu.ac.in/'),
('Indian Institute of Technology (ISM) Dhanbad','Dhanbad','Jharkhand','Engineering','https://www.iitism.ac.in/'),
('National Institute of Technology Silchar','Silchar','Assam','Engineering','https://www.nits.ac.in/'),
('National Institute of Technology Srinagar','Srinagar','Jammu and Kashmir','Engineering','https://nitsri.ac.in/'),
('National Institute of Technology Agartala','Agartala','Tripura','Engineering','https://nita.ac.in/'),
('Jawaharlal Nehru University','New Delhi','Delhi','University','https://www.jnu.ac.in/'),
('University of Delhi','New Delhi','Delhi','University','https://www.du.ac.in/'),
('Banaras Hindu University','Varanasi','Uttar Pradesh','University','https://www.bhu.ac.in/'),
('University of Hyderabad','Hyderabad','Telangana','University','https://uohyd.ac.in/'),
('Savitribai Phule Pune University','Pune','Maharashtra','University','https://www.unipune.ac.in/'),
('Laxmi Narain College of Technology, Bhopal','Bhopal','Madhya Pradesh','Engineering','https://lnct.ac.in/'),
('All India Institute of Medical Sciences New Delhi','New Delhi','Delhi','Medicine','https://www.aiims.edu/'),
('National Law School of India University','Bengaluru','Karnataka','Law','https://www.nls.ac.in/'),
('Indian Institute of Management Ahmedabad','Ahmedabad','Gujarat','Management','https://www.iima.ac.in/'),
('Indian Institute of Management Bangalore','Bengaluru','Karnataka','Management','https://www.iimb.ac.in/'),
('National Institute of Design Ahmedabad','Ahmedabad','Gujarat','Design','https://www.nid.edu/')]
GUIDES = [
('course','Python programming fundamentals','Technology','Online','A self-study learning pathway: Python basics, variables, loops, functions, files and a portfolio mini-project. Suggested tools: Python docs and practice exercises.'),
('course','Communication and public speaking','Soft skills','Online','An introductory roadmap covering confident introductions, active listening, presentations, group discussions and feedback.'),
('course','Excel and data literacy','Technology','Online','Practice spreadsheets, formulas, charts, data cleaning and presenting findings. Suitable for beginners.'),
('course','Web development essentials','Technology','Online','Follow HTML, CSS, JavaScript, accessibility and a personal portfolio project. Self-paced starter roadmap.'),
('course','Resume and interview preparation','Career readiness','Online','Build an accurate resume, prepare STAR examples and practice interview questions. Guidance resource, not a certification.'),
('course','Financial literacy for students','Finance','Online','Learn budgeting, savings, compounding, digital payments and the basics of fraud prevention.'),
('course','Creative design fundamentals','Design','Online','Explore typography, layout, colour, wireframing, user research and simple portfolio exercises.'),
('course','Introduction to AI and data science','Technology','Online','Learn the distinctions between AI, ML and data science, datasets, evaluation and responsible use.'),
('resource','What to choose after Class 10?','Class 10','India','Compare Science, Commerce, Humanities and vocational pathways with subjects, eligibility and personal interests in mind.'),
('resource','Career planning after Class 12','Class 12','India','Build a shortlist by interests, programme eligibility, fees, location, admission process and future flexibility.'),
('resource','How to compare colleges fairly','College selection','India','Check approvals, programmes, current admission prospectus, total cost, faculty, facilities, verified placement records and independent reviews.'),
('resource','Scholarships and financial aid checklist','Financial aid','India','Search official national/state scholarship portals, check eligibility documents and never pay a guaranteed-scholarship agent.'),
('resource','Engineering career pathways','Career exploration','India','Explore computer science, mechanical, civil, electrical and interdisciplinary fields through study and project examples.'),
('resource','Healthcare careers beyond MBBS','Career exploration','India','Explore nursing, allied health sciences, pharmacy, public health, medical technology and the associated eligibility requirements.'),
('resource','How to prepare for a school seminar','Schools','India','A school coordinator checklist: target classes, capacity, accessibility, venue, consent, learning goals and follow-up feedback.'),
('resource','Internship safety checklist','Career readiness','India','Verify company and supervisor, written responsibilities, age eligibility, payment terms, safeguarding and suspicious upfront fees.'),
('resource','Questions to ask a mentor','Mentorship','India','Ask about their route into the field, day-to-day work, skill expectations, costs and possible alternative pathways.'),
('resource','A parent’s guide to career conversations','Parents','India','Use open questions, discuss interests and affordability, and help students make their own informed decisions.')]

def hash_password(password):
    salt=secrets.token_bytes(16); h=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,350000)
    return salt.hex()+':'+h.hex()
def verify_password(password,stored):
    try:
        salt,digest=stored.split(':'); check=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),350000)
        return hmac.compare_digest(check,bytes.fromhex(digest))
    except Exception:return False

def csrf(request):
    if not request.session.get('csrf'):request.session['csrf']=secrets.token_urlsafe(24)
    return request.session['csrf']
def require_csrf(request,token):
    if not token or not hmac.compare_digest(str(token),str(request.session.get('csrf',''))):raise HTTPException(403,'Invalid security token. Refresh and retry.')
def current_user(request,db):
    uid=request.session.get('uid'); u=db.get(User,uid) if uid else None
    if u and not u.active:request.session.clear();return None
    return u
def must_login(request,db,role=None):
    u=current_user(request,db)
    if not u:raise HTTPException(401,'Please log in to continue.')
    if role and u.role not in role:raise HTTPException(403,'You do not have access to this action.')
    return u
def render(request,name,**ctx):
    with SessionLocal() as db:
        user=current_user(request,db)
        data={'request':request,'user':user,'csrf':csrf(request),'kinds':KINDS,'notice':request.session.pop('notice',None),'year':date.today().year,'regions':REGIONS}
    data.update(ctx)
    return tpl.TemplateResponse(request,name,data)
def notice(request,text):request.session['notice']=text
def redirect(url):return RedirectResponse(url,status_code=303)
def dt(value):
    if not value:return None
    try:return datetime.fromisoformat(value)
    except:raise HTTPException(400,'Invalid date/time')
def ensure_future(d):
    if d and d<now():raise HTTPException(400,'Choose a future date/time')
def validate_text(s,n=250):return str(s or '').strip()[:n]

@app.middleware('http')
async def tracking(request,call_next):
    if request.url.path.startswith(('/static','/api/','/favicon.ico')):return await call_next(request)
    visitor=request.cookies.get('cs_vid') or secrets.token_urlsafe(16)
    response=await call_next(request)
    if request.method=='GET' and response.status_code<400 and not request.url.path.startswith('/admin'):
        try:
            with SessionLocal() as db:
                db.add(Visit(visitor=visitor,path=request.url.path[:230]));db.commit()
        except Exception:pass
    if not request.cookies.get('cs_vid'):response.set_cookie('cs_vid',visitor,max_age=31536000,httponly=True,samesite='lax',secure=os.getenv('APP_ENV')=='production')
    return response

@app.get('/',response_class=HTMLResponse)
def home(request:Request):
    with SessionLocal() as db:
        featured=db.query(Item).filter(Item.published==True,Item.kind.in_(['seminar','course','tour'])).order_by(Item.created_at.desc()).limit(6).all()
        mentors=db.query(User).filter(User.role=='mentor',User.verified==True,User.active==True).limit(3).all()
    return render(request,'home.html',featured=featured,mentors=mentors)

@app.get('/about')
def about(request:Request):return render(request,'about.html')
@app.get('/privacy')
def privacy(request:Request):return render(request,'legal.html',kind='privacy')
@app.get('/terms')
def terms(request:Request):return render(request,'legal.html',kind='terms')

def validate_mentor_fields(marks10,marks12,exam,exam_score,university,stream,cgpa,placement,year):
    if not university.strip() or not stream.strip():raise HTTPException(400,'Mentor university and stream are required')
    for label,value in [('Class 10 marks',marks10),('Class 12 marks',marks12)]:
        if not value.strip():raise HTTPException(400,label+' required')
        try: num=float(value)
        except:raise HTTPException(400,label+' must be a percentage from 0 to 100')
        if not 0<=num<=100:raise HTTPException(400,label+' must be between 0 and 100')
    if cgpa.strip():
        try: num=float(cgpa)
        except:raise HTTPException(400,'CGPA must be numeric')
        if not 0<=num<=10:raise HTTPException(400,'CGPA must use 0–10 scale')
    if exam not in ('','JEE Main','JEE Advanced','NEET UG','CUET UG','Other'):raise HTTPException(400,'Invalid exam')
    if placement not in ('','Student','Seeking placement','Placed','Self-employed','Other'):raise HTTPException(400,'Invalid placement status')
    if year.strip() and (not year.isdigit() or not 1950<=int(year)<=2100):raise HTTPException(400,'Invalid graduation year')

@app.get('/register')
def register_page(request:Request):return render(request,'auth.html',mode='register')
@app.post('/register')
def register(request:Request,name:str=Form(...),email:str=Form(...),password:str=Form(...),role:str=Form('student'),phone:str=Form(''),grade:str=Form(''),school_name:str=Form(''),percentage:str=Form(''),state:str=Form(''),city:str=Form(''),purpose:str=Form(''),marks10:str=Form(''),marks12:str=Form(''),mentor_exam:str=Form(''),mentor_exam_score:str=Form(''),university:str=Form(''),degree:str=Form(''),stream:str=Form(''),cgpa:str=Form(''),placement_status:str=Form(''),company:str=Form(''),graduation_year:str=Form(''),linkedin:str=Form(''),expertise:str=Form(''),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    email=email.strip().lower()
    if role not in ['student','parent','mentor','school']:raise HTTPException(400,'Invalid account type')
    if len(password)<10:raise HTTPException(400,'Password must be at least 10 characters')
    if not (3<=len(name.strip())<=130) or '@' not in email:raise HTTPException(400,'Enter a valid name and email')
    if role=='mentor':
        validate_mentor_fields(marks10,marks12,mentor_exam,mentor_exam_score,university,stream,cgpa,placement_status,graduation_year)
    with SessionLocal() as db:
        if db.query(User).filter(User.email==email).first():raise HTTPException(400,'Email already registered')
        u=User(name=name.strip(),email=email,password=hash_password(password),role=role,phone=phone[:30],grade=grade[:30],expertise=validate_text(expertise,150) if role=='mentor' else '');db.add(u);db.commit();db.refresh(u)
        if role=='mentor':
            db.add(MentorCredentials(user_id=u.id,marks10=marks10.strip(),marks12=marks12.strip(),exam=mentor_exam.strip(),exam_score=validate_text(mentor_exam_score,60),university=validate_text(university,180),degree=validate_text(degree,140),stream=validate_text(stream,120),cgpa=cgpa.strip(),placement_status=placement_status.strip(),company=validate_text(company,150),graduation_year=graduation_year.strip(),linkedin=validate_text(linkedin,250)));db.commit()
        request.session['uid']=u.id
    if role=='student':
        with SessionLocal() as db:
            db.add(StudentJourney(user_id=u.id,grade=grade[:30],school=validate_text(school_name,180),percentage=percentage[:15],state=state[:70],city=city[:100],aim=purpose[:100]));db.commit()
    notice(request,'Welcome to CareerSathi! Complete your guidance journey.')
    return redirect('/journey' if role=='student' else '/dashboard')
@app.get('/journey')
def journey_page(request:Request):
    with SessionLocal() as db:
        user=must_login(request,db)
        if user.role!='student':return redirect('/dashboard')
        journey=db.query(StudentJourney).filter_by(user_id=user.id).first()
        if not journey:
            journey=StudentJourney(user_id=user.id,grade=user.grade,school=user.institution or '',city=user.city or '');db.add(journey);db.commit();db.refresh(journey)
        assessments=db.query(Assessment).filter_by(user_id=user.id).order_by(Assessment.created_at.desc()).limit(1).all()
        enquiries=db.query(JourneyEnquiry).filter_by(user_id=user.id).order_by(JourneyEnquiry.created_at.desc()).limit(5).all()
    return render(request,'journey.html',journey=journey,latest=assessments[0] if assessments else None,enquiries=enquiries)

@app.post('/journey/profile')
def journey_profile(request:Request,school:str=Form(...),grade:str=Form(...),percentage:str=Form(''),state:str=Form(''),city:str=Form(''),exam:str=Form(''),exam_score:str=Form(''),aim:str=Form(''),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    if grade not in ['8','9','10','11','12','college','other']:raise HTTPException(400,'Select a valid class')
    if percentage:
        try:
            if not 0<=float(percentage)<=100:raise ValueError()
        except ValueError:raise HTTPException(400,'Percentage must be between 0 and 100')
    with SessionLocal() as db:
        user=must_login(request,db,role=['student']); journey=db.query(StudentJourney).filter_by(user_id=user.id).first()
        if not journey:journey=StudentJourney(user_id=user.id);db.add(journey)
        for k,v,limit in [('school',school,180),('grade',grade,30),('percentage',percentage,15),('state',state,70),('city',city,100),('exam',exam,60),('exam_score',exam_score,35),('aim',aim,100)]:setattr(journey,k,validate_text(v,limit))
        journey.stage='profile';user.grade=grade;user.institution=school[:150];user.city=city[:90];db.commit()
    return redirect('/journey#assessment')

@app.post('/journey/assessment')
def journey_assessment(request:Request,interests:list[str]=Form([]),work_style:str=Form(...),favorite_subject:str=Form(...),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    allowed={'math','biology','coding','business','finance','arts','writing','social','design','law','sports','research','people'}
    selected=[x for x in interests if x in allowed]
    if not selected or work_style not in ['practical','analytical','creative','people'] or len(favorite_subject)>100:raise HTTPException(400,'Select your interests and learning style')
    scores={'Science (PCM)':0,'Science (PCB)':0,'Commerce':0,'Arts / Humanities':0}
    weights={'math':(3,0,1,0),'biology':(0,3,0,1),'coding':(3,0,1,0),'business':(0,0,3,1),'finance':(1,0,3,0),'arts':(0,0,0,3),'writing':(0,0,1,3),'social':(0,1,0,3),'design':(1,0,1,3),'law':(0,0,1,3),'sports':(1,1,1,1),'research':(2,2,0,1),'people':(0,2,1,2)}
    for interest in selected:
        for key,weight in zip(scores,weights[interest]):scores[key]+=weight
    if work_style=='creative':scores['Arts / Humanities']+=2
    if work_style=='analytical':scores['Science (PCM)']+=1;scores['Science (PCB)']+=1
    if work_style=='people':scores['Arts / Humanities']+=1;scores['Science (PCB)']+=1
    ranked=sorted(scores,key=lambda key:(-scores[key],list(scores).index(key)))
    with SessionLocal() as db:
        user=must_login(request,db,role=['student']); journey=db.query(StudentJourney).filter_by(user_id=user.id).first()
        if not journey:journey=StudentJourney(user_id=user.id);db.add(journey)
        journey.interests=','.join(selected);journey.stage='assessed'
        recommendation=('Possible streams to explore: '+', '.join(ranked[:2])) if journey.grade in ['8','9','10','11'] else ('Career areas to investigate: '+', '.join(ranked[:2]))
        db.add(Assessment(user_id=user.id,interest=','.join(selected),style=work_style,recommendation=recommendation));db.commit()
    notice(request,'Assessment saved. Review your options and send an enquiry.');return redirect('/journey#choose')

@app.post('/journey/enquiry')
def journey_enquiry(request:Request,subject:str=Form(...),institute_type:str=Form(''),location:str=Form(''),budget:str=Form(''),note:str=Form(''),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    if subject not in ['Science PCM','Science PCB','Commerce','Arts / Humanities','Vocational / Diploma','Engineering','Medical / Healthcare','Law','Design','Management','Government Exams','Scholarship','College Admission','Mentorship','Other']:raise HTTPException(400,'Choose a valid goal')
    with SessionLocal() as db:
        user=must_login(request,db,role=['student'])
        if not db.query(Assessment).filter_by(user_id=user.id).first():raise HTTPException(400,'Complete your assessment before making an enquiry')
        db.add(JourneyEnquiry(user_id=user.id,subject=subject,institute_type=validate_text(institute_type,80),location=validate_text(location,160),budget=validate_text(budget,60),note=validate_text(note,1500)))
        j=db.query(StudentJourney).filter_by(user_id=user.id).first()
        if j:j.stage='enquired'
        db.commit()
    notice(request,'Enquiry received. Our team can review your preferences in the admin dashboard.');return redirect('/journey#enquiry')

@app.get('/login')
def login_page(request:Request):return render(request,'auth.html',mode='login')
@app.post('/login')
def login(request:Request,email:str=Form(...),password:str=Form(...),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        u=db.query(User).filter(User.email==email.lower().strip()).first()
        if not u or not u.active or not verify_password(password,u.password):raise HTTPException(401,'Invalid credentials or disabled account')
        request.session.clear();request.session['uid']=u.id
    return redirect('/admin/dashboard' if u.role=='admin' else '/dashboard')
@app.post('/logout')
def logout(request:Request,csrf_token:str=Form(...)):
    require_csrf(request,csrf_token);request.session.clear();return redirect('/')

@app.get('/dashboard')
def dashboard(request:Request):
    with SessionLocal() as db:
        u=must_login(request,db)
        if u.role=='admin':return redirect('/admin/dashboard')
        if u.role=='mentor':
            bookings=db.query(Booking,User).join(User,Booking.user_id==User.id).filter(Booking.mentor_id==u.id).order_by(Booking.created_at.desc()).all()
        else:
            bookings=db.query(Booking,Item).outerjoin(Item,Booking.item_id==Item.id).filter(Booking.user_id==u.id).order_by(Booking.created_at.desc()).all()
        assessments=db.query(Assessment).filter(Assessment.user_id==u.id).order_by(Assessment.created_at.desc()).limit(3).all()
    return render(request,'dashboard.html',bookings=bookings,assessments=assessments)
@app.get('/profile')
def profile_page(request:Request):
    with SessionLocal() as db:
        u=must_login(request,db)
        credentials=db.query(MentorCredentials).filter_by(user_id=u.id).first() if u.role=='mentor' else None
        return render(request,'profile.html',credentials=credentials)
@app.post('/profile')
def profile_save(request:Request,name:str=Form(...),phone:str=Form(''),city:str=Form(''),grade:str=Form(''),expertise:str=Form(''),institution:str=Form(''),bio:str=Form(''),marks10:str=Form(''),marks12:str=Form(''),mentor_exam:str=Form(''),mentor_exam_score:str=Form(''),university:str=Form(''),degree:str=Form(''),stream:str=Form(''),cgpa:str=Form(''),placement_status:str=Form(''),company:str=Form(''),graduation_year:str=Form(''),linkedin:str=Form(''),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        u=must_login(request,db)
        for key,val,limit in [('name',name,130),('phone',phone,30),('city',city,90),('grade',grade,30),('expertise',expertise,150),('institution',institution,150),('bio',bio,2000)]:setattr(u,key,validate_text(val,limit))
        if u.role=='mentor':
            validate_mentor_fields(marks10,marks12,mentor_exam,mentor_exam_score,university,stream,cgpa,placement_status,graduation_year)
            cred=db.query(MentorCredentials).filter_by(user_id=u.id).first()
            if not cred:cred=MentorCredentials(user_id=u.id);db.add(cred)
            fields={'marks10':marks10,'marks12':marks12,'exam':mentor_exam,'exam_score':mentor_exam_score,'university':university,'degree':degree,'stream':stream,'cgpa':cgpa,'placement_status':placement_status,'company':company,'graduation_year':graduation_year,'linkedin':linkedin}
            for k,v in fields.items():setattr(cred,k,validate_text(v,250))
            u.verified=False # Updated credentials must be reviewed by admin again.
        db.commit()
    notice(request,'Profile saved. Academic edits require mentor re-verification.' if u.role=='mentor' else 'Profile updated successfully');return redirect('/profile')

@app.get('/explore/{kind}')
def explore(request:Request,kind:str,q:str='',category:str='',state:str='',city:str='',live:str=''):
    if kind not in KINDS:raise HTTPException(404)
    with SessionLocal() as db:
        query=db.query(Item).filter(Item.kind==kind,Item.published==True)
        if q:query=query.filter(Item.title.ilike('%'+q[:80]+'%'))
        if category:query=query.filter(Item.category==category)
        if state:query=query.filter(Item.location.ilike('%'+state[:80]+'%'))
        if city:query=query.filter(Item.location.ilike('%'+city[:80]+'%'))
        items=query.order_by(Item.starts_at.asc().nullslast(),Item.created_at.desc()).all()
        categories=[r[0] for r in db.query(Item.category).filter(Item.kind==kind,Item.published==True,Item.category!='').distinct().all()]
    directory=[]; live_results=[]; live_error=None
    if kind=='tour':
        for c in COLLEGE_DIRECTORY:
            if state and state.casefold()!=c[2].casefold():continue
            if city and city.casefold() not in c[1].casefold():continue
            if q and q.casefold() not in (' '.join(c[:4])+(' LNCT' if 'Laxmi Narain' in c[0] else '')).casefold():continue
            directory.append(c)
        if live=='1' and (q or city or state):
            if os.getenv('GOOGLE_PLACES_API_KEY'):
                live_results,live_error=live_institutes(state,city,q,'college')
            else:
                live_error='Optional Google live search is not configured; showing available reference institutions below.'
    return render(request,'explore.html',kind=kind,items=items,q=q,category=category,categories=categories,state=state,city=city,directory=directory,college_indices={c[0]:i for i,c in enumerate(COLLEGE_DIRECTORY)},live_results=live_results,live_error=live_error,live=live,api_configured=bool(os.getenv('GOOGLE_PLACES_API_KEY')))
@app.get('/item/{item_id}')
def detail(request:Request,item_id:int):
    with SessionLocal() as db:
        item=db.get(Item,item_id)
        if not item or not item.published:raise HTTPException(404)
        existing=db.query(Booking).filter(Booking.item_id==item_id,Booking.status!='cancelled').count()
    return render(request,'detail.html',item=item,existing=existing,lesson_sections=[x.strip() for x in (item.description or '').split('\n\n') if x.strip()])
@app.post('/book/item/{item_id}')
def book_item(request:Request,item_id:int,note:str=Form(''),scheduled_at:str=Form(''),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        u=must_login(request,db)
        if u.role not in ['student','parent','school']:raise HTTPException(403,'This account cannot book this service')
        item=db.get(Item,item_id)
        if not item or not item.published:raise HTTPException(404)
        if item.capacity and db.query(Booking).filter(Booking.item_id==item.id,Booking.status!='cancelled').count()>=item.capacity:raise HTTPException(400,'This event is full')
        if db.query(Booking).filter(Booking.user_id==u.id,Booking.item_id==item_id,Booking.status!='cancelled').first():raise HTTPException(400,'Already booked or enrolled')
        when=dt(scheduled_at) if scheduled_at else item.starts_at
        if item.kind=='tour' and not when:raise HTTPException(400,'Choose a preferred tour date')
        ensure_future(when)
        db.add(Booking(user_id=u.id,item_id=item.id,kind=item.kind,scheduled_at=when,note=validate_text(note,800),status='pending' if item.kind in ['tour','internship'] else 'confirmed',payment_status='unpaid' if item.price>0 else 'not_required'))
        db.commit()
    notice(request,'Request received! Check its status in your dashboard. Paid reservations are not final until confirmed by the team.');return redirect('/dashboard')
@app.get('/mentors')
def mentors(request:Request,q:str=''):
    with SessionLocal() as db:
        query=db.query(User).filter(User.role=='mentor',User.active==True,User.verified==True)
        if q:query=query.filter((User.expertise.ilike('%'+q[:70]+'%'))|(User.name.ilike('%'+q[:70]+'%')))
        people=query.all()
    return render(request,'mentors.html',people=people,q=q)
@app.get('/mentor/{mentor_id}')
def mentor_profile(request:Request,mentor_id:int):
    with SessionLocal() as db:
        mentor=db.get(User,mentor_id)
        if not mentor or mentor.role!='mentor' or not mentor.verified or not mentor.active:raise HTTPException(404)
    return render(request,'mentor.html',mentor=mentor,credentials=db.query(MentorCredentials).filter_by(user_id=mentor.id).first())
@app.post('/book/mentor/{mentor_id}')
def mentor_book(request:Request,mentor_id:int,scheduled_at:str=Form(...),note:str=Form(...),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    d=dt(scheduled_at);ensure_future(d)
    if not d:raise HTTPException(400,'Select a date')
    with SessionLocal() as db:
        u=must_login(request,db,role=['student','parent'])
        mentor=db.get(User,mentor_id)
        if not mentor or mentor.role!='mentor' or not mentor.verified or not mentor.active:raise HTTPException(404)
        clash=db.query(Booking).filter(Booking.mentor_id==mentor_id,Booking.scheduled_at==d,Booking.status.in_(['pending','confirmed'])).first()
        if clash:raise HTTPException(409,'This slot has already been requested. Please choose another.')
        db.add(Booking(user_id=u.id,mentor_id=mentor_id,kind='mentorship',scheduled_at=d,note=validate_text(note,1000),status='pending',payment_status='unpaid'));db.commit()
    notice(request,'Mentorship request sent! Admin or mentor will confirm your session.');return redirect('/dashboard')
@app.post('/booking/{booking_id}/{action}')
def booking_action(request:Request,booking_id:int,action:str,csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    if action not in ['cancel','confirm','complete']:raise HTTPException(400)
    with SessionLocal() as db:
        u=must_login(request,db);b=db.get(Booking,booking_id)
        if not b:raise HTTPException(404)
        if action=='cancel' and (u.id==b.user_id or u.role=='admin'):b.status='cancelled'
        elif action in ['confirm','complete'] and (u.role=='admin' or (u.role=='mentor' and b.mentor_id==u.id)):b.status='confirmed' if action=='confirm' else 'completed'
        else:raise HTTPException(403)
        db.commit()
    notice(request,'Booking updated');return redirect('/admin/dashboard' if u.role=='admin' else '/dashboard')
@app.get('/assessment')
def assessment_page(request:Request):return render(request,'assessment.html',result=None)
@app.post('/assessment')
def assessment_submit(request:Request,interest:str=Form(...),style:str=Form(...),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    suggestions={'technology':'Technology, engineering & data','people':'Healthcare, education & psychology','business':'Business, finance & entrepreneurship','creative':'Design, media & communication','science':'Research, science & environment'}
    result=suggestions.get(interest)
    if not result or style not in ['hands-on','analytical','collaborative']:raise HTTPException(400)
    with SessionLocal() as db:
        u=current_user(request,db)
        if u:db.add(Assessment(user_id=u.id,interest=interest,style=style,recommendation=result));db.commit()
    return render(request,'assessment.html',result=result)
# Google Places API New: optional live lookup, no scraping, no fabricated coverage.
# Query results are not persisted; provider's API terms and billing apply.
def live_institutes(state='', district='', q='', kind='all'):
    key=os.getenv('GOOGLE_PLACES_API_KEY','').strip()
    if not key or not (state or district or q):return [], 'Live institute search is not configured. Add GOOGLE_PLACES_API_KEY to the server environment.'
    term={'school':'schools','college':'colleges','university':'universities','all':'schools colleges universities'}.get(kind,'schools colleges universities')
    where=', '.join(x for x in [district,state,'India'] if x)
    phrase=' '.join(x for x in [q,term,'in',where] if x)[:250]
    body=json.dumps({'textQuery':phrase,'pageSize':20,'regionCode':'IN','languageCode':'en'}).encode()
    req=urllib.request.Request('https://places.googleapis.com/v1/places:searchText',data=body,headers={'Content-Type':'application/json','X-Goog-Api-Key':key,'X-Goog-FieldMask':'places.id,places.displayName,places.formattedAddress,places.googleMapsUri,places.primaryType'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=7) as response:results=json.load(response).get('places',[])
        return [{'name':v.get('displayName',{}).get('text','Institution'),'address':v.get('formattedAddress',''),'link':v.get('googleMapsUri',''),'type':v.get('primaryType','Educational institution')} for v in results if v.get('id')],None
    except (urllib.error.URLError,TimeoutError,ValueError) as exc:
        return [], 'Live search is temporarily unavailable. Check API key, API access/billing, or network connectivity.'

@app.get('/institutes')
def institutes_redirect(q:str='',state:str='',district:str='',kind:str='all',live:str=''):
    from urllib.parse import urlencode
    params={k:v for k,v in [('q',q),('state',state),('city',district),('live',live)] if v}
    return RedirectResponse('/explore/tour'+('?' + urlencode(params) if params else ''),status_code=302)

@app.get('/college/{college_id}')
def college_profile(request:Request,college_id:int):
    if college_id < 0 or college_id >= len(COLLEGE_DIRECTORY):raise HTTPException(404,'College not found')
    c=COLLEGE_DIRECTORY[college_id]
    return render(request,'college_profile.html',college=c,college_id=college_id)

@app.get('/college-compare')
def college_compare(request:Request,ids:str=''):
    choices=[]
    for part in ids.split(','):
        if part.strip().isdigit():
            i=int(part)
            if 0 <= i < len(COLLEGE_DIRECTORY) and i not in choices:choices.append(i)
    return render(request,'college_compare.html',choices=[(i,COLLEGE_DIRECTORY[i]) for i in choices[:4]])

@app.get('/colleges')
def colleges(request:Request,q:str='',state:str='',stream:str=''):
    with SessionLocal() as db: reviews=db.query(Review,User).join(User,Review.author_id==User.id).filter(Review.approved==True).order_by(Review.created_at.desc()).limit(40).all()
    return render(request,'colleges.html',reviews=reviews,college_indices={c[0]:i for i,c in enumerate(COLLEGE_DIRECTORY)},college_directory=[c for c in COLLEGE_DIRECTORY if (not q or q.casefold() in (' '.join(c[:4])).casefold()) and (not state or c[2]==state) and (not stream or c[3]==stream)],q=q,state=state,stream=stream)
@app.post('/colleges/review')
def review_add(request:Request,college:str=Form(...),rating:int=Form(...),text:str=Form(...),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    if not 1<=rating<=5 or len(text.strip())<20:raise HTTPException(400,'Provide a rating and at least 20 characters')
    with SessionLocal() as db:
        u=must_login(request,db)
        db.add(Review(author_id=u.id,college=validate_text(college,180),rating=rating,text=validate_text(text,3000)));db.commit()
    notice(request,'Thanks! Your review was submitted for moderation.');return redirect('/colleges')
@app.get('/contact')
def contact_page(request:Request):return render(request,'contact.html')
@app.post('/contact')
def contact_submit(request:Request,name:str=Form(...),email:str=Form(...),topic:str=Form('General enquiry'),message:str=Form(...),state:str=Form(''),city:str=Form(''),institution:str=Form(''),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    if state and state not in REGIONS:raise HTTPException(400,'Please choose a valid state or union territory')
    if len(message.strip())<10 or '@' not in email:raise HTTPException(400,'Enter a valid email and message')
    with SessionLocal() as db:db.add(Inquiry(name=validate_text(name,130),email=validate_text(email,230),topic=validate_text(topic,120),message=validate_text('State/UT: '+state+'\nCity/district: '+city+'\nSchool/college: '+institution+'\n\n'+message,4000)));db.commit()
    notice(request,'Your enquiry has been received. Our team will contact you.');return redirect('/contact')

@app.get('/admin/dashboard')
def admin_dashboard(request:Request):
    with SessionLocal() as db:
        must_login(request,db,role=['admin'])
        data={'users':db.query(User).count(),'active':db.query(User).filter(User.active==True).count(),'visits':db.query(Visit).count(),'visitors':db.query(func.count(func.distinct(Visit.visitor))).scalar() or 0,'bookings':db.query(Booking).count(),'inquiries':db.query(Inquiry).filter(Inquiry.resolved==False).count(),'reviews_pending':db.query(Review).filter(Review.approved==False).count()}
        users=db.query(User).order_by(User.created_at.desc()).limit(25).all()
        bookings=db.query(Booking,User).join(User,Booking.user_id==User.id).order_by(Booking.created_at.desc()).limit(25).all()
        items=db.query(Item).order_by(Item.created_at.desc()).limit(25).all()
        inquiries=db.query(Inquiry).order_by(Inquiry.created_at.desc()).limit(20).all()
        reviews=db.query(Review).order_by(Review.created_at.desc()).limit(20).all()
        journeys=db.query(JourneyEnquiry,User).join(User,JourneyEnquiry.user_id==User.id).order_by(JourneyEnquiry.created_at.desc()).limit(50).all()
        since=now()-timedelta(days=13)
        daily=dict(db.query(func.date(Visit.created_at),func.count(Visit.id)).filter(Visit.created_at>=since).group_by(func.date(Visit.created_at)).all())
        chart=[{'date':(date.today()-timedelta(days=i)).isoformat(),'visits':daily.get((date.today()-timedelta(days=i)).isoformat(),0)} for i in range(13,-1,-1)]
    return render(request,'admin.html',stats=data,users=users,bookings=bookings,items=items,inquiries=inquiries,reviews=reviews,journeys=journeys,chart=chart)
@app.post('/admin/user/{uid}/{action}')
def admin_user(request:Request,uid:int,action:str,csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        admin=must_login(request,db,role=['admin']);u=db.get(User,uid)
        if not u or u.id==admin.id:raise HTTPException(400,'Cannot change this user')
        if action=='disable':u.active=False
        elif action=='enable':u.active=True
        elif action=='verify' and u.role=='mentor':u.verified=True
        elif action=='unverify' and u.role=='mentor':u.verified=False
        else:raise HTTPException(400)
        db.commit()
    notice(request,'User access updated');return redirect('/admin/dashboard#users')
@app.post('/admin/item')
def admin_item(request:Request,title:str=Form(...),kind:str=Form(...),description:str=Form(''),subtitle:str=Form(''),category:str=Form(''),location:str=Form(''),starts_at:str=Form(''),price:int=Form(0),capacity:int=Form(0),csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        must_login(request,db,role=['admin'])
        if kind not in KINDS or price<0 or capacity<0 or not title.strip():raise HTTPException(400)
        db.add(Item(title=validate_text(title,220),kind=kind,description=validate_text(description,6000),subtitle=validate_text(subtitle,230),category=validate_text(category,90),location=validate_text(location,120),starts_at=dt(starts_at),price=price,capacity=capacity));db.commit()
    notice(request,'Content published');return redirect('/admin/dashboard#content')
@app.post('/admin/item/{item_id}/toggle')
def admin_toggle(request:Request,item_id:int,csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        must_login(request,db,role=['admin']);item=db.get(Item,item_id)
        if not item:raise HTTPException(404)
        item.published=not item.published;db.commit()
    return redirect('/admin/dashboard#content')
@app.post('/admin/review/{review_id}/{action}')
def admin_review(request:Request,review_id:int,action:str,csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        must_login(request,db,role=['admin']);r=db.get(Review,review_id)
        if not r:raise HTTPException(404)
        if action=='approve':r.approved=True
        elif action=='hide':r.approved=False
        else:raise HTTPException(400)
        db.commit()
    return redirect('/admin/dashboard#reviews')
@app.post('/admin/inquiry/{inquiry_id}/resolve')
def resolve(request:Request,inquiry_id:int,csrf_token:str=Form(...)):
    require_csrf(request,csrf_token)
    with SessionLocal() as db:
        must_login(request,db,role=['admin']);v=db.get(Inquiry,inquiry_id)
        if not v:raise HTTPException(404)
        v.resolved=True;db.commit()
    return redirect('/admin/dashboard#inquiries')
@app.get('/admin/export/{kind}')
def admin_export(request:Request,kind:str):
    with SessionLocal() as db:
        must_login(request,db,role=['admin'])
        if kind=='users':headers=['ID','Name','Email','Role','Active','Verified','Joined'];rows=[[u.id,u.name,u.email,u.role,u.active,u.verified,u.created_at.isoformat()] for u in db.query(User).all()]
        elif kind=='bookings':headers=['ID','User ID','Type','Item ID','Mentor ID','Status','Payment Status','Date'];rows=[[b.id,b.user_id,b.kind,b.item_id,b.mentor_id,b.status,b.payment_status,b.created_at.isoformat()] for b in db.query(Booking).all()]
        elif kind=='visits':headers=['Day','Page','Views'];rows=[[d,p,n] for d,p,n in db.query(func.date(Visit.created_at),Visit.path,func.count(Visit.id)).group_by(func.date(Visit.created_at),Visit.path).all()]
        else:raise HTTPException(404)
    f=io.StringIO();w=csv.writer(f);w.writerow(headers);w.writerows(rows)
    return StreamingResponse(iter([f.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="careersathi_{kind}.csv"'})
@app.get('/health')
def health():return {'status':'ok','service':'CareerSathi'}

# --- v11 Growth Pack (additive): quiz, roadmaps, match, rewards, parent, plans, resume, FAQ assistant ---
import sys as _sys
_sys.modules.setdefault('app', _sys.modules[__name__])
from extras import router as _extras_router
app.include_router(_extras_router)

if __name__=='__main__':
    import uvicorn
    uvicorn.run('app:app',host='127.0.0.1',port=8000)
