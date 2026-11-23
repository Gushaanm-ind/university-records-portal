#!/usr/bin/env python3
"""
tools/smoke_test.py — logs in as admin, HOD, one teacher, and one student
using the seeded accounts, visits every page, prints a status table, and
exits non-zero on any unexpected status.
"""
import os
import sys
import uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set env vars for testing
if not os.environ.get("PORTAL_FERNET_KEY"):
    from cryptography.fernet import Fernet
    os.environ["PORTAL_FERNET_KEY"] = Fernet.generate_key().decode()
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = uuid.uuid4().hex

# Override DB to temp — only meaningful for SQLite. MySQL mode uses the
# configured server instead, which this script reseeds and rewrites passwords
# for, so it refuses to touch MySQL unless SMOKE_ALLOW_MYSQL=1 is set.
import config
import tempfile
original_db = config.Config.DATABASE
db_path = os.path.join(tempfile.gettempdir(), f"smoke_{uuid.uuid4().hex}.db")
if (os.environ.get("DB_ENGINE") or "sqlite").strip().lower() == "mysql":
    if os.environ.get("SMOKE_ALLOW_MYSQL") != "1":
        sys.exit(
            "Refusing to run: DB_ENGINE=mysql, and this script reseeds and changes "
            "passwords. Set SMOKE_ALLOW_MYSQL=1 to run it against "
            f"{os.environ.get('MYSQL_DATABASE', 'university_db')}, then restore the "
            "demo passwords with: python set_demo_passwords.py"
        )
    print(f"Running against MySQL: {os.environ.get('MYSQL_DATABASE', 'university_db')} "
          "(this reseeds the database)\n")
else:
    config.Config.DATABASE = db_path

from app import create_app
from seed import seed
from db import get_db
from security import hash_password

# Seed the database
seed(write_credentials_file=False)

# Set a known password "testpass123!" for the test users we need
conn = get_db()
try:
    h = hash_password("testpass123!")
    conn.execute("UPDATE users SET password_hash=? WHERE username=?", (h, "admin"))
    conn.execute("UPDATE users SET password_hash=? WHERE username=?", (h, "hod"))
    conn.execute("UPDATE users SET password_hash=? WHERE username=?", (h, "T001"))
    conn.execute("UPDATE users SET password_hash=? WHERE username=?", (h, "101"))
    conn.commit()
finally:
    conn.close()

app = create_app()
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False

client = app.test_client()


def login(username):
    return client.post("/login", data={"username": username, "password": "testpass123!"},
                       follow_redirects=True)


def check(role, path, method="GET", expected=200):
    if method == "GET":
        resp = client.get(path)
    else:
        resp = client.post(path)
    status = resp.status_code
    ok = status == expected
    if not ok:
        print(f"  FAIL: {method} {path} -> {status} (expected {expected})")
    return ok, status


def run_smoke(role, username, pages):
    print(f"\n{'='*60}")
    print(f"Smoke test: {role} ({username})")
    print(f"{'='*60}")

    login(username)

    all_ok = True
    for path, method, expected in pages:
        ok, status = check(role, path, method, expected)
        if not ok:
            all_ok = False
    return all_ok


from repositories.objects import get_all_students, get_all_courses, get_all_teachers

_first_student = get_all_students()[0]["id"]
_first_teacher = get_all_teachers()[0]["id"]
_first_course = get_all_courses()[0]["id"]

admin_pages = [
    ("/", "GET", 302),
    ("/admin", "GET", 200),
    ("/admin/students", "GET", 200),
    (f"/admin/student/{_first_student}", "GET", 200),
    ("/admin/teachers", "GET", 200),
    (f"/admin/teacher/{_first_teacher}", "GET", 200),
    ("/admin/courses", "GET", 200),
    (f"/admin/course/{_first_course}", "GET", 200),
    ("/admin/users", "GET", 200),
    ("/admin/create-user", "GET", 200),
    ("/admin/activity", "GET", 200),
    ("/admin/login-history", "GET", 200),
    ("/admin/reports", "GET", 200),
    ("/admin/profile", "GET", 200),
]

hod_pages = [
    ("/", "GET", 302),
    ("/hod", "GET", 200),
    ("/hod/students", "GET", 200),
    (f"/hod/student/{_first_student}", "GET", 200),
    ("/hod/teachers", "GET", 200),
    (f"/hod/teacher/{_first_teacher}", "GET", 200),
    ("/hod/courses", "GET", 200),
    (f"/hod/course/{_first_course}", "GET", 200),
    ("/hod/login-history", "GET", 200),
    ("/admin/reports", "GET", 200),
]

teacher_pages = [
    ("/", "GET", 302),
    ("/teacher", "GET", 200),
    ("/teacher/students", "GET", 200),
    (f"/teacher/student/{_first_student}", "GET", 200),
    ("/teacher/courses", "GET", 200),
    (f"/teacher/course/{_first_course}", "GET", 200),
]

_other_student = get_all_students()[1]["id"]
student_pages = [
    ("/", "GET", 302),
    ("/student", "GET", 200),
    (f"/student/{_first_student}", "GET", 200),
    (f"/student/{_other_student}", "GET", 403),
]


def main():
    results = {}

    results["admin"] = run_smoke("admin", "admin", admin_pages)
    results["hod"] = run_smoke("hod", "hod", hod_pages)
    results["teacher"] = run_smoke("teacher", "T001", teacher_pages)
    results["student"] = run_smoke("student", "101", student_pages)

    # Summary table
    print(f"\n{'='*60}")
    print("SMOKE TEST SUMMARY")
    print(f"{'='*60}")
    print(f"{'Role':<12} {'Status':<10} {'Pages':<10}")
    print(f"{'-'*12} {'-'*10} {'-'*10}")

    overall_ok = True
    for role, ok in results.items():
        status_str = "PASS" if ok else "FAIL"
        print(f"{role:<12} {status_str:<10} {'✓' if ok else '✗':<10}")
        if not ok:
            overall_ok = False

    print(f"{'='*60}")

    if not overall_ok:
        print("\nSMOKE TEST FAILED")
        sys.exit(1)
    else:
        print("\nSMOKE TEST PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
