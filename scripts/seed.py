# university_portal/scripts/seed.py
"""
Seed the university database with departments, teachers, students, courses,
enrolments, and user accounts. Writes CREDENTIALS.txt.
Safe to run twice: clears users/students/teachers/courses/enrolments and re-seeds.
"""
import os
import sys
import random

# Running this file as a script puts scripts/ on sys.path, not the project root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from portal.db import get_db, init_db, using_mysql
from portal.credentials import write_credentials_file as write_credentials
from portal.security import hash_password, generate_random_password, encrypt_national_id

random.seed(42)

# MySQL spells "insert this row unless it is already there" differently.
_INSERT_IGNORE = "INSERT IGNORE" if using_mysql() else "INSERT OR IGNORE"

# Cleared on every seed run, children before parents.
_DATA_TABLES = (
    "enrollments",
    "users",
    "courses",
    "students",
    "teachers",
    "audit_log",
    "login_history",
)


def _reset_data(conn):
    """Empty the data tables and restart their ids so a re-seed is reproducible.

    The audit trail and login history go too: their target ids would name
    different people once the ids restart. Departments are kept, because the
    seed row for them is idempotent and courses/users point at them.
    """
    if using_mysql():
        # TRUNCATE resets AUTO_INCREMENT; foreign keys must be lifted first
        # because these tables reference each other.
        conn.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in _DATA_TABLES:
            conn.execute(f"TRUNCATE TABLE {table}")
        conn.execute("SET FOREIGN_KEY_CHECKS = 1")
        return

    for table in _DATA_TABLES:
        conn.execute(f"DELETE FROM {table}")
    # Restart the AUTOINCREMENT counters so ids are 1..N on every seed run.
    # Without this, ids keep growing and demo links such as /admin/student/1
    # stop resolving after a re-seed.
    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name IN "
        "('teachers','students','courses','users','audit_log','login_history')"
    )
    conn.commit()

DEPARTMENTS = [
    ("CSE", "Computer Science and Engineering"),
    ("ECE", "Electronics and Communication"),
    ("ME",  "Mechanical Engineering"),
    ("CE",  "Civil Engineering"),
]

TEACHERS = [
    ("T001", "Mr. Sharma",   "sharma@cse.univ.edu", "9811100001", "CSE"),
    ("T002", "Ms. Gupta",    "gupta@cse.univ.edu",  "9722200002", "CSE"),
    ("T003", "Mr. Verma",    "verma@cse.univ.edu",  "9633300003", "CSE"),
    ("T004", "Dr. Rao",      "rao@ece.univ.edu",    "9544400004", "ECE"),
    ("T005", "Dr. Kumar",    "kumar@me.univ.edu",   "9455500005", "ME"),
    ("T006", "Dr. Mishra",   "mishra@ce.univ.edu",  "9366600006", "CE"),
]

STUDENT_NAMES_BY_ROLL = {
    101: ("Aman Verma",  "CSE"),
    102: ("Riya Kapoor", "CSE"),
    103: ("Karan Mehta", "CSE"),
    104: ("Neha Joshi",  "ECE"),
    105: ("Simran Kaur", "ECE"),
}

