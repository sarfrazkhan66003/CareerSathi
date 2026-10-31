"""Idempotent free educational lesson seeder. Does not delete or modify user data."""
from app import SessionLocal, Item

TOPICS = [
('Python Programming','Technology','variables, strings, numbers, lists and dictionaries','write a simple expense tracker that totals weekly spending','use input validation and clear variable names','Python.org documentation, beginner tutorial'),
('Web Development with HTML and CSS','Technology','semantic HTML, layouts, selectors and responsive design','make an accessible portfolio with a navigation bar and contact section','test on mobile and add labels for every input','MDN Web Docs: Learn Web Development'),
('JavaScript Fundamentals','Technology','functions, arrays, objects and DOM events','build a quiz that scores answers and displays feedback','avoid unsafe HTML injection; use textContent for user text','MDN JavaScript Guide'),
('SQL and Databases','Technology','tables, keys, SELECT, JOIN and aggregation','design a small library database and query overdue books','use parameterized queries, not string-built SQL','PostgreSQL official tutorial'),
('Data Science Foundations','Technology','data collection, cleaning, grouping and visualization','analyze monthly rainfall or school attendance with a small CSV','record assumptions and do not infer causation from correlation','Kaggle Learn and Python pandas documentation'),
('Artificial Intelligence Basics','Technology','training data, classification, evaluation and bias','compare a rules-based recommendation with a simple trained model','keep humans in the loop for high-stakes decisions','Google Machine Learning Crash Course'),
('Cybersecurity Essentials','Technology','passwords, phishing, privacy and software updates','create a personal account-security checklist','never share OTPs and always report suspicious messages','CERT-In cyber safety guidance'),
('Computer Networks','Technology','IP addressing, DNS, HTTP and network troubleshooting','draw what happens when a browser opens a website','distinguish HTTPS encryption from website trustworthiness','Cloudflare Learning Center'),
('Git and GitHub Basics','Technology','repositories, commits, branches and collaboration','track revisions of a small personal website','never commit passwords or API secrets','Pro Git book'),
('Excel and Google Sheets','Business','formulas, sorting, filters, charts and pivot summaries','create a monthly budget with SUMIF and conditional formatting','check formulas before sharing financial reports','Microsoft Excel training'),
('Mathematics for Careers','STEM','percentages, ratios, algebra, probability and graphs','calculate loan interest and plot a small trend','show units and write each calculation step','NCERT Mathematics textbooks'),
('Physics for Everyday Life','STEM','motion, energy, electricity and experimental measurement','measure how a toy car travels down a ramp','never experiment with mains electricity','NCERT Physics textbooks'),
('Chemistry Fundamentals','STEM','atoms, bonding, reactions and safe laboratory practice','balance five reactions and explain their conservation laws','never mix unknown chemicals','NCERT Chemistry textbooks'),
('Biology and Human Health','STEM','cells, genetics, ecology and evidence-based health literacy','draw a cell and trace how traits are inherited','health information is educational, not medical advice','NCERT Biology textbooks'),
('Spoken English & Communication','Soft Skills','active listening, introductions, pronunciation and clear messages','record a two-minute self-introduction and critique it','favor clarity over accent imitation','British Council LearnEnglish'),
('Public Speaking and Presentations','Soft Skills','audience analysis, structure, storytelling and delivery','present a three-minute explanation of your chosen career','cite factual claims and rehearse aloud','Toastmasters public speaking resources'),
('Critical Thinking & Problem Solving','Soft Skills','evidence, assumptions, trade-offs and logical fallacies','compare two college options using a weighted decision table','check multiple independent sources','Foundation for Critical Thinking resources'),
('Time Management & Study Skills','Soft Skills','study planning, spaced practice and active recall','make a one-week study calendar with revision blocks','avoid burnout and include breaks and sleep','Learning Scientists study strategies'),
('Financial Literacy for Students','Finance','budgeting, saving, interest, risk and digital payments','make a budget with needs, wants, savings and emergency money','never share UPI PIN or OTP and understand financial risks','RBI financial education'),
('Entrepreneurship and Startups','Business','problem discovery, value propositions, pricing and customer interviews','interview five users and draft a lean business canvas','validate assumptions before spending money','Startup India learning resources'),
('Digital Marketing & SEO','Business','audience research, helpful content, keywords and analytics','write a topic cluster for an educational blog','avoid fake testimonials and misleading statistics','Google Search Central SEO Starter Guide'),
('Resume Writing & Interview Skills','Careers','achievement bullets, role research, STAR stories and follow-ups','write one-page resume and practice five mock interview questions','do not invent credentials or employers','National Career Service India'),
('Career Discovery After Class 10','Careers','stream selection, interests, aptitude and course pathways','compare science, commerce, humanities and vocational choices','no stream guarantees a specific salary or job','NCERT and official board guidance'),
('Career Discovery After Class 12','Careers','entrance exams, eligibility, fees, scholarships and college fit','make a shortlist with admission criteria and total costs','check official admission portals for current dates','National Career Service India'),
('Engineering Career Roadmap','Careers','engineering branches, mathematics foundations, projects and internships','compare computer science, civil, mechanical and electronics curricula','accreditation, placements and fees require institution verification','AICTE and official college websites'),
('Medical and Allied Health Careers','Careers','healthcare roles, eligibility, accreditation and practical training','compare medicine, nursing, physiotherapy and allied health','only official regulators can confirm professional eligibility','NMC and official regulator websites'),
('Law and Civil Services Roadmap','Careers','legal education, public service, exams and ethical reasoning','map eligibility routes and list three public-service roles','confirm exam syllabi from the conducting authority','UPSC and Bar Council official sites'),
('Graphic Design and UI/UX','Creative','visual hierarchy, contrast, research and usability testing','redesign a school timetable or sign-up form','check accessibility and seek consent before using photos','Nielsen Norman Group introductory articles'),
('Psychology and Counseling Careers','Careers','research methods, ethics, psychology branches and professional training','compare academic psychology with regulated practice roles','do not diagnose classmates; verify licensing requirements','official university programmes and relevant regulators'),
('Environmental Science & Sustainability','STEM','climate, biodiversity, waste, energy and environmental indicators','audit classroom waste and propose one measurable improvement','distinguish local weather from long-term climate trends','UNEP learning resources'),
('Robotics and Electronics Basics','Technology','sensors, control, circuits and prototyping','simulate an LED circuit or build a battery-powered sensor demo','use only safe low-voltage components with supervision','Arduino official tutorials'),
('Scholarships & Education Planning','Careers','scholarship criteria, budgeting, deadlines and document preparation','prepare a scholarship application checklist','never pay unverified agents for guaranteed scholarships','National Scholarship Portal'),
]

