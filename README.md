# University Database Portal

A role-based web application for managing a university database (students, teachers, departments, courses, enrolments and marks), built with Flask, SQLite, and Jinja2.

## Source material

Built from the DBMS practicals:

- **DBMS_Practical_Unit_C_25GAX303.pdf** — Database Design Concepts, 11 experiments:
  1. Unnormalized table and the three anomalies
  2. Finding functional dependencies with SQL
  3. First Normal Form (1NF)
  4. Second Normal Form (2NF)
  5. Third Normal Form (3NF)
  6. Boyce-Codd Normal Form (BCNF)
  7. Lossless and lossy join decomposition
  8. Dependency preservation
  9. Multivalued dependency and 4NF
  10. Join dependency and 5NF
  11. Denormalization

  The portal implements the 3NF schema from Experiment 5 (experiment 2's
  functional dependencies are enforced by the keys) and uses the manual's own
  sample data: students Aman Verma (101), Riya Kapoor (102), Karan Mehta (103),
  Neha Joshi (104), Simran Kaur (105); courses C101 DBMS (Mr. Sharma), C102 Java
  (Ms. Gupta), C103 Python (Mr. Verma), C104 Circuits (Dr. Rao); teachers also
  include Dr. Kumar and Dr. Mishra; departments CSE (Dr. Singh) and ECE
  (Dr. Nair), extended with ME and CE so the portal has more than one branch to
  filter by. Experiments 6–11 are analysis exercises on separate demo tables
  (`class_allocation`, `teacher_course`, `student_teacher`, `class_room`), so
  they are documented in the practical file rather than modelled in the app.
- **DBMS_Practicals_24GAX303.pdf** — Practical 1 (JOINs) and Practical 2 (aggregates, GROUP BY, HAVING, subqueries). These query patterns are implemented in the Reports page (average marks per department, students above the average, second highest mark).

The company_db employee tables from Practical 1 and 2 are reference only and are not included in the university data.

**New here?** `GUIDE.md` is the step-by-step version: how to run it, how to start the app, and how to print the database tables in the terminal. This file is the reference documentation.

## Setup

```bash
cd university_portal
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set the required environment variables:

```bash
export PORTAL_FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

Keep the same `PORTAL_FERNET_KEY` for the life of a database: it encrypts
`students.national_id_enc`, so a new key cannot decrypt rows written with the
old one. Re-seed after changing the key.

Seed the database and set the simple demo passwords:

```bash
python seed.py
python set_demo_passwords.py
```

`seed.py` creates the data and writes `CREDENTIALS.txt` with random passwords.
`set_demo_passwords.py` replaces them with the fixed demo passwords below and
rewrites `CREDENTIALS.txt`, so the file always matches the database.

Look at the tables without leaving the terminal:

```bash
python tools/show_tables.py              # department, teacher, student, course, enrollment
python tools/show_tables.py --list       # every table and its row count
python tools/show_tables.py --sql "SELECT * FROM courses"
```### Using MySQL instead of SQLite

The portal ships with SQLite as the default because it needs no server. It can
also run against a real MySQL server with no code changes: create the database,
set five environment variables, and re-run the same seed script.

```sql
-- once, as a MySQL administrator
CREATE DATABASE university_db CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'portal'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT ALL PRIVILEGES ON university_db.* TO 'portal'@'localhost';
```

`utf8mb4_bin` matters: MySQL's default collation ignores case, which would let
`Admin` log in as `admin`.

```bash
export DB_ENGINE=mysql
export MYSQL_USER=portal
export MYSQL_PASSWORD='choose-a-password'
export MYSQL_HOST=127.0.0.1      # defaults
export MYSQL_PORT=3306
export MYSQL_DATABASE=university_db

export SECRET_KEY="dev-secret-change-me"
export PORTAL_FERNET_KEY="Jz5EWERS6MnfMqH3r5LB5bnxb2vEtvK5Wcmut8Q8ncU="

python seed.py                          # creates schema_mysql.sql tables + sample data
python set_demo_passwords.py --verify    # CREDENTIALS.txt now matches MySQL
PORT=5055 python app.py                 # same URL: http://127.0.0.1:5055/login
```

Seeing the tables is the same command as before:

```bash
python tools/show_tables.py --list
python tools/show_tables.py --table users --limit 5
python tools/show_tables.py --sql "SELECT role, COUNT(*) FROM users GROUP BY role"
```

Unset `DB_ENGINE` (or set it to `sqlite`) to go back to the file database. The
two engines hold the same tables; `university.db` is not deleted or modified
while MySQL mode is active. `db.py` wraps the PyMySQL connection so the rest of
the application keeps using sqlite3-style `conn.execute("… ?", params)` calls.

