"""v12 · Payments (Razorpay), mentor slots + video links, notifications, reminders, school dashboard."""
import json, os, threading, time, hmac
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, object_session
import app as core
from .models import XProfile, XPoint, XPlanRequest
from .models2 import *
from . import services as S, data as D
from .routes import page, award, profile_for, SessionLocal, User, Booking, vt
from .routes2 import flag_for, consent_ok, need_consent

router = APIRouter()
Item = core.Item

# ---------- booking notifications (SQLAlchemy events; core code untouched) ----------
def _queue(target, kind):
    s = object_session(target)
    if s is not None: s.info.setdefault('x_notify', []).append((kind, target.id))

@event.listens_for(Booking, 'after_insert')
def _booking_inserted(mapper, conn, t): _queue(t, 'new')

@event.listens_for(Booking, 'after_update')
def _booking_updated(mapper, conn, t):
    if inspect(t).attrs.status.history.has_changes(): _queue(t, 'status')

@event.listens_for(Session, 'after_rollback')
def _rollback(session): session.info.pop('x_notify', None)

@event.listens_for(Session, 'after_commit')
def _dispatch(session):
    items = session.info.pop('x_notify', None)
    if not items: return
    run = lambda: [notify_booking(k, i) for k, i in items]
    threading.Thread(target=run, daemon=True).start() if os.getenv('SMTP_HOST') else run()

def jitsi_link(bid): return 'https://meet.jit.si/CareerSathi-%d-%s' % (bid, S.new_token(6).replace('_', 'x').replace('-', 'y'))

def ensure_link(db, b):
    l = db.query(XSessionLink).filter_by(booking_id=b.id).first()
    if l: return l.url
    f = db.query(XUserFlag).filter_by(user_id=b.mentor_id).first() if b.mentor_id else None
    url = (f.meeting_url if f and f.meeting_url.startswith('https://') else jitsi_link(b.id))
    db.add(XSessionLink(booking_id=b.id, url=url)); db.commit(); return url

def notify_booking(kind, bid):
    try:
        with SessionLocal() as db:
            b = db.get(Booking, bid)
            if not b: return
            u = db.get(User, b.user_id); m = db.get(User, b.mentor_id) if b.mentor_id else None
            item = db.get(Item, b.item_id) if b.item_id else None; what = item.title if item else (b.kind or 'session').title()
            when = b.scheduled_at.strftime('%d %b %Y, %I:%M %p') if b.scheduled_at else 'to be scheduled'
            if kind == 'new':
                S.send_email(u.email, 'Booking request received: %s' % what, 'Hi %s,\n\nWe received your request for %s (%s). Status: %s.' % (u.name.split()[0], what, when, b.status))
                if m: S.send_email(m.email, 'New session request', '%s requested a session on %s. Open your dashboard to confirm.' % (u.name, when))
            elif b.status == 'confirmed':
                link = ensure_link(db, b) if b.kind == 'mentorship' else ''
                body = 'Hi %s,\n\nYour booking for %s (%s) is confirmed.' % (u.name.split()[0], what, when) + ('\nVideo link: ' + link if link else '')
                S.send_email(u.email, 'Booking confirmed: %s' % what, body)
                if m and link: S.send_email(m.email, 'Session confirmed', 'Session with %s on %s.\nVideo link: %s' % (u.name, when, link))
            else:
                S.send_email(u.email, 'Booking update: %s' % what, 'Your booking #%d is now "%s".' % (b.id, b.status))
    except Exception as e: S.log.error('notify failed: %s', e)

# ---------- payments ----------
def fee_paise(db, purpose, ref):
    if purpose == 'plan': return D.PLANS[ref]['price'] * 100 if ref in ('plus', 'pro') else 0
    b = db.get(Booking, int(ref)); item = db.get(Item, b.item_id) if b and b.item_id else None
    return (item.price if item else int(os.getenv('MENTOR_SESSION_FEE_INR', '0'))) * 100

