# 🎓 University Records Portal

Who can see which marks, and who can change them? This portal answers that question, and writes down every time someone tries to answer it the wrong way.

It's a role-based university records system built with Flask and Jinja2. No SPA, no build step, one command to run.

Students, teachers, HODs and admins each get a dashboard scoped to what they're allowed to do: view their own marks, enter marks, edit department records, or manage every account. Every route enforces its role, and every edit, denial and sensitive view is written to an audit trail.

## Highlights

- **Four roles, one codebase:** student, teacher, HOD and admin, with per-route permission checks. Tamper with a URL and you get a 403 plus an audit row.
- **Real sign-in presence:** the admin dashboard shows who has a live session right now (refreshed every 10s), separately from whether an account is enabled.
- **Encrypted national IDs:** Fernet-encrypted at rest, admin-only, and decrypted only after the admin re-enters their password. Every reveal and refusal is logged.
- **Account management:** create users for any role, deactivate or reactivate them, reset passwords (shown once), and lock accounts out after 5 failed attempts.
- **Reports:** averages per department, students above average, and second-highest mark.
- **SQLite or MySQL:** same code, selected with `DB_ENGINE`.

## Quick Start

```bash
./run.sh
```

That creates a venv, installs dependencies, seeds demo data, and opens the browser.

Demo logins:

| Role    | Username    | Password       |
|---------|-------------|----------------|
| Admin   | `admin`     | `Admin123!`    |
| HOD     | `hod`       | `Hod123!`      |
| Teacher | `T001`–`T006` | `Teacher123!` |
| Student | `101`–`150` | `Student123!`  |

## Tests

```bash
./run.sh test
```

Runs 221 pytest cases against temporary databases.

For an end-to-end check that logs in as all four roles:

```bash
./venv/bin/python scripts/smoke_test.py
```

## Project Layout

```
app.py       Flask factory, security headers, error pages
portal/      config, db, security, audit, credentials, blueprints,
             repositories, services, templates, static
scripts/     seed, demo passwords, table viewer, smoke test
tests/       221 cases
docs/        GUIDE (usage), REFERENCE (design/security/MySQL), HANDOFF (state)
```

## Security Notes

- Parameterised SQL only
- scrypt password hashing
- CSRF protection on every form
- Strict CSP
- HttpOnly and SameSite cookies
- Encrypted national IDs
- Full audit trail

**Heads up:** this is a teaching project. The demo passwords are public and the demo Fernet key lives in `run.sh`. Change both (and delete `CREDENTIALS.txt`) before any real use. Please don't put your actual university's records in here. 😄
