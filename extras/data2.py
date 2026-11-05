"""v12 content: enquiry options, practice banks, finders, translations, blog seeds."""
GRADES = [('8','Class 8'),('9','Class 9'),('10','Class 10'),('11','Class 11'),('12','Class 12'),('college','College / passed 12th'),('other','Other')]
STREAM_OPTS = [('PCM','PCM'),('PCB','PCB'),('PCMB','PCMB (both Maths & Biology)'),('COM','Commerce'),('ART','Arts / Humanities')]
EXAMS = ['None yet','JEE Main','JEE Advanced','NEET UG','CUET UG','CLAT','NDA','NATA / JEE Paper 2','UCEED / NID DAT','CA Foundation','State CET','Olympiad / NTSE (school level)','Other']
PURPOSES = [('stream','I want to choose my stream'),('roadmap','I want to understand the roadmap for my career'),('skills','I have a career doubt: which skills should I develop?'),
            ('college','I want help choosing colleges'),('exam','Entrance exam preparation'),('scholarship','Scholarship / fees help'),('other','Other doubt')]

# ---------- practice ----------
HR = [
 ('H1','In an interview you are asked, "Tell me about yourself." What is the best approach?',['Read your whole biography from birth','Give a short summary of education, skills and goals relevant to the role','Say "there is nothing special"','Talk only about your hobbies'],1,'A 60–90 second, relevant summary shows clarity and respect for the interviewer\'s time.'),
 ('H2','"What is your biggest weakness?" Which answer is strongest?',['"I have no weaknesses."','"I work too hard." (without detail)','A real, non-critical weakness plus the steps you are taking to improve','A weakness that makes you unsuitable for the role'],2,'Honesty with an improvement plan shows self-awareness.'),
 ('H3','"Why should we select you?" Best response:',['"Because I need the job."','Link your skills to their need, with one concrete example','"Select me, I am the best."','Criticise other candidates'],1,'Evidence-based, role-linked answers are convincing.'),
 ('H4','You disagree with a teammate on a project. What do you do?',['Complain to the teacher/manager first','Listen, discuss facts, and agree on the goal and a fair test','Ignore the teammate','Do the work alone and say nothing'],1,'Collaboration and fact-based discussion resolve conflict best.'),
 ('H5','You realise you will miss a deadline. Best action?',['Hide it until the deadline','Inform early, explain, and offer a revised plan','Blame someone else','Submit poor-quality work silently'],1,'Early, honest communication builds trust.'),
 ('H6','"Where do you see yourself in five years?" Best answer:',['"In your chair."','Describe realistic growth in skills and responsibility that fits the role','"I have no idea and no plans."','"Working somewhere else."'],1,'Show ambition that is aligned with the role.'),
 ('H7','You do not know the answer to a technical question. What should you do?',['Make up an answer confidently','Say honestly you are not sure, then explain how you would find or reason it out','Stay silent','Change the topic'],1,'Honest reasoning is valued more than bluffing.'),
 ('H8','At the end the interviewer asks, "Do you have any questions?" Best choice:',['"No."','Ask thoughtful questions about learning, the team or expectations','Ask only about leave and salary','Ask something already on their website'],1,'Good questions show interest and preparation.'),
]
CODE_MCQ = [
 ('P1','Python: what does print(type([])) display?',["<class 'tuple'>","<class 'list'>","<class 'dict'>","<class 'set'>"],1,'[] is an empty list.'),
 ('P2','Python: what is len({1, 2, 2, 3})?',['4','3','2','Error'],1,'A set stores unique values: {1, 2, 3}.'),
 ('P3','Python: what is the value of 2 ** 3 ** 2?',['64','512','36','128'],1,'Exponent is right-associative: 2 ** (3 ** 2) = 2 ** 9 = 512.'),
 ('P4','Python: what does "abc"[::-1] return?',['abc','cba','bca','Error'],1,'A step of -1 reverses the string.'),
 ('P5','Which Python structure gives average O(1) lookup by key?',['list','dict','tuple scan','string'],1,'Dictionaries are hash tables.'),
 ('P6','SQL: which clause filters rows AFTER GROUP BY?',['WHERE','HAVING','ORDER BY','LIMIT'],1,'HAVING filters groups; WHERE filters rows before grouping.'),
 ('P7','Python: what does print(10 // 3, 10 % 3) display?',['3.33 1','3 1','3 3','1 3'],1,'// is floor division (3) and % is remainder (1).'),
 ('P8','Which data structure follows LIFO (last in, first out)?',['Queue','Stack','Array only','Graph'],1,'A stack removes the most recently added item first.'),
 ('P9','What is the time complexity of binary search on a sorted array?',['O(n)','O(log n)','O(n log n)','O(1)'],1,'The search space halves every step.'),
 ('P10','Which HTML tag creates the largest heading?',['<h6>','<head>','<h1>','<title>'],2,'<h1> is the top-level heading.'),
]
CODING = [
 ('Reverse a string','Write a function that returns the reverse of a given string.','Python slicing or a loop from the end.','def rev(s):\n    return s[::-1]'),
 ('Palindrome check','Return True if a string reads the same forwards and backwards (ignore case).','Compare the cleaned string with its reverse.','def is_pal(s):\n    s = s.lower()\n    return s == s[::-1]'),
 ('FizzBuzz','Print numbers 1 to 100. For multiples of 3 print Fizz, of 5 print Buzz, of both print FizzBuzz.','Check the multiple-of-15 case first.','for i in range(1, 101):\n    if i % 15 == 0: print("FizzBuzz")\n    elif i % 3 == 0: print("Fizz")\n    elif i % 5 == 0: print("Buzz")\n    else: print(i)'),
 ('Two Sum','Given a list and a target, return indices of two numbers adding up to the target.','Use a dictionary of value → index while scanning once.','def two_sum(a, t):\n    seen = {}\n    for i, x in enumerate(a):\n        if t - x in seen: return [seen[t - x], i]\n        seen[x] = i'),
 ('Count vowels','Count vowels (a, e, i, o, u) in a string.','Loop and test membership in a set of vowels.','def vowels(s):\n    return sum(c in "aeiou" for c in s.lower())'),
]
PRACTICE_TOPICS = {'hr': ('Mock interview (HR)', HR), 'coding': ('Coding & tech basics', CODE_MCQ)}