def complete_payment(db, pay, payment_id):
    if pay.status == 'paid': return False
    pay.status, pay.payment_id = 'paid', (payment_id or '')[:60]
    if pay.purpose == 'plan':
        p = profile_for(db, db.get(User, pay.user_id)); p.plan, p.plan_until = pay.ref, datetime.utcnow() + timedelta(days=365)
        db.query(XPlanRequest).filter_by(user_id=pay.user_id, status='requested').update({'status': 'active', 'payment_status': 'paid_online'})
    else:
        b = db.get(Booking, int(pay.ref))
        if b: b.payment_status = 'paid'
    db.commit()
    u = db.get(User, pay.user_id)
    S.send_email(u.email, 'Payment received', 'Thank you. We received ₹%d for %s %s (payment id %s).' % (pay.amount_paise // 100, pay.purpose, pay.ref, pay.payment_id))
    return True

@router.get('/pay/{purpose}/{ref}')
def pay_page(request: Request, purpose: str, ref: str):
    if purpose not in ('plan', 'booking'): raise HTTPException(404)
    with SessionLocal() as db:
        u = core.must_login(request, db); need_consent(request, db, u)
        if purpose == 'plan' and ref not in ('plus', 'pro'): raise HTTPException(404)
        if purpose == 'booking':
            b = db.get(Booking, int(ref)) if ref.isdigit() else None
            if not b or b.user_id != u.id: raise HTTPException(404, 'Booking not found')
            if b.payment_status == 'paid': raise HTTPException(400, 'This booking is already paid.')
        amount = fee_paise(db, purpose, ref)
        if amount <= 0: raise HTTPException(400, 'No payment is required for this item.')
        info = dict(purpose=purpose, ref=ref, amount=amount // 100, enabled=S.razorpay_enabled(), key=S.env('RAZORPAY_KEY_ID'), order='', error='', payer=u.name, payer_email=u.email)
        if info['enabled']:
            try:
                o = S.razorpay_create_order(amount, '%s-%s-%d' % (purpose, ref, u.id), {'user': str(u.id)})
                db.add(XPayment(user_id=u.id, purpose=purpose, ref=ref, amount_paise=amount, order_id=o['id'])); db.commit(); info['order'] = o['id']
            except Exception as e: S.log.error('razorpay order: %s', e); info['error'] = 'The payment service is unavailable right now. Please try again later.'
    return page(request, 'x_pay.html', **info)

@router.post('/pay/verify')
async def pay_verify(request: Request):
    if not request.headers.get('x-csrf') or request.headers.get('x-csrf') != request.session.get('csrf'): return JSONResponse({'error': 'Security token missing'}, 403)
    d = await request.json(); oid, pid, sig = str(d.get('order_id', '')), str(d.get('payment_id', '')), str(d.get('signature', ''))
    if not S.razorpay_signature_ok(oid, pid, sig): return JSONResponse({'error': 'Payment signature mismatch'}, 400)
    with SessionLocal() as db:
        u = core.must_login(request, db); pay = db.query(XPayment).filter_by(order_id=oid, user_id=u.id).first()
        if not pay: return JSONResponse({'error': 'Order not found'}, 404)
        complete_payment(db, pay, pid)
    return {'ok': True, 'redirect': '/pricing' if pay.purpose == 'plan' else '/my-sessions'}

@router.post('/pay/webhook')
async def pay_webhook(request: Request):
    raw = await request.body()
    if not S.razorpay_webhook_ok(raw, request.headers.get('x-razorpay-signature', '')): return JSONResponse({'error': 'bad signature'}, 400)
    ev = json.loads(raw or b'{}')
    if ev.get('event') in ('payment.captured', 'order.paid'):
        ent = ev.get('payload', {}).get('payment', {}).get('entity', {})
        with SessionLocal() as db:
            pay = db.query(XPayment).filter_by(order_id=ent.get('order_id', '')).first()
            if pay: complete_payment(db, pay, ent.get('id', ''))
    return {'ok': True}

# ---------- mentor slots, sessions, video links ----------
@router.get('/my/slots')
def my_slots(request: Request):
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['mentor']); f = flag_for(db, u)
        slots = db.query(XSlot).filter(XSlot.mentor_id == u.id, XSlot.starts_at > datetime.utcnow() - timedelta(hours=1)).order_by(XSlot.starts_at).all()
        rows = [(s.id, s.starts_at, s.minutes, s.booking_id) for s in slots]; link = f.meeting_url
    return page(request, 'x_slots_mgr.html', rows=rows, link=link)

@router.post('/my/slots/add')
def slot_add(request: Request, starts_at: str = Form(...), minutes: int = Form(30), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    try: when = datetime.fromisoformat(starts_at)
    except ValueError: raise HTTPException(400, 'Choose a valid date and time.')
    if when < datetime.utcnow() + timedelta(minutes=30) or when > datetime.utcnow() + timedelta(days=90): raise HTTPException(400, 'Choose a time between 30 minutes and 90 days from now.')
    if minutes not in (15, 30, 45, 60): raise HTTPException(400, 'Choose 15, 30, 45 or 60 minutes.')
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['mentor'])
        if db.query(XSlot).filter_by(mentor_id=u.id, starts_at=when).first(): raise HTTPException(400, 'You already have a slot at that time.')
        if db.query(XSlot).filter(XSlot.mentor_id == u.id, XSlot.booking_id == None, XSlot.starts_at > datetime.utcnow()).count() >= 40: raise HTTPException(400, 'You have too many open slots. Delete some first.')
        db.add(XSlot(mentor_id=u.id, starts_at=when, minutes=minutes)); db.commit()
    core.notice(request, 'Slot added.'); return core.redirect('/my/slots')

@router.post('/my/slots/{sid}/delete')
def slot_delete(request: Request, sid: int, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['mentor']); s = db.get(XSlot, sid)
        if not s or s.mentor_id != u.id: raise HTTPException(404)
        if s.booking_id: raise HTTPException(400, 'This slot is already booked. Cancel the booking from your dashboard.')
        db.delete(s); db.commit()
    core.notice(request, 'Slot removed.'); return core.redirect('/my/slots')

@router.post('/my/slots/link')
def slot_link(request: Request, url: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token); url = url.strip()[:300]
    if url and not url.startswith('https://'): raise HTTPException(400, 'Meeting link must start with https://')
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['mentor']); f = flag_for(db, u); f.meeting_url = url; db.commit()
    core.notice(request, 'Meeting link saved. Leave blank to use an automatic Jitsi room.'); return core.redirect('/my/slots')

@router.get('/mentors/{mid}/slots')
def mentor_slots(request: Request, mid: int):
    with SessionLocal() as db:
        m = db.get(User, mid)
        if not m or m.role != 'mentor' or not m.verified or not m.active: raise HTTPException(404, 'Mentor not found')
        slots = db.query(XSlot).filter(XSlot.mentor_id == mid, XSlot.booking_id == None, XSlot.starts_at > datetime.utcnow() + timedelta(minutes=30)).order_by(XSlot.starts_at).limit(40).all()
        rows = [(s.id, s.starts_at, s.minutes) for s in slots]; name = m.name
    return page(request, 'x_slots.html', mentor_id=mid, mentor_name=name, rows=rows, fee=int(os.getenv('MENTOR_SESSION_FEE_INR', '0')))

@router.post('/slots/{sid}/book')
def slot_book(request: Request, sid: int, note: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['student', 'parent']); need_consent(request, db, u)
        s = db.query(XSlot).filter_by(id=sid).with_for_update().first() if db.bind.dialect.name != 'sqlite' else db.get(XSlot, sid)
        if not s or s.booking_id or s.starts_at < datetime.utcnow() + timedelta(minutes=30): raise HTTPException(409, 'That slot is no longer available.')
        fee = int(os.getenv('MENTOR_SESSION_FEE_INR', '0'))
        b = Booking(user_id=u.id, mentor_id=s.mentor_id, kind='mentorship', scheduled_at=s.starts_at, note=vt(note, 1000), status='pending', payment_status='unpaid' if fee > 0 else 'not_required')
        db.add(b); db.flush(); s.booking_id = b.id; db.commit(); bid = b.id
        award(db, u.id, 'booked_slot', str(bid))
    core.notice(request, 'Session requested. The mentor will confirm and you will get the video link by email.')
    return core.redirect('/pay/booking/%d' % bid if fee > 0 else '/my-sessions')

@router.get('/my-sessions')
def my_sessions(request: Request):
    with SessionLocal() as db:
        u = core.must_login(request, db)
        bs = db.query(Booking).filter(((Booking.user_id == u.id) | (Booking.mentor_id == u.id))).order_by(Booking.scheduled_at.desc()).limit(40).all(); rows = []
        for b in bs:
            l = db.query(XSessionLink).filter_by(booking_id=b.id).first(); other = db.get(User, b.mentor_id if b.user_id == u.id else b.user_id) if (b.mentor_id or b.user_id) else None
            rows.append(dict(id=b.id, kind=b.kind, at=b.scheduled_at, status=b.status, pay=b.payment_status, link=l.url if l and b.status == 'confirmed' else '', other=other.name if other and b.kind == 'mentorship' else '', mine=b.user_id == u.id))
    return page(request, 'x_sessions.html', rows=rows)

# ---------- school dashboard ----------
@router.get('/school')
def school_dash(request: Request):
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['school', 'admin'])
        bs = db.query(Booking).filter(Booking.user_id == u.id).order_by(Booking.created_at.desc()).limit(40).all(); rows = []
        for b in bs:
            item = db.get(Item, b.item_id) if b.item_id else None; r = db.query(XSchoolReport).filter_by(booking_id=b.id).first()
            rows.append(dict(id=b.id, title=item.title if item else b.kind, kind=b.kind, at=b.scheduled_at, status=b.status, rep=(r.attendees, r.rating, r.comment) if r else None))
    return page(request, 'x_school.html', rows=rows)