`schema_mysql.sql` differs from `schema.sql` only where MySQL requires it:
`AUTO_INCREMENT`, `VARCHAR` instead of unbounded `TEXT` for unique/indexed
columns, `utf8mb4_bin` collation so usernames and emails stay case-sensitive
like SQLite, and timestamp columns kept as `VARCHAR(32)` because the app stores
ISO strings such as `2026-11-04T12:01:52.219134`.

Check the file against the database at any time:

```bash
python set_demo_passwords.py --verify
```

Run the application:

```bash
python app.py
```

Open http://127.0.0.1:5000/login.

### Demo credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin123!` |
| HOD | `hod` | `Hod123!` |
| Teacher | `T001` … `T006` | `Teacher123!` |
| Student | `101` … `150` | `Student123!` |

If a page ever says "Your form expired", reload it and submit again — the CSRF
token belongs to the session that rendered the form.

## Running tests

pytest is pinned in `requirements.txt`, so a fresh install is enough:

```bash
pytest -q
```

The suite has **220 tests**: authentication and lockout, CSRF, session timeout,
role permissions (one test per role/URL/method combination), edit and audit
trails, reports, sensitive-field reveal, credential-file consistency, and the
practical's sample data.

Run the smoke test (logs in as all four roles against a temporary database):

```bash
python tools/smoke_test.py
```

Each test gets its own freshly seeded copy of the database, so tests are
independent and repeatable. Confirm stability with:

```bash
for i in 1 2 3; do echo "=== Run $i ==="; pytest -q; done
python seed.py && python set_demo_passwords.py && pytest -q
```

## Roles and permissions

| Action | Student | Teacher | HOD | Admin |
|---|---|---|---|---|
| Own profile, own courses, own marks | Yes | Yes | Yes | Yes |
| View every student's profile and marks | No | Yes (read only) | Yes | Yes |
| View every teacher | No | Yes (read only) | Yes | Yes |
| Edit a student (name, email, branch, marks) | No | No | Yes | Yes |
| Edit a teacher (name, email, phone, branch) | No | No | Yes | Yes |
| Edit own name or email | No | No | Yes | Yes |
| Change own password | Yes | Yes | Yes | Yes |
| Create, deactivate, reset password of users | No | No | No | Yes |
| View activity log | No | No | No | Yes |
| View login history | Own only | Own only | All except admin | All |
| View admin accounts | No | No | No | Yes |

Rules:

- A student can never edit anything, including their own name or marks. A student requesting another student's URL gets 403.
- A teacher can see all students but cannot edit them.
- The HOD can edit students and teachers, but cannot see or change admin accounts, cannot create users, and cannot see the activity log.
- Every route and every POST checks the role and, for students, that the target record belongs to the logged-in user.
- Tampered URLs and IDs must return 403 and write an `ACCESS_DENIED` audit row.

## Pages

1. Login and logout
2. Dashboard: role-specific counts and quick links
3. Students list: search by name or roll number, filter by branch. Visible to teacher, HOD, admin.
4. Student detail: profile, enrolments, marks. Edit form for HOD and admin. National ID visible only to admin, with a "Reveal" button that is logged.
5. Teachers list and teacher detail. Edit for HOD and admin.
6. Courses list and course detail. Marks entry for HOD and admin. Read only for teacher and student (student sees only own marks).
7. My profile: view own details. Change password (all roles).
8. User management (admin only): create user, deactivate user, reset password (new password shown once).
9. Activity log (admin only).
10. Login history (role-aware: own only for student/teacher, all-except-admin for HOD, all for admin).
11. Reports (admin, HOD, teacher).
12. Error pages: 403, 404, 500, and the CSRF "your form expired" page.

Navigation shows only the links each role can use.

## Database design (mapped to the practicals)

The schema follows Unit C Experiments 1–5 (3NF design from Experiment 5):

| Table | Cardinarity | Practical reference |
|---|---|---|
| `departments` (1) → `students` (m) | 1:many | Exp. 5: a department has many students |
| `departments` (1) → `teachers` (m) | 1:many | Exp. 5: a department has many teachers |
| `teachers` (1) → `courses` (m) | 1:many | Exp. 5: a teacher teaches many courses |
| `departments` (1) → `courses` (m) | 1:many | Exp. 5: a course belongs to one department |
| `students` (m) ↔ `courses` (m) via `enrollments` | many-to-many | Exp. 1–5: the enrolment table resolves the M:N, with marks |