EXTRA_STUDENTS = [
    ("Arjun Singh", "CSE"), ("Priya Sharma", "CSE"), ("Vikram Patel", "CSE"),
    ("Ananya Gupta", "CSE"), ("Rohan Mehta", "CSE"), ("Sneha Reddy", "CSE"),
    ("Karthik Nair", "CSE"), ("Divya Iyer", "CSE"), ("Amit Joshi", "CSE"),
    ("Pooja Banerjee", "CSE"), ("Siddharth Rao", "CSE"), ("Meera Krishnan", "CSE"),
    ("Rakshith Gowda", "CSE"), ("Trisha Menon", "CSE"), ("Nikhil Desai", "CSE"),
    ("Pallavi Saxena", "ECE"), ("Himanshu Verma", "ECE"), ("Huma Parveen", "ECE"),
    ("Ishaan Banerjee", "ECE"), ("Kavya Subramaniam", "ECE"), ("Mohit Agarwal", "ECE"),
    ("Nidhi Chandak", "ECE"), ("Omkar Kulkarni", "ECE"), ("Ritu Das", "ECE"),
    ("Sagar Deshmukh", "ECE"), ("Tanvi Joshi", "ECE"), ("Utkarsh Mishra", "ECE"),
    ("Varun Gupta", "ME"), ("Shruti Pandey", "ME"), ("Aakash Yadav", "ME"),
    ("Bharti Singh", "ME"), ("Chetan Joshi", "ME"), ("Devika Nair", "ME"),
    ("Faizan Khan", "ME"), ("Gaurav Mishra", "ME"), ("Hemlata Patel", "ME"),
    ("Irfan Qureshi", "ME"), ("Jaya Lakra", "ME"), ("Kailash Barman", "ME"),
    ("Lara James", "ME"), ("Mohan Rao", "ME"), ("Rajesh Thakur", "ME"),
    ("Abhay Tiwari", "CE"), ("Binita Shah", "CE"), ("Chandra Kant", "CE"),
]

COURSES = [
    ("C101", "DBMS",             4, "T001", "CSE"),
    ("C102", "Java",             4, "T002", "CSE"),
    ("C103", "Python",           4, "T003", "CSE"),
    ("C104", "Circuits",         3, "T004", "ECE"),
    ("C105", "AI Basics",        3, "T005", "ME"),
    ("C106", "Data Structures",  4, "T001", "CSE"),
    ("C107", "Signals",          3, "T004", "ECE"),
    ("C108", "Mechanics",        4, "T005", "ME"),
    ("C109", "Fluid Mechanics",  3, "T006", "CE"),
    ("C110", "Statics",          4, "T006", "CE"),
    ("C111", "Algorithms",       4, "T003", "CSE"),
    ("C112", "Electronics",      3, "T004", "ECE"),
]


def email_for_student(roll_no: int, branch_code: str) -> str:
    return f"student{roll_no}@{branch_code.lower()}.univ.edu"


def national_id_for(roll_no: int) -> str:
    return f"1234{roll_no:05d}{random.randint(1000,9999):04d}"


