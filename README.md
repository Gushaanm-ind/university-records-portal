# University Database Portal

A role-based web app for a university database — students, teachers, departments,
courses, enrolments and marks — built with Flask, Jinja2 and SQLite. Four roles
(student, teacher, HOD, admin) with an audit trail, login history, reports and
admin user management.

## Quick start

```bash
git clone <your-repo-url> university_portal
cd university_portal
./run.sh
```

Then open **http://127.0.0.1:5055/login**.

`run.sh` creates the virtualenv, installs the packages, generates the demo
database and keys, starts the server and opens the browser. Run it again any
time — if the portal is already up it just reopens the browser.

| Command | Does |
| --- | --- |
| `./run.sh` | start (or reuse) and open the browser |
| `./run.sh stop` | stop the server |
| `./run.sh restart` | restart |
| `./run.sh status` | is it running? |
| `./run.sh logs` | last 60 log lines |
| `./run.sh verify` | check data + `CREDENTIALS.txt` |
| `./run.sh test` | run the test suite |
| `./run.sh reset` | rebuild the database |

## Demo accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `Admin123!` |
| HOD | `hod` | `Hod123!` |
| Teacher | `T001` … `T006` | `Teacher123!` |
| Student | `101` … `150` | `Student123!` |

Demo data: 4 departments, 6 teachers, 50 students, 12 courses, 204 enrolments,
58 user accounts. `CREDENTIALS.txt` (generated, git-ignored) lists every account.

## What it does

- **Login** with lockout after 5 failed attempts (15 minutes) and a 30-minute
  idle timeout.
- **Dashboards** per role with counts and quick actions.
- **Students / teachers / courses** lists with search and filters; detail pages
  with enrolments and marks.
- **Marks entry** by HOD and admin; read-only views for teachers and students.
- **Admin user management**: create a user for any role, deactivate, reactivate,
  reset a password (shown once), all recorded in the audit log.
- **Reports**: averages per department, students above average, second-highest
  mark.
- **Activity log and login history**, role-filtered.
- **Signed in now**: a live list of accounts with an active session, refreshed
  every 10 seconds, separate from whether an account is enabled.
- **National ID reveal** for admin only, encrypted at rest, decrypted only after
  the admin re-enters their password; every reveal and refusal is logged.

## Roles at a glance

| Action | Student | Teacher | HOD | Admin |
| --- | --- | --- | --- | --- |
| Own profile, courses, marks | Yes | Yes | Yes | Yes |
| View all students / teachers | No | Yes (read) | Yes | Yes |
| Edit students / teachers | No | No | Yes | Yes |
| Create, deactivate, reactivate users | No | No | No | Yes |
| Activity log | No | No | No | Yes |
| Login history | Own | Own | All except admin | All |

Every route checks the role; a tampered URL returns 403 and writes an
`ACCESS_DENIED` audit row.

## Tests

```bash
./run.sh test     # 220 pytest tests, each on a fresh temporary database
./venv/bin/python scripts/smoke_test.py   # end-to-end login as all four roles
```

## Project layout

```
app.py              Flask app factory, security headers, error pages
run.sh              one-command launcher
requirements.txt    Python dependencies

portal/             the application package
  config.py           environment-driven settings
  db.py               SQLite/MySQL connection layer
  schema.sql          database schema (schema_mysql.sql for MySQL)
  security.py         password hashing, Fernet encryption
  audit.py            audit trail writer
  credentials.py      CREDENTIALS.txt writer and checker
  repositories/       SQL queries
  services/           business rules (auth, permissions, edits, reports)
  blueprints/         routes per role (auth, dashboard, student, teacher, hod, admin)
  templates/          Jinja2 pages
  static/             style.css design system, app.js interface behaviour

scripts/            seed.py, set_demo_passwords.py, show_tables.py, smoke_test.py
tests/              220 pytest cases
docs/               GUIDE.md, REFERENCE.md, HANDOFF.md
```

## Security notes

Parameterised SQL only, hashed passwords (scrypt), CSRF token on every form,
strict Content-Security-Policy, HttpOnly/SameSite cookies, encrypted national IDs
and a recorded audit row for every edit, denial and sensitive view.

This is a teaching/demo project: the demo passwords are public and the Fernet key
is a local default. Change both (and delete `CREDENTIALS.txt`) before any real
use. See [`docs/REFERENCE.md`](docs/REFERENCE.md) for the full security list,
database design and seed details.

## Docs

- [`docs/GUIDE.md`](docs/GUIDE.md) — short step-by-step usage guide
- [`docs/REFERENCE.md`](docs/REFERENCE.md) — detailed reference (design, security, data, MySQL)
- [`docs/HANDOFF.md`](docs/HANDOFF.md) — current verified state and open items