# ---------- finders (guidance only) ----------
CAT = ['General','OBC','SC','ST','Minority','Person with disability','Girl child / woman']
LEVELS = [('school','School (Class 8–12)'),('ug','Undergraduate'),('pg','Postgraduate')]
INCOME = ['Below ₹1 lakh','₹1–2.5 lakh','₹2.5–8 lakh','Above ₹8 lakh','Prefer not to say']
def scholarships(state, cat, level, income):
    out = [('National Scholarship Portal (NSP)','https://scholarships.gov.in/','Central and many state schemes are applied for here. Open the portal, choose your level, and read each scheme\'s eligibility, income limit and last date.')]
    if state: out.append(('State scholarship portal: %s' % state, 'https://scholarships.gov.in/', 'Search "%s scholarship portal" on the official state government site; many states run their own schemes with separate dates.' % state))
    if cat in ('SC', 'ST', 'OBC', 'Minority'): out.append(('Category-based schemes (%s)' % cat, 'https://scholarships.gov.in/', 'The portal lists pre-matric / post-matric and merit-cum-means schemes for your category. Keep caste/community and income certificates ready.'))
    if cat == 'Person with disability': out.append(('Schemes for students with disabilities', 'https://scholarships.gov.in/', 'Check the disability-related schemes on NSP and your State Social Welfare department.'))
    if cat == 'Girl child / woman': out.append(('Schemes for girls and women', 'https://www.aicte-india.org/', 'AICTE and state governments run schemes for girl students in technical education; confirm current names on the official site.'))
    if level in ('ug', 'pg'): out.append(('UGC and university scholarships', 'https://www.ugc.gov.in/', 'Check UGC fellowships/schemes and your university\'s own merit scholarships.'))
    if income in ('Below ₹1 lakh', '₹1–2.5 lakh'): out.append(('Means-based fee support', 'https://scholarships.gov.in/', 'Lower family income may qualify you for means-tested schemes. Ask your school/college scholarship cell.'))
    return out