def seed(write_credentials_file=True):
    """Populate the database.

    Set write_credentials_file=False when seeding a throwaway database (tests,
    smoke test) so the real CREDENTIALS.txt is not overwritten.
    """
    init_db()

    conn = get_db()
    try:
        _reset_data(conn)

        dept_map = {}
        for code, name in DEPARTMENTS:
            conn.execute(
                f"{_INSERT_IGNORE} INTO departments (code, name) VALUES (?,?)",
                (code, name),
            )
            row = conn.execute("SELECT id FROM departments WHERE code=?", (code,)).fetchone()
            dept_map[code] = row["id"]

        teacher_map = {}
        for staff_code, name, email, phone, dept_code in TEACHERS:
            conn.execute(
                f"{_INSERT_IGNORE} INTO teachers (staff_code, name, email, phone, department_id) VALUES (?,?,?,?,?)",
                (staff_code, name, email, phone, dept_map[dept_code]),
            )
            row = conn.execute("SELECT id FROM teachers WHERE staff_code=?", (staff_code,)).fetchone()
            teacher_map[staff_code] = row["id"]

        student_map = {}
        for roll in range(101, 151):
            if roll <= 105:
                name, dept_code = STUDENT_NAMES_BY_ROLL[roll]
            else:
                idx = roll - 106
                name, dept_code = EXTRA_STUDENTS[idx]
            email = email_for_student(roll, dept_code)
            national_id = national_id_for(roll)
            encrypted = encrypt_national_id(national_id)
            conn.execute(
                f"{_INSERT_IGNORE} INTO students (roll_no, name, email, department_id, national_id_enc) VALUES (?,?,?,?,?)",
                (str(roll), name, email, dept_map[dept_code], encrypted),
            )
            row = conn.execute("SELECT id FROM students WHERE roll_no=?", (str(roll),)).fetchone()
            student_map[str(roll)] = row["id"]

        course_map = {}
        for code, title, credits, teacher_code, dept_code in COURSES:
            conn.execute(
                f"{_INSERT_IGNORE} INTO courses (code, title, credits, teacher_id, department_id) VALUES (?,?,?,?,?)",
                (code, title, credits, teacher_map[teacher_code], dept_map[dept_code]),
            )
            row = conn.execute("SELECT id FROM courses WHERE code=?", (code,)).fetchone()
            course_map[code] = row["id"]

        conn.execute("DELETE FROM enrollments")

        # Exact enrolments and marks from the Unit C practical (Experiment 1).
        # These five students' rows must match the lab sheet.
        PRACTICAL_ENROLMENTS = [
            ("101", "C101", 78),
            ("101", "C102", 82),
            ("102", "C101", 91),
            ("102", "C103", 88),
            ("103", "C102", 69),
            ("104", "C104", 74),
            ("104", "C101", 85),
            ("105", "C104", 80),
        ]
        used = {}
        for roll_str, course_code, marks in PRACTICAL_ENROLMENTS:
            conn.execute(
                "INSERT INTO enrollments (student_id, course_id, marks) VALUES (?,?,?)",
                (student_map[roll_str], course_map[course_code], marks),
            )
            used.setdefault(roll_str, set()).add(course_map[course_code])

        # Every other enrolment is chosen so each student ends with 3-5 courses.
        all_course_ids = list(course_map.values())
        for roll_str, student_id in student_map.items():
            already = used.get(roll_str, set())
            target = random.randint(3, 5)
            remaining = [cid for cid in all_course_ids if cid not in already]
            extra = max(0, target - len(already))
            for cid in random.sample(remaining, min(extra, len(remaining))):
                marks = None
                if random.random() < 0.7:
                    marks = random.randint(0, 100)
                conn.execute(
                    "INSERT INTO enrollments (student_id, course_id, marks) VALUES (?,?,?)",
                    (student_id, cid, marks),
                )

        conn.execute("DELETE FROM users")

        # Generate passwords first
        admin_pwd = generate_random_password()
        hod_pwd = generate_random_password()
        teacher_passwords = {}
        for sc, *_ in TEACHERS:
            teacher_passwords[sc] = generate_random_password()
        student_passwords = {}
        for r in range(101, 151):
            student_passwords[str(r)] = generate_random_password()

        def create_user(username, pwd, role, student_id=None, teacher_id=None):
            h = hash_password(pwd)
            conn.execute(
                "INSERT INTO users (username, password_hash, role, student_id, teacher_id, is_active) VALUES (?,?,?,?,?,1)",
                (username, h, role, student_id, teacher_id),
            )
            return conn.execute(
                "SELECT id FROM users WHERE username=?", (username,)
            ).fetchone()["id"]

        admin_user_id = create_user("admin", admin_pwd, "admin")
        hod_user_id = create_user("hod", hod_pwd, "hod")

        for sc, *_ in TEACHERS:
            create_user(sc, teacher_passwords[sc], "teacher", teacher_id=teacher_map[sc])

        for roll_str, student_id in student_map.items():
            create_user(roll_str, student_passwords[roll_str], "student", student_id=student_id)

        conn.commit()
    finally:
        conn.close()

    if write_credentials_file:
        passwords = {"admin": admin_pwd, "hod": hod_pwd}
        passwords.update(teacher_passwords)
        passwords.update(student_passwords)
        path = write_credentials(passwords)
        print(f"CREDENTIALS.txt written to {path}")


if __name__ == "__main__":
    seed()
    print("Seed complete.")
    print("Next: python scripts/set_demo_passwords.py  (sets the simple demo passwords)")
