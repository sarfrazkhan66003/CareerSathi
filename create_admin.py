"""Create or update admin credentials interactively. Run: python create_admin.py"""
from getpass import getpass
from app import SessionLocal, User, hash_password
email=input('Admin email: ').strip().lower()
name=input('Admin name: ').strip()
password=getpass('Admin password (12+ characters): ')
if '@' not in email or not name or len(password)<12:raise SystemExit('Email/name invalid or password too short')
with SessionLocal() as db:
    user=db.query(User).filter(User.email==email).first()
    if user:
        if user.role!='admin':raise SystemExit('Existing non-admin account cannot be elevated with this script. Use a different email.')
        user.password=hash_password(password);user.active=True
    else:db.add(User(name=name,email=email,password=hash_password(password),role='admin',active=True,verified=True))
    db.commit()
print('Admin account created/updated. Sign in at /login and visit /admin/dashboard.')