def build_lesson(name,category,ideas,practice,safety,reference):
    return '\n\n'.join([
      'LESSON 1 — WHAT YOU WILL LEARN\n'+name+' is a foundational learning pathway for curious students. This self-study lesson introduces '+ideas+'. By the end, you should be able to explain the core ideas in your own words, apply them to a small task and identify the next skills you need.',
      'LESSON 2 — UNDERSTAND THE FOUNDATIONS\nStart by writing down what you already know about '+name.lower()+'. Break the subject into small parts: '+ideas+'. For each part, define the term, write one real-world example and explain why it matters. A good explanation answers: what is it, when would I use it, what could go wrong, and how would I check my work?',
      'LESSON 3 — LEARN BY APPLYING\nTry this practical activity: '+practice+'. First describe the result you want. List the steps, tools and information needed. Complete a first draft, test it with at least two examples, then revise one weakness. Save both the first version and your improved version so you can see your progress.',
      'LESSON 4 — EXAMPLE AND REFLECTION\nImagine two learners: A memorizes definitions, while B applies the same ideas to a project and explains their choices. Both may pass a quiz, but B also has evidence of problem solving. After each study session, answer three questions: What can I explain without notes? What is still confusing? What small experiment or example could test my understanding?',
      'LESSON 5 — PRACTICE EXERCISES\n1. Define three important terms from this topic in plain language.\n2. Give one local or everyday example for each term.\n3. Complete this task: '+practice+'.\n4. Write 150 words describing what worked, what failed and what you would change.\n5. Teach the idea to a friend or parent and ask them one question to check understanding.',
      'LESSON 6 — SAFETY, ETHICS AND NEXT STEPS\n'+safety+'. Do not assume completing this guide is equivalent to an accredited qualification or professional training. For deeper study, consult: '+reference+'. Check current eligibility, fees, exams and course information through official sources. Suggested routine: study for 30 minutes, practice for 30 minutes, and review your notes on the next day and again after one week.'
    ])

with SessionLocal() as db:
    existing={(v.title,v.kind) for v in db.query(Item.title,Item.kind).all()}
    total=0
    for name,cat,ideas,practice,safety,reference in TOPICS:
        title=name+' — Free Learning Notes'
        if (title,'course') in existing:continue
        db.add(Item(kind='course',title=title,subtitle='Free self-study guide · 6 reading lessons',description=build_lesson(name,cat,ideas,practice,safety,reference),category=cat,location='Online',price=0,published=True))
        total+=1
    db.commit()
print(f'Added {total} detailed free learning guides. Existing entries preserved.')
