"""Pure assessment logic (no HTTP, no DB)."""
import random, json
from .assess_data import BANK, BY_SECTION, BY_SECTION_F, KINDS, INTEREST, SECTIONS

STREAM_NAMES = {'PCM': 'PCM (Physics, Chemistry, Maths)', 'PCB': 'PCB (Physics, Chemistry, Biology)', 'PCMB': 'PCMB (Maths + Biology both)',
                'COM': 'Commerce', 'ART': 'Arts / Humanities'}
# weights per stream: section or interest-code -> weight
WEIGHTS = {
 'PCM': {'maths': .30, 'reasoning': .20, 'science': .20, 'interest': .30},
 'PCB': {'science': .35, 'reasoning': .10, 'maths': .10, 'english': .05, 'interest': .40},
 'COM': {'maths': .25, 'reasoning': .15, 'english': .20, 'social': .10, 'interest': .30},
 'ART': {'social': .25, 'english': .25, 'gk': .15, 'reasoning': .10, 'interest': .25},
}

def audience(grade):
    """Which assessments are offered for a class value ('8'..'12','college','other')."""
    g = str(grade)
    if g in ('8', '9'): return ['foundation']
    if g == '10': return ['class10']
    return ['subject', 'aptitude', 'gk']          # 11, 12, college, other (plus Career Compass quiz)

def pick_questions(kind, seed):
    rng = random.Random(seed); ids = []
    for sec, n in KINDS[kind]['mix'].items():
        pool = (BY_SECTION_F if kind == 'foundation' else BY_SECTION)[sec][:]; rng.shuffle(pool); ids += pool[:n]
    return ids

def grade(qids, answers):
    """answers: dict qid -> chosen index. Returns {section: [correct,total]} and review rows."""
    sec = {}; review = []
    for qid in qids:
        q = BANK[qid]; s = sec.setdefault(q['sec'], [0, 0]); s[1] += 1
        got = answers.get(qid); ok = got == q['a']
        s[0] += 1 if ok else 0
        review.append(dict(q=q['q'], opts=q['opts'], chosen=got, right=q['a'], ok=ok, why=q['why'], sec=q['sec']))
    return sec, review

def percents(sec): return {k: round(c / t * 100) for k, (c, t) in sec.items() if t}

def band(p):
    if p >= 80: return 'Excellent'
    if p >= 60: return 'Strong'
    if p >= 40: return 'Developing'
    return 'Needs practice'

def interest_scores(likert):
    """likert: list of ints (1..5) aligned with INTEREST. Returns pct per stream code (0..100)."""
    tot = {}; cnt = {}
    for (code, _), v in zip(INTEREST, likert):
        tot[code] = tot.get(code, 0) + (v - 1) / 4 * 100; cnt[code] = cnt.get(code, 0) + 1
    return {k: tot[k] / cnt[k] for k in tot}

def suggest_streams(pcts, interest=None):
    """Weighted fit per stream using the sections that exist. Returns sorted [(code, score)] and a PCMB flag."""
    out = {}
    for st, w in WEIGHTS.items():
        num = den = 0
        for key, wt in w.items():
            if key == 'interest':
                if interest and st in interest: num += wt * interest[st]; den += wt
            elif key in pcts: num += wt * pcts[key]; den += wt
        if den: out[st] = round(num / den)
    ranked = sorted(out.items(), key=lambda x: -x[1])
    flag = 'PCM' in out and 'PCB' in out and out['PCM'] >= 65 and out['PCB'] >= 65 and abs(out['PCM'] - out['PCB']) <= 10 and pcts.get('maths', 0) >= 60 and pcts.get('science', 0) >= 60
    return ranked, flag

def stream_advice(code, flag):
    notes = {'PCM': 'Opens engineering, architecture, data science, defence, pure sciences. Needs steady practice in maths and physics.',
             'PCB': 'Opens medicine (NEET), pharmacy, biotechnology, allied health. Needs strong biology and chemistry memory plus concept clarity.',
             'COM': 'Opens CA, finance, business, economics, law (with CLAT), management. Maths is optional but helps.',
             'ART': 'Opens law, civil services, journalism, psychology, design, teaching, languages. Rewards reading and writing.'}
    extra = ' You are strong in both maths and biology, so PCMB is possible, but it is a heavy load.' if flag and code in ('PCM', 'PCB') else ''
    return notes[code] + extra

def result_payload(kind, sec, likert=None):
    pcts = percents(sec); total_c = sum(c for c, t in sec.values()); total_t = sum(t for c, t in sec.values())
    overall = round(total_c / total_t * 100) if total_t else 0
    data = dict(overall=overall, band=band(overall), pcts=pcts)
    if KINDS[kind]['stream']:
        interest = interest_scores(likert) if likert and len(likert) == len(INTEREST) else None
        ranked, flag = suggest_streams(pcts, interest)
        data['streams'] = ranked; data['pcmb'] = bool(flag)
    strong = sorted(pcts.items(), key=lambda x: -x[1]); data['strong'] = [SECTIONS[k] for k, v in strong[:2]]; data['weak'] = [SECTIONS[k] for k, v in strong[::-1][:2] if v < 60]
    return data
