from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from app import Base, engine

now = datetime.utcnow

class XQuizResult(Base):
    __tablename__ = 'x_quiz_results'
    id = Column(Integer, primary_key=True)
    token = Column(String(40), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    scores = Column(String(120), nullable=False)      # "R:12,I:18,..."
    top = Column(String(10), default='')
    created_at = Column(DateTime, default=now)

class XPoint(Base):
    __tablename__ = 'x_points'
    __table_args__ = (UniqueConstraint('user_id', 'action', 'ref', name='uq_x_points'),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    action = Column(String(30), nullable=False)
    ref = Column(String(60), default='')
    points = Column(Integer, default=0)
    created_at = Column(DateTime, default=now)

class XProfile(Base):
    __tablename__ = 'x_profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, index=True)
    referral_code = Column(String(12), unique=True, index=True)
    link_code = Column(String(12), unique=True, index=True)
    leaderboard_optin = Column(Boolean, default=False)
    plan = Column(String(12), default='free')
    plan_until = Column(DateTime, nullable=True)

class XPlanRequest(Base):
    __tablename__ = 'x_plan_requests'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    plan = Column(String(12), nullable=False)
    status = Column(String(15), default='requested')   # requested | active | rejected
    payment_status = Column(String(20), default='unpaid')
    note = Column(String(300), default='')
    created_at = Column(DateTime, default=now)

class XReferral(Base):
    __tablename__ = 'x_referrals'
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    referee_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    created_at = Column(DateTime, default=now)

class XParentLink(Base):
    __tablename__ = 'x_parent_links'
    __table_args__ = (UniqueConstraint('parent_id', 'student_id', name='uq_x_parent'),)
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=now)

Base.metadata.create_all(bind=engine)