PREDICT_EXAMS = {'JEE Main': 'https://josaa.nic.in/', 'NEET UG': 'https://mcc.nic.in/', 'CUET UG': 'https://cuet.nta.nic.in/'}
def predict_bands(exam, rank):
    """Qualitative guidance bands. NOT cutoffs; real cutoffs change every year and by category."""
    if exam == 'JEE Main':
        tiers = [(5000,'Very strong rank. Explore top NITs, IIITs and leading institutes; check each branch\'s previous-year closing ranks.'),
                 (30000,'Strong rank. Explore NITs/IIITs (various branches) and top state/private institutes.'),
                 (150000,'Good options exist in state government and reputed private colleges; compare placements and fees carefully.'),
                 (10**9,'Consider reputed private colleges, BCA/BSc Computer Science/Data, or reappearing with a clear plan. Skills and projects matter a lot.')]
    elif exam == 'NEET UG':
        tiers = [(20000,'Very competitive rank. Government MBBS seats may be possible depending on state and category; check MCC/state counselling rules.'),
                 (100000,'Government seats are possible in some states/categories; also explore BDS, BAMS/BHMS and private options by fees.'),
                 (10**9,'Explore allied health, B.Pharm, BSc Nursing, biotechnology and other life-science degrees; consider a drop year only after a realistic review.')]
    else:
        tiers = [(10**9,'CUET results depend on subject, university and programme. Check each university\'s previous-year cut-offs on its official site.')]
    for lim, text in tiers:
        if rank <= lim: return text
    return tiers[-1][1]

