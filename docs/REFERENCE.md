# Reference

Deep details moved out of the README so the README stays a quick front page.

- [Source material and schema mapping](#source-material-and-schema-mapping)
- [Database design](#database-design)
- [Security controls](#security-controls)
- [Seed data](#seed-data)
- [Credentials file](#credentials-file)
- [Manual setup (without run.sh)](#manual-setup-without-runsh)
- [MySQL mode](#mysql-mode)
- [Known limitations](#known-limitations)

## Source material and schema mapping

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

  The portal implements the 3NF schema from Experiment 5 (Experiment 2's
  functional dependencies are enforced by the keys) and uses the manual's own
  sample data: students Aman Verma (101), Riya Kapoor (102), Karan Mehta (103),
  Neha Joshi (104), Simran Kaur (105); courses C101 DBMS (Mr. Sharma), C102 Java
  (Ms. Gupta), C103 Python (Mr. Verma), C104 Circuits (Dr. Rao); teachers also
  include Dr. Kumar and Dr. Mishra; departments CSE (Dr. Singh) and ECE
  (Dr. Nair), extended with ME and CE so the portal has more than one branch to
  filter by. Experiments 6–11 are analysis exercises on separate demo tables
  (`class_allocation`, `teacher_course`, `student_teacher`, `class_room`), so they
  are documented in the practical file rather than modelled in the app.
- **DBMS_Practicals_24GAX303.pdf** — Practical 1 (JOINs) and Practical 2
  (aggregates, GROUP BY, HAVING, subqueries). These patterns are implemented on
  the Reports page (average marks per department, students above the average,
  second-highest mark).

The company_db employee tables from Practicals 1 and 2 are reference only and are
not included in the university data.

## Database design

The schema follows Unit C Experiments 1–5 (3NF design from Experiment 5):

| Relationship | Cardinality | Practical reference |
| --- | --- | --- |
| `departments` → `students` | 1:many | Exp. 5: a department has many students |
| `departments` → `teachers` | 1:many | Exp. 5: a department has many teachers |
| `teachers` → `courses` | 1:many | Exp. 5: a teacher teaches many courses |
| `departments` → `courses` | 1:many | Exp. 5: a course belongs to one department |
| `students` ↔ `courses` via `enrollments` | many-to-many | Exp. 1–5: the enrolment table resolves the M:N, with marks |

Foreign keys: `teachers.department_id`, `students.department_id`,
`courses.teacher_id`, `courses.department_id`, `enrollments.student_id`,
`enrollments.course_id`. All enforced with `PRAGMA foreign_keys = ON`.

Tables: `departments`, `teachers`, `students`, `courses`, `enrollments`, `users`,
`audit_log`, `login_history`.

## Security controls

- Passwords hashed with `werkzeug.security.generate_password_hash` (scrypt,
  fallback to pbkdf2:sha256 on older Python).
- Account lockout: 15 minutes after 5 failed logins, logged as `ACCOUNT_LOCKED`.
- Session timeout: 30 minutes of inactivity.
- Cookies: HttpOnly, SameSite=Lax, and `Secure` when `SESSION_COOKIE_SECURE=1`
  (kept off by default so a plain `http://localhost` demo can sign in; a Secure
  cookie is not sent over HTTP).
- `SECRET_KEY` read from the environment; if missing, a random key is generated
  with a warning.
- CSRF token on every POST form (Flask-WTF CSRFProtect), with a friendly "form
  expired" page instead of a raw 400.
- Every 403 writes an `ACCESS_DENIED` audit row (route, actor, role, IP).
- Security headers on every response: Content-Security-Policy `default-src 'self'`
  (plus `script-src 'self'`, `font-src 'self'`, `object-src 'none'`,
  `frame-ancestors 'none'`), X-Frame-Options DENY, X-Content-Type-Options nosniff,
  Referrer-Policy same-origin.
- Fernet encryption for `students.national_id_enc`. Key from
  `PORTAL_FERNET_KEY`; the app refuses to start without it. Only admin can view
  the decrypted value, and each view writes `VIEW_SENSITIVE`.
- Parameterised SQL only (`?` placeholders). No string-built SQL.
- Input validation: max lengths, email format, marks 0–100 (CHECK constraint and
  form check), enum checks for role and status.
- Friendly 403, 404, 500 pages. No stack traces to users. Debug only with `DEBUG=1`.
- Password change requires a minimum of 8 characters.
- Every edit records old and new value in `audit_log`, with the actor's username
  and role read from `users` by `audit.py`.
- `login_history` holds sign-in attempts only — success and failure, each with the
  IP address. A logout is recorded in `audit_log`, never as a failed login.
- All client-side JavaScript lives in `static/app.js`; there is no inline script,
  so the CSP needs no `'unsafe-inline'` for scripts.

## Seed data

- 4 branches: CSE, ECE, ME, CE
- Enrolments for rolls 101–105 are exactly the rows printed in the Unit C
  practical (Aman Verma C101=78, C102=82; Riya Kapoor C101=91, C103=88; Karan
  Mehta C102=69; Neha Joshi C104=74, C101=85; Simran Kaur C104=80). Other students
  take 3–5 courses.
- 6 teachers: T001–T006 (Mr. Sharma, Ms. Gupta, Mr. Verma, Dr. Rao, Dr. Kumar,
  Dr. Mishra)
- 50 students: roll 101–150 (101–105 are the practical students; 106–150 have
  realistic Indian names)
- 12 courses: C101–C112
- Each student enrolled in 3–5 courses (204 enrolments), marks 0–100, about a
  third left NULL to exercise the reporting queries
- 1 admin, 1 HOD, 6 teacher accounts, 50 student accounts (58 users total)
- `seed.py` gives every account a random 14-character password; the credentials
  file records it. `set_demo_passwords.py` then sets the fixed demo passwords.
- Re-seeding clears `audit_log` and `login_history`, because their target ids
  would otherwise point at different people once the ids restart.

## Credentials file

`CREDENTIALS.txt` is generated from the live database by `credentials.py`, the
single writer used by both `seed.py` and `set_demo_passwords.py`, so the file
cannot drift from the tables. It contains:

- A header with the demo-only warning, a `Generated:` UTC timestamp and the
  account totals read from the database (currently 58 users).
- Sections: Admin, HOD, Teachers, Students (grouped by branch).
- For each account: username, role, full name, branch, roll number or staff code,
  plain-text password.
- Any account without a linked student/teacher row is listed under "Other
  accounts", and a password the writer was not given is shown as
  `(not recorded)` — never invented.

`./run.sh verify` (or `python set_demo_passwords.py --verify`) re-reads the file,
checks every account exists, compares every password with the stored hash, and
reports any account that is missing, stale or deactivated.

## Manual setup (without run.sh)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export PORTAL_FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

python seed.py
python set_demo_passwords.py
PORT=5055 python app.py
```

Keep the same `PORTAL_FERNET_KEY` for the life of a database: it encrypts
`students.national_id_enc`, so a new key cannot decrypt rows written with the old
one. Re-seed after changing the key.

## MySQL mode

SQLite is the default because it needs no server. The app also runs against MySQL
with no code changes: create the database, set five environment variables, re-run
the same seed script.

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

python seed.py                        # creates schema_mysql.sql tables + sample data
python set_demo_passwords.py --verify  # CREDENTIALS.txt now matches MySQL
PORT=5055 python app.py
```

Unset `DB_ENGINE` (or set it to `sqlite`) to go back to the file database.
`university.db` is not deleted or modified while MySQL mode is active. `db.py`
wraps the PyMySQL connection so the rest of the app keeps using sqlite3-style
`conn.execute("… ?", params)` calls.

`schema_mysql.sql` differs from `schema.sql` only where MySQL requires it:
`AUTO_INCREMENT`, `VARCHAR` instead of unbounded `TEXT` for unique/indexed
columns, `utf8mb4_bin` collation so usernames and emails stay case-sensitive like
SQLite, and timestamp columns kept as `VARCHAR(32)` because the app stores ISO
strings such as `2026-11-04T12:01:52.219134`.

## Known limitations

- **SQLite**: not suitable for production. Concurrent write access is serialised.
- **Demo only**: Fernet key, SECRET_KEY and passwords are not production-grade.
  The credentials file must be deleted before any real use.
- **No email confirmation, OAuth or 2FA**: demo passwords are known and shared per
  role; suitable for a lab submission only.
- **No pagination**: lists are small (50 students, 12 courses), so it is omitted.
- **No file uploads, no REST API**: a server-rendered web UI.
- **No password strength meter**: minimum 8 characters, no complexity rules.
- **MySQL test coverage**: `tests/conftest.py` isolates each test by copying the
  SQLite file, so the suite exercises SQLite. MySQL is verified manually with
  `seed.py`, `set_demo_passwords.py --verify` and `tools/smoke_test.py`.
