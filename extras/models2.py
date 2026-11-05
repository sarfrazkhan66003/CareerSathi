"""v12 tables (all new, prefixed x_). Existing tables are never altered."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey, UniqueConstraint
from app import Base, engine
now = datetime.utcnow
FK = lambda t: ForeignKey(t + '.id')

class XUserFlag(Base):            # email verification, age/guardian consent, onboarding, mentor link
    __tablename__ = 'x_user_flags'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, default=False)
    verify_token = Column(String(60), index=True)
    verify_sent_at = Column(DateTime)
    dob = Column(Date)
    guardian_name = Column(String(130), default='')
    guardian_email = Column(String(230), default='')
    guardian_token = Column(String(60), index=True)
    guardian_consent = Column(Boolean, default=False)
    consent_at = Column(DateTime)
    step = Column(String(20), default='consent')      # consent | assessment | enquiry | done
    meeting_url = Column(String(300), default='')      # mentor's own video link (optional)
    created_at = Column(DateTime, default=now)

class XReset(Base):
    __tablename__ = 'x_resets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)

class XOutbox(Base):
    __tablename__ = 'x_outbox'
    id = Column(Integer, primary_key=True)
    to_email = Column(String(230), index=True)
    subject = Column(String(200))
    body = Column(Text)
    status = Column(String(15), default='queued')     # queued | sent | no_smtp | failed
    created_at = Column(DateTime, default=now)

class XLoginAttempt(Base):
    __tablename__ = 'x_login_attempts'
    id = Column(Integer, primary_key=True)
    ip = Column(String(60), index=True)
    email = Column(String(230), index=True)
    ok = Column(Boolean, default=False)
    at = Column(DateTime, default=now, index=True)

class XAssessAttempt(Base):
    __tablename__ = 'x_assess_attempts'
    id = Column(Integer, primary_key=True)
    token = Column(String(40), unique=True, index=True)
    user_id = Column(Integer, FK('users'), index=True)
    kind = Column(String(20))
    qids = Column(Text, default='')         # "R3,M7,..."
    sections = Column(Text, default='')     # JSON: section -> [correct,total]
    result = Column(Text, default='')       # JSON: streams, band
    done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

class XEnquiry(Base):
    __tablename__ = 'x_enquiries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), nullable=False, index=True)
    name = Column(String(130)); email = Column(String(230)); phone = Column(String(30), default='')
    grade = Column(String(20)); marks = Column(String(15), default='')
    exam = Column(String(60), default=''); exam_score = Column(String(60), default='')
    stream = Column(String(30), default='')
    purposes = Column(String(300), default='')
    career_goal = Column(String(200), default='')
    colleges = Column(Text, default='')      # JSON list, max 5
    comment = Column(Text, default='')
    mentor_id = Column(Integer, FK('users'))
    mentor_status = Column(String(15), default='none')   # none | requested | auto | allotted
    status = Column(String(15), default='new')            # new | allotted | closed
    created_at = Column(DateTime, default=now)

class XSlot(Base):
    __tablename__ = 'x_slots'
    __table_args__ = (UniqueConstraint('mentor_id', 'starts_at', name='uq_x_slot'),)
    id = Column(Integer, primary_key=True)
    mentor_id = Column(Integer, FK('users'), nullable=False, index=True)
    starts_at = Column(DateTime, nullable=False, index=True)
    minutes = Column(Integer, default=30)
    booking_id = Column(Integer, FK('bookings'))

class XSessionLink(Base):
    __tablename__ = 'x_session_links'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, FK('bookings'), unique=True, nullable=False)
    url = Column(String(300))

class XPayment(Base):
    __tablename__ = 'x_payments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), nullable=False, index=True)
    purpose = Column(String(20))            # plan | booking
    ref = Column(String(40))                # plan key or booking id
    amount_paise = Column(Integer, default=0)
    order_id = Column(String(60), unique=True, index=True)
    payment_id = Column(String(60))
    status = Column(String(15), default='created')   # created | paid | failed
    created_at = Column(DateTime, default=now)

class XReviewVote(Base):
    __tablename__ = 'x_review_votes'
    __table_args__ = (UniqueConstraint('review_id', 'user_id', name='uq_x_rvote'),)
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, FK('reviews'), nullable=False, index=True)
    user_id = Column(Integer, FK('users'), nullable=False)

class XInternship(Base):
    __tablename__ = 'x_internships'
    id = Column(Integer, primary_key=True)
    company = Column(String(150)); contact_name = Column(String(130)); contact_email = Column(String(230))
    title = Column(String(180)); description = Column(Text); location = Column(String(100), default='')
    stipend = Column(String(60), default=''); apply_by = Column(String(20), default='')
    status = Column(String(12), default='pending', index=True)   # pending | approved | rejected
    created_at = Column(DateTime, default=now)

class XApplication(Base):
    __tablename__ = 'x_applications'
    __table_args__ = (UniqueConstraint('internship_id', 'user_id', name='uq_x_app'),)
    id = Column(Integer, primary_key=True)
    internship_id = Column(Integer, FK('x_internships'), nullable=False)
    user_id = Column(Integer, FK('users'), nullable=False)
    message = Column(Text, default='')
    created_at = Column(DateTime, default=now)

class XPractice(Base):
    __tablename__ = 'x_practice'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), nullable=False, index=True)
    topic = Column(String(20)); score = Column(Integer, default=0); total = Column(Integer, default=0)
    created_at = Column(DateTime, default=now)

class XLesson(Base):
    __tablename__ = 'x_lessons'
    __table_args__ = (UniqueConstraint('user_id', 'item_id', 'idx', name='uq_x_lesson'),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), nullable=False, index=True)
    item_id = Column(Integer, FK('items'), nullable=False)
    idx = Column(Integer, nullable=False)

class XStreak(Base):
    __tablename__ = 'x_streaks'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), unique=True, nullable=False)
    last_day = Column(Date); count = Column(Integer, default=0); best = Column(Integer, default=0)

class XPost(Base):
    __tablename__ = 'x_posts'
    id = Column(Integer, primary_key=True)
    slug = Column(String(120), unique=True, index=True)
    title = Column(String(200)); summary = Column(String(300), default=''); body = Column(Text)
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)

class XSchoolReport(Base):
    __tablename__ = 'x_school_reports'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, FK('bookings'), unique=True, nullable=False)
    user_id = Column(Integer, FK('users'), nullable=False)
    attendees = Column(Integer, default=0); rating = Column(Integer, default=5); comment = Column(Text, default='')
    created_at = Column(DateTime, default=now)

class XTestimonial(Base):
    __tablename__ = 'x_testimonials'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, FK('users'), nullable=False)
    text = Column(Text); label = Column(String(80), default='')
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

class XAudit(Base):
    __tablename__ = 'x_audit'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer); method = Column(String(8)); path = Column(String(200)); status = Column(Integer)
    at = Column(DateTime, default=now, index=True)

class XCollege(Base):
    __tablename__ = 'x_colleges'
    id = Column(Integer, primary_key=True)
    name = Column(String(180), unique=True); city = Column(String(80), default=''); state = Column(String(80), default='')
    stream = Column(String(80), default=''); url = Column(String(250), default='')

class XReminder(Base):
    __tablename__ = 'x_reminders'
    __table_args__ = (UniqueConstraint('kind', 'ref', name='uq_x_rem'),)
    id = Column(Integer, primary_key=True)
    kind = Column(String(20)); ref = Column(String(40)); at = Column(DateTime, default=now)

Base.metadata.create_all(bind=engine)
