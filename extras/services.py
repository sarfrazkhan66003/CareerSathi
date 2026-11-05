"""External-service helpers. All are optional and configured with environment variables.
Without configuration they degrade safely (e.g. e-mails are kept in the outbox table)."""
import os, json, hmac, hashlib, base64, smtplib, logging, secrets, urllib.request, urllib.parse
from email.message import EmailMessage
import app as core
from .models2 import XOutbox

log = logging.getLogger('careersathi')
env = lambda k, d='': os.getenv(k, d)
site_url = lambda: env('SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

# ---------- e-mail (SMTP or outbox) ----------
def send_email(to, subject, body):
    """Always records the mail in x_outbox. Sends via SMTP when SMTP_HOST is set. Never raises."""
    if not to or '@' not in to: return 'skipped'
    status, rid = 'queued', None
    try:
        with core.SessionLocal() as db:
            row = XOutbox(to_email=to[:230], subject=subject[:200], body=body[:8000]); db.add(row); db.commit(); rid = row.id
        if env('SMTP_HOST'):
            msg = EmailMessage(); msg['From'] = env('SMTP_FROM', env('SMTP_USER', 'noreply@careersathi.in')); msg['To'] = to; msg['Subject'] = subject
            msg.set_content(body + '\n\n— CareerSathi · Guiding Futures, Building Careers')
            with smtplib.SMTP(env('SMTP_HOST'), int(env('SMTP_PORT', '587')), timeout=10) as s:
                if env('SMTP_TLS', '1') == '1': s.starttls()
                if env('SMTP_USER'): s.login(env('SMTP_USER'), env('SMTP_PASSWORD'))
                s.send_message(msg)
            status = 'sent'
        else:
            status = 'no_smtp'; log.warning('E-mail to %s (SMTP not configured): %s', to, subject)
    except Exception as e:
        status = 'failed'; log.error('E-mail failed: %s', e)
    try:
        with core.SessionLocal() as db:
            if rid: db.query(XOutbox).filter_by(id=rid).update({'status': status}); db.commit()
    except Exception: pass
    return status

# ---------- Razorpay ----------
def razorpay_enabled(): return bool(env('RAZORPAY_KEY_ID') and env('RAZORPAY_KEY_SECRET'))

def razorpay_create_order(amount_paise, receipt, notes=None):
    body = json.dumps({'amount': int(amount_paise), 'currency': 'INR', 'receipt': receipt[:40], 'notes': notes or {}}).encode()
    auth = base64.b64encode(('%s:%s' % (env('RAZORPAY_KEY_ID'), env('RAZORPAY_KEY_SECRET'))).encode()).decode()
    req = urllib.request.Request('https://api.razorpay.com/v1/orders', data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Basic ' + auth})
    with urllib.request.urlopen(req, timeout=15) as r: return json.loads(r.read())

def razorpay_signature_ok(order_id, payment_id, signature):
    secret = env('RAZORPAY_KEY_SECRET')
    if not (secret and order_id and payment_id and signature): return False
    exp = hmac.new(secret.encode(), ('%s|%s' % (order_id, payment_id)).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(exp, str(signature))

def razorpay_webhook_ok(raw_body, signature):
    secret = env('RAZORPAY_WEBHOOK_SECRET')
    if not (secret and signature): return False
    return hmac.compare_digest(hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest(), str(signature))

# ---------- Cloudflare Turnstile (CAPTCHA) ----------
def captcha_enabled(): return bool(env('TURNSTILE_SITE_KEY') and env('TURNSTILE_SECRET'))

def captcha_ok(response, ip=''):
    if not captcha_enabled(): return True
    if not response: return False
    try:
        data = urllib.parse.urlencode({'secret': env('TURNSTILE_SECRET'), 'response': response, 'remoteip': ip}).encode()
        with urllib.request.urlopen(urllib.request.Request('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=data), timeout=8) as r:
            return bool(json.loads(r.read()).get('success'))
    except Exception: return False

# ---------- Claude API (AI counsellor) ----------
AI_SYSTEM = ("You are Sathi, the assistant of CareerSathi, an Indian career-guidance platform for students in classes 8-12 and their parents. "
 "Reply in the user's language (English, Hindi or Hinglish), warm, simple and under 120 words. Give guidance only: explain streams, exams, skills and study paths; "
 "never promise admissions, jobs, salaries or ranks; tell users to verify dates and eligibility on official websites; do not collect personal data; "
 "never give medical, legal or mental-health diagnoses (suggest a trusted adult or professional); if a student seems in distress, encourage talking to a parent, teacher or the Tele-MANAS helpline 14416. "
 "Politely refuse unrelated requests.")

def ai_enabled(): return bool(env('ANTHROPIC_API_KEY'))

def ai_answer(question, context=''):
    if not ai_enabled(): return None
    payload = {'model': env('ANTHROPIC_MODEL', 'claude-sonnet-5-5'), 'max_tokens': 400, 'system': AI_SYSTEM + (' Context: ' + context if context else ''),
               'messages': [{'role': 'user', 'content': question[:600]}]}
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(payload).encode(),
                                 headers={'content-type': 'application/json', 'x-api-key': env('ANTHROPIC_API_KEY'), 'anthropic-version': '2023-06-01'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            parts = json.loads(r.read()).get('content', [])
        text = ' '.join(p.get('text', '') for p in parts if p.get('type') == 'text').strip()
        return text[:1500] or None
    except Exception as e:
        log.error('AI call failed: %s', e); return None

def new_token(n=24): return secrets.token_urlsafe(n)
