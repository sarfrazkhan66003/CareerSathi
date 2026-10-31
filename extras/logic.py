"""Pure, testable business logic. No HTTP, no database."""
import re, secrets
from .data import TYPES, QUESTIONS, CAREERS, BADGES, FAQ

ORDER = list(TYPES)  # R I A S E C

def score_quiz(answers):
    """answers: list of 24 ints 1..5 -> {'R': 4..20, ...}"""
    if len(answers) != len(QUESTIONS) or any((not isinstance(a, int)) or not 1 <= a <= 5 for a in answers):
        raise ValueError('Answer all 24 questions with values 1 to 5')
    scores = {t: 0 for t in ORDER}
    for (t, _), a in zip(QUESTIONS, answers):
        scores[t] += a
    return scores

def percent(scores):
    return {t: round((v - 4) / 16 * 100) for t, v in scores.items()}  # 4..20 -> 0..100

def top_types(scores, n=3):
    return sorted(ORDER, key=lambda t: (-scores[t], ORDER.index(t)))[:n]

def rank_careers(scores):
    """Weighted fit: first RIASEC letter of a career counts 3x, second 2x, third 1x."""
    pct = percent(scores)
    out = []
    for c in CAREERS:
        weights = [3, 2, 1][:len(c['types'])]
        raw = sum(w * pct[t] for w, t in zip(weights, c['types']))
        out.append((c, round(raw / sum(weights))))
    out.sort(key=lambda x: (-x[1], x[0]['title']))
    return out

def badge_for(points):
    cur = BADGES[0]
    for b in BADGES:
        if points >= b[0]:
            cur = b
    nxt = next((b for b in BADGES if b[0] > points), None)
    return cur, nxt

def public_name(full_name):
    parts = (full_name or 'Student').split()
    return parts[0].title() + (' ' + parts[-1][0].upper() + '.' if len(parts) > 1 else '')

def new_code(n=8):
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(n))

STOP = {'how','can','the','what','does','this','that','are','for','and','you','your','who','where','when','why','with','from','about','after','class','which','please','tell','want','need','get','have','has','will','would','could','should','much','many','any','not','too','our','its','into'}

def _tok(s):
    return {w for w in re.findall(r'[a-z0-9]+', (s or '').lower()) if len(w) > 2 and w not in STOP}

def faq_answer(question):
    q = _tok(question)
    if not q:
        return None
    best, score = None, 0
    for keys, answer in FAQ:
        s = len(q & _tok(keys))
        if s > score:
            best, score = answer, s
    return best

def match_mentors(profile, mentors):
    """profile: dict(interests:str, exam:str, city:str, state:str, goal:str)
    mentors: list of dict(id,name,expertise,stream,university,exam,city,company,degree,bio)
    Returns list of (mentor, score, reasons) best first. Transparent rules, max 100."""
    want = _tok(' '.join([profile.get('interests', ''), profile.get('goal', '')]))
    exam = (profile.get('exam') or '').strip().lower()
    place = _tok(profile.get('city', '') + ' ' + profile.get('state', ''))
    result = []
    for m in mentors:
        text = _tok(' '.join(str(m.get(k, '')) for k in ('expertise', 'stream', 'degree', 'company', 'bio', 'university')))
        reasons, score = [], 0
        overlap = want & text
        if overlap:
            pts = min(60, 20 * len(overlap)); score += pts
            reasons.append('Shares your interests: ' + ', '.join(sorted(overlap)[:4]))
        if exam and exam != 'other' and exam in (m.get('exam') or '').lower():
            score += 25; reasons.append('Has taken ' + m['exam'])
        if place & _tok(m.get('city', '') + ' ' + m.get('university', '')):
            score += 15; reasons.append('Near your city/state')
        result.append((m, min(score, 100), reasons))
    result.sort(key=lambda x: (-x[1], x[0].get('name', '')))
    return result
