#!/usr/bin/env python3
"""
Set simple, known demo passwords on every account and rewrite CREDENTIALS.txt
so the file always matches what is actually stored in the database.

Run after seeding:
    python set_demo_passwords.py

Check that CREDENTIALS.txt is truthful without changing anything:
    python set_demo_passwords.py --verify

Passwords set:
    admin            Admin123!
    hod              Hod123!
    teachers T001-6  Teacher123!
    students 101-150 Student123!
"""
import sys

from credentials import verify_credentials_file, write_credentials_file
from db import get_db, init_db

# Imported lazily so a missing PORTAL_FERNET_KEY does not block password resets.
from security import hash_password

ADMIN_PASSWORD = "Admin123!"
HOD_PASSWORD = "Hod123!"
TEACHER_PASSWORD = "Teacher123!"
STUDENT_PASSWORD = "Student123!"

ROLE_PASSWORDS = {
    "admin": ADMIN_PASSWORD,
    "hod": HOD_PASSWORD,
    "teacher": TEACHER_PASSWORD,
    "student": STUDENT_PASSWORD,
}


def verify():
    ok, problems = verify_credentials_file()
    if ok:
        print("CREDENTIALS.txt matches the database: every account, every password.")
        return 0
    print(f"CREDENTIALS.txt does NOT match the database ({len(problems)} problem(s)):")
    for problem in problems:
        print(f"  - {problem}")
    print("\nFix with: python set_demo_passwords.py")
    return 1


def main():
    init_db()
    conn = get_db()
    try:
        users = conn.execute(
            "SELECT username, role FROM users ORDER BY role, username"
        ).fetchall()
        if not users:
            print("No users found. Run 'python seed.py' first.")
            return 1

        passwords = {}
        for user in users:
            role = user["role"]
            password = ROLE_PASSWORDS.get(role, STUDENT_PASSWORD)
            passwords[user["username"]] = password

            conn.execute(
                """UPDATE users
                      SET password_hash = ?,
                          failed_attempts = 0,
                          locked_until = NULL
                   WHERE username = ?""",
                (hash_password(password), user["username"]),
            )
        conn.commit()

        path = write_credentials_file(passwords, conn=conn)
    finally:
        conn.close()

    print(f"Updated {len(users)} accounts.")
    print(f"CREDENTIALS.txt rewritten at {path}")
    print("")
    print("  admin   / Admin123!")
    print("  hod     / Hod123!")
    print("  T001-6  / Teacher123!")
    print("  101-150 / Student123!")

    ok, problems = verify_credentials_file(path)
    if not ok:  # pragma: no cover - would mean the write above is broken
        print("\nWarning: the rewritten file failed its own check:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    return 0


if __name__ == "__main__":
    if "--verify" in sys.argv[1:]:
        sys.exit(verify())
    sys.exit(main())