# ---------- Hindi translations (used by t() on v12 pages and navigation) ----------
HI = {
 'Home':'होम','Career Compass':'करियर कम्पास','Roadmaps':'रोडमैप','Plans':'प्लान','About':'हमारे बारे में','Rewards':'रिवॉर्ड्स','My child':'मेरा बच्चा','Growth':'ग्रोथ',
 'Start here':'यहाँ से शुरू करें','Your next steps':'आपके अगले कदम','Step 1: Age & consent':'चरण 1: आयु और सहमति','Step 2: Assessment':'चरण 2: मूल्यांकन टेस्ट','Step 3: Enquiry form':'चरण 3: पूछताछ फ़ॉर्म',
 'Date of birth':'जन्म तिथि','Guardian name':'अभिभावक का नाम','Guardian email':'अभिभावक का ईमेल','Continue':'आगे बढ़ें','Start test':'टेस्ट शुरू करें','Submit answers':'उत्तर जमा करें','Your result':'आपका परिणाम',
 'Suggested stream':'सुझाया गया स्ट्रीम','Name':'नाम','Email':'ईमेल','Class':'कक्षा','Marks (%)':'अंक (%)','Entrance exam':'प्रवेश परीक्षा','Exam score / rank':'परीक्षा स्कोर / रैंक','Stream':'स्ट्रीम',
 'Colleges (up to 5)':'कॉलेज (अधिकतम 5)','Comment / doubt':'टिप्पणी / संदेह','Send enquiry':'पूछताछ भेजें','Choose a mentor':'मेंटर चुनें','Let CareerSathi allot a mentor':'CareerSathi को मेंटर चुनने दें',
 'Forgot password?':'पासवर्ड भूल गए?','Reset password':'पासवर्ड रीसेट करें','Practice':'अभ्यास','Blog':'ब्लॉग','Stories':'सफलता की कहानियाँ','Skip for now':'अभी छोड़ें','Take the test':'टेस्ट दें',
 'Mock interview':'मॉक इंटरव्यू','Scholarship finder':'छात्रवृत्ति खोजक','College predictor':'कॉलेज अनुमान','Daily check-in':'दैनिक चेक-इन','Streak':'लगातार दिन','Pay now':'अभी भुगतान करें',
 'Verify your email':'अपना ईमेल सत्यापित करें','Resend':'दोबारा भेजें','Language':'भाषा','Dark mode':'डार्क मोड','Open full report':'पूरी रिपोर्ट खोलें','My sessions':'मेरे सत्र','Join video call':'वीडियो कॉल से जुड़ें',
 'Ask Sathi':'साथी से पूछें','Send':'भेजें','Questions, answered.':'सवालों के जवाब।','Find a mentor':'मेंटर खोजें','Track progress':'प्रगति देखें','Certificate of completion':'पूर्णता प्रमाणपत्र',
}
# ---------- blog seeds (original short articles; general guidance) ----------
POSTS = [
 ('how-to-choose-stream-after-class-10','How to choose a stream after Class 10','A practical way to choose between PCM, PCB, Commerce and Arts without pressure.',
  "Choosing a stream feels like a life-or-death decision, but it is really a good first guess that you can adjust later.\n\nStart with three questions. What subjects do you enjoy even when no exam is near? Which subjects are you genuinely strong at? And what kind of work do you picture yourself doing?\n\nThen test the guess. Take a full-length assessment, read the roadmap of two or three careers you like, and talk to a student already in that stream.\n\nFinally check the practical side: eligibility rules for the exams you want, family budget and coaching access. Marks matter, but interest plus steady effort decides most outcomes. Whatever you choose, keep building skills outside the syllabus."),
 ('jee-vs-neet-vs-cuet','JEE, NEET or CUET: which entrance route fits you?','Three major entrance routes explained in simple words.',
  "JEE is the common route to engineering and technology programmes. NEET UG is the route to medical and allied-health degrees. CUET is used by many central and participating universities for undergraduate arts, science and commerce programmes.\n\nThe right exam depends on the career you want, not on which one is most popular. Read the official information bulletin, check the subjects required, and map the syllabus against your strengths.\n\nBuild a weekly study plan, give regular mock tests, and always keep a backup plan such as a good state exam or a skill-based degree."),
 ('how-to-build-a-student-portfolio','Build a simple portfolio in Class 11–12','Projects, certificates and proof of skills help for design, coding and many other fields.',
  "A portfolio is proof that you can do something, not only that you studied it.\n\nPick one skill and make three small things: a website or app, a short research project, a design set, or a content series. Write down what problem you solved and what you learned.\n\nKeep it on a free platform with a clear link. Update it every month. Colleges, mentors and internship providers value real work far more than a long list of certificates."),
 ('how-parents-can-support-career-choice','How parents can support a career decision','Listening, information and patience help more than pressure.',
  "Children choose better when they feel heard. Ask what they enjoy and why. Share information about options, including newer careers, instead of only familiar ones.\n\nAvoid comparing with cousins or neighbours. Talk about money honestly, including budget limits and education-loan options. Encourage them to speak to a mentor or professional.\n\nAgree on a plan with a review date, so a decision can be adjusted when new information appears."),
 ('study-abroad-timeline','A calm timeline for studying abroad','Start 12–18 months early and use only official sources.',
  "Start early: shortlist countries and courses, then check test requirements such as IELTS, TOEFL, SAT, GRE or GMAT.\n\nPrepare your documents and essays months before deadlines, and compare tuition, living cost, scholarships and loan terms.\n\nNever pay anyone for a guaranteed admission or visa. Apply through the university's official portal and follow the embassy's official instructions."),
 ('digital-skills-every-student-needs','Digital skills every student needs','Typing, spreadsheets, safe internet use and clear writing.',
  "Whatever career you choose, a few digital skills help: fast and accurate typing, spreadsheets for simple data work, clear email and document writing, and safe internet habits like strong passwords and checking sources.\n\nPractice with real tasks: plan a budget in a spreadsheet, write a polite email to a teacher, summarise an article in five lines. These small habits save time in college and at work."),
]

HI.update({'Explore': 'खोजें', 'Career tools': 'करियर टूल्स', 'Log in': 'लॉग इन', 'Get started': 'शुरू करें', 'Dashboard': 'डैशबोर्ड', 'My enquiries': 'मेरी पूछताछ',
           'My sessions': 'मेरे सत्र', 'Log out': 'लॉग आउट', 'Home': 'होम'})