@router.post('/school/report/{bid}')
def school_report(request: Request, bid: int, attendees: int = Form(...), rating: int = Form(...), comment: str = Form(''), csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    if not (0 <= attendees <= 5000 and 1 <= rating <= 5): raise HTTPException(400, 'Check attendee count (0–5000) and rating (1–5).')
    with SessionLocal() as db:
        u = core.must_login(request, db, role=['school', 'admin']); b = db.get(Booking, bid)
        if not b or (b.user_id != u.id and u.role != 'admin'): raise HTTPException(404)
        if db.query(XSchoolReport).filter_by(booking_id=bid).first(): raise HTTPException(400, 'Report already submitted.')
        db.add(XSchoolReport(booking_id=bid, user_id=u.id, attendees=attendees, rating=rating, comment=vt(comment, 1500))); db.commit()
    core.notice(request, 'Thank you. Report saved.'); return core.redirect('/school')

# ---------- reminders & weekly parent digest ----------
def run_reminders(now=None):
    now = now or datetime.utcnow(); sent = 0
    with SessionLocal() as db:
        rows = db.query(Booking).filter(Booking.scheduled_at > now, Booking.scheduled_at <= now + timedelta(hours=24), Booking.status.in_(['confirmed', 'pending'])).all()
        for b in rows:
            if db.query(XReminder).filter_by(kind='b24', ref=str(b.id)).first(): continue
            db.add(XReminder(kind='b24', ref=str(b.id))); db.commit()
            u = db.get(User, b.user_id); m = db.get(User, b.mentor_id) if b.mentor_id else None
            link = ensure_link(db, b) if b.kind == 'mentorship' and b.status == 'confirmed' else ''
            txt = 'Reminder: your booking is on %s.%s' % (b.scheduled_at.strftime('%d %b %Y, %I:%M %p'), ('\nVideo link: ' + link) if link else '')
            S.send_email(u.email, 'Reminder: upcoming booking', txt); sent += 1
            if m: S.send_email(m.email, 'Reminder: upcoming session', txt)
    return sent

def run_digests(now=None, force=False):
    now = now or datetime.utcnow(); sent = 0
    if now.weekday() != 0 and not force: return 0
    wk = '%d-%02d' % now.isocalendar()[:2]; since = now - timedelta(days=7)
    with SessionLocal() as db:
        for link in db.query(XParentLink).all():
            ref = '%d-%s' % (link.id, wk)
            if db.query(XReminder).filter_by(kind='digest', ref=ref).first(): continue
            p, s = db.get(User, link.parent_id), db.get(User, link.student_id)
            pts = db.query(XPoint).filter(XPoint.user_id == s.id, XPoint.created_at > since).all()
            total = sum(x.points for x in pts); acts = sorted({x.action for x in pts})
            db.add(XReminder(kind='digest', ref=ref)); db.commit()
            extra = (' (' + ', '.join(a.replace('_', ' ') for a in acts) + ')') if acts else ', no new activity'
            first = s.name.split()[0]
            S.send_email(p.email, 'Weekly progress: %s' % first, 'This week %s earned %d points%s.\n\nSee details: %s/parent' % (first, total, extra, S.site_url())); sent += 1
    return sent

def _loop():
    while True:
        time.sleep(900)
        try: run_reminders(); run_digests()
        except Exception as e: S.log.error('scheduler: %s', e)

def start_scheduler():
    if os.getenv('DISABLE_SCHEDULER') != '1': threading.Thread(target=_loop, daemon=True).start()

@router.post('/admin/run-reminders')
def admin_run(request: Request, csrf_token: str = Form(...)):
    core.require_csrf(request, csrf_token)
    with SessionLocal() as db: core.must_login(request, db, role=['admin'])
    n, d = run_reminders(), run_digests(force=True)
    core.notice(request, 'Sent %d reminders and %d parent digests.' % (n, d)); return core.redirect('/admin/growth')