Foreign keys: `teachers.department_id`, `students.department_id`, `courses.teacher_id`, `courses.department_id`, `enrollments.student_id`, `enrollments.course_id`. All enforced with `PRAGMA foreign_keys = ON`.

## Security controls

- Passwords hashed with `werkzeug.security.generate_password_hash` (scrypt, fallback to pbkdf2:sha256 on older Python).
- Account lockout: 15 minutes after 5 failed logins, logged as `ACCOUNT_LOCKED`.
- Session timeout: 30 minutes of inactivity.
- Cookies: HttpOnly, SameSite=Lax, and `Secure` when `SESSION_COOKIE_SECURE=1`
  (kept off by default so a plain `http://localhost` demo can sign in; a Secure
  cookie is not sent over HTTP).
- `SECRET_KEY` read from the environment; if missing, a random key is generated with a warning.
- CSRF token on every POST form (Flask-WTF CSRFProtect), with a friendly
  "form expired" page instead of a raw 400.
- Every 403 writes an `ACCESS_DENIED` audit row (route, actor, role, IP).
- Security headers on every response: Content-Security-Policy `default-src 'self'`, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy same-origin.
- Fernet encryption for `students.national_id_enc`. Key from `PORTAL_FERNET_KEY`. App refuses to start without it. Only admin can view the decrypted value, and each view writes `VIEW_SENSITIVE`.
- Parameterised SQL only (`?` placeholders). No string-built SQL.
- Input validation: max lengths, email format, marks 0–100 (CHECK constraint and form check), enum checks for role and status.
- Friendly 403, 404, 500 pages. No stack traces to users. Debug mode only when `DEBUG=1`.
- Password change requires minimum 8 characters.
- Every edit records old and new value in `audit_log`. Every row also names the actor: the username and role are read from `users` by `audit.py`, so the trail is never blank.
- `login_history` holds sign-in attempts only — success and failure both, each with the IP address. A logout is recorded in `audit_log`, never as a failed login.

## Seed data

- 4 branches: CSE, ECE, ME, CE
- Enrolments for rolls 101–105 are exactly the rows printed in the Unit C practical (Aman Verma C101=78, C102=82; Riya Kapoor C101=91, C103=88; Karan Mehta C102=69; Neha Joshi C104=74, C101=85; Simran Kaur C104=80). Other students take 3–5 courses.
- 6 teachers: T001–T006 (Mr. Sharma, Ms. Gupta, Mr. Verma, Dr. Rao, Dr. Kumar, Dr. Mishra)
- 50 students: roll 101–150 (101–105 are the practical students; 106–150 have realistic Indian names)
- 12 courses: C101–C112
- Each student enrolled in 3–5 courses (204 enrolments), marks 0–100, about a third left NULL to exercise the reporting queries
- 1 admin, 1 HOD, 6 teacher accounts, 50 student accounts (58 users total)
- `seed.py` gives every account a random 14-character password (upper, lower,
  digit, symbol, from the `secrets` module); `set_demo_passwords.py` then sets
  the fixed demo passwords used for marking and testing
- `CREDENTIALS.txt` is written by both scripts through one shared writer
- Re-seeding also clears `audit_log` and `login_history`, because their target ids would otherwise point at different people once the ids restart

## Credentials file

`CREDENTIALS.txt` is generated from the live database by `credentials.py`, the
single writer used by both `seed.py` and `set_demo_passwords.py`, so the file
cannot drift from the tables. It contains:

- Header: the "DEMO ACCOUNTS … delete before real use" warning, a `Generated:`
  UTC timestamp, and the account totals read from the database
  (currently 58 users: 1 admin, 1 HOD, 6 teachers, 50 students)
- Sections: Admin, HOD, Teachers, Students (grouped by branch)
- For each account: username, role, full name, branch, roll number or staff code, plain-text password
- Any account without a linked student/teacher row is still listed under "Other accounts", and a password the writer was not given is shown as `(not recorded)` — never invented

`python set_demo_passwords.py --verify` re-reads the file, checks every account
exists, compares every password with the stored hash, and reports any account
that is missing, stale or deactivated.

## Known limitations

- **SQLite**: Not suitable for production. Concurrent write access is serialised.
- **Demo only**: Fernet key, SECRET_KEY, passwords, and the credentials file are not production-grade. The credentials file must be deleted before any real use.
- **No email confirmation, no OAuth, no 2FA**: the demo passwords are known and identical per role; suitable for a lab submission only.
- **No pagination**: Lists are small (50 students, 12 courses) so pagination is omitted.
- **No file uploads, no REST API**: The application is a server-rendered web UI.
- **No password strength meter**: Minimum 8 characters enforced, but no complexity requirements beyond that.
