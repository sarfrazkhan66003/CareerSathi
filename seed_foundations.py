"""Append beginner-friendly fundamentals to existing tutorial courses, without touching accounts or bookings."""
from app import SessionLocal,Item
SUPPLEMENTS={
"Python Programming": """BONUS LESSON — PYTHON FOUNDATIONS WITH EXAMPLES
Python instructions execute from top to bottom. A variable names a value: age = 16. An integer such as 16 represents a whole number, while a string such as 'Bhopal' represents text. Python is case-sensitive: Age and age are different names. Use print(age) to show a value.

EXAMPLE: YOUR FIRST PROGRAM
name = 'Asha'
marks = [76, 85, 90]
average = sum(marks) / len(marks)
print(name, round(average, 1))
This prints Asha 83.7. A list stores multiple values; sum adds them; len counts items. Division returns a decimal. Change one mark and predict the new average before running the program.

CONDITIONS AND LOOPS
A condition chooses a branch: if average >= 60: print('Pass'). Indentation determines which instructions belong to a block. A for loop repeats an action: for mark in marks: print(mark). Functions package reusable logic: def total(values): return sum(values).

PRACTICE
1. Create variables for your city and class. 2. Make a list of five test scores. 3. Print the highest, lowest and average. 4. Write a function that returns the average. 5. What happens if the list is empty? Add a check before dividing. This is an introductory exercise, not a graded certificate.""",
"Web Development with HTML and CSS": """BONUS LESSON — HTML AND CSS STARTER EXAMPLE
HTML describes meaning and page structure. A heading uses <h1>CareerSathi</h1>, a paragraph uses <p>Learn with confidence.</p> and a navigation link uses <a href='/about'>About us</a>. CSS styles the elements. Semantic HTML makes information easier to navigate for browsers and assistive technology.

MINI PAGE EXERCISE
Create index.html and put a heading, an unordered list of your favorite subjects, a paragraph and a contact link inside the page body. In a separate style.css file, add body { font-family: sans-serif; max-width: 800px; margin: auto; } and h1 { color: #6252c4; }. Link the CSS from the HTML head.

ACCESSIBILITY BASICS
Use a label for every form input, descriptive link text, keyboard-visible focus and good contrast. Do not use images as the only way to show important text. Test your layout at mobile width.

PRACTICE
1. Add sections called About, Skills, Projects and Contact. 2. Add a responsive grid. 3. Navigate without a mouse. 4. Explain the difference between HTML structure and CSS presentation.""",
"SQL and Databases": """BONUS LESSON — SQL FROM FIRST PRINCIPLES
A relational database stores rows in tables. Imagine Students(student_id, name, city) and Courses(course_id, title). An integer ID uniquely identifies a student. Avoid storing the same facts repeatedly. A foreign key links a row to another table.

BASIC QUERIES
SELECT name, city FROM Students; retrieves two columns. SELECT name FROM Students WHERE city = 'Patna'; filters the rows. SELECT city, COUNT(*) FROM Students GROUP BY city; groups students by location. ORDER BY name sorts results.

SAFE INPUT
Never concatenate raw form values into SQL. Use prepared/parameterized queries. Back up data before changing tables.

PRACTICE
Design tables for schools, students and mentorship bookings, with primary and foreign keys. Write one filtering query, one grouped count and a query that joins bookings to student names. Draw a diagram of how the tables connect."""
}
with SessionLocal() as db:
    changed=0
    for title,extra in SUPPLEMENTS.items():
        items=db.query(Item).filter(Item.kind=='course',Item.title.ilike(title+'%')).all()
        for item in items:
            if 'BONUS LESSON —' in (item.description or ''):continue
            item.description=(item.description or '')+'\n\n'+extra
            changed+=1
    db.commit()
print(f'Enhanced {changed} course(s); accounts, bookings and other guides preserved.')
