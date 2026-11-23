# University Portal — Guide

A Flask + SQLite web app for a university database: students, teachers, courses,
marks, with four login roles. This page is the short version. The deep details
(database design, security rules, seed data) are in
[`docs/REFERENCE.md`](docs/REFERENCE.md).

---

## 1. Start it — one command

```bash
cd ~/Documents/university_portal
./run.sh
```

That is the whole startup. On the first run it also creates the virtual
environment, installs the packages, creates the demo database and opens the
browser. On later runs it starts in about a second. If the portal is already
running, `./run.sh` just opens the browser again.

**The portal is at http://127.0.0.1:5055/login**

| I want to… | Command |
| --- | --- |
| Start (or reuse) and open the browser | `./run.sh` |
| Start without opening a browser | `./run.sh -n` |
| Stop the server | `./run.sh stop` |
| Restart after code changes | `./run.sh restart` |
| Check it is up | `./run.sh status` |
| Read the server log | `./run.sh logs` |
| Check the data and passwords | `./run.sh verify` |
| Run all 220 tests | `./run.sh test` |
| Rebuild the database from scratch | `./run.sh reset` |

The script keeps its own settings in `.run/` (pid + log). Nothing else to
install or activate by hand.

---

## 2. Sign in

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `Admin123!` | Admin — everything |
| `hod` | `Hod123!` | HOD — department data, edits, reports |
| `T001` … `T006` | `Teacher123!` | Teacher — own courses, marks |
| `101` … `150` | `Student123!` | Student — own marks and profile |

The same list is generated from the database into `CREDENTIALS.txt`.

After signing in you land on your own dashboard: `/admin`, `/hod`, `/teacher`,
`/student`. The sidebar only shows what your role is allowed to open.

---

## 3. What each role can do

- **Student** — sees own courses, marks and profile; can change own password.
  Cannot edit any data.
- **Teacher** — sees every student and course, read only; enters marks on own
  courses.
- **HOD** — edits students and teachers, sees department reports and login
  history. Cannot create users or read the activity log.
- **Admin** — creates users (student, teacher, HOD, admin), deactivates and
  reactivates accounts, resets passwords, edits anyone, reads the activity log
  and all login history, and reveals a student's national ID (each reveal is
  logged).

### Admin: managing users
1. Sidebar → **Users**.
2. **Create user** → pick the role card, fill in the details, use *Generate* for
   a password if you like. The password is shown once on the confirmation page —
   copy it then.
3. On the Users list: search, filter by role or status, **deactivate** an
   account, or **reactivate** it later. Reset a password from the same page.

Accounts are deactivated rather than deleted, so the audit trail keeps its
references. Deactivated accounts cannot sign in.

---

## 4. Look at the data in the terminal

```bash
./venv/bin/python tools/show_tables.py --list                      # tables + row counts
./venv/bin/python tools/show_tables.py                             # 5 main tables
./venv/bin/python tools/show_tables.py --table users --limit 5
./venv/bin/python tools/show_tables.py --sql "SELECT role, COUNT(*) FROM users GROUP BY role"
```

Read-only: `SELECT`, `WITH` and `PRAGMA` only. Expected totals: 4 departments,
6 teachers, 50 students, 12 courses, 204 enrolments, 58 users.

`./run.sh verify` prints those counts and checks every password in
`CREDENTIALS.txt` against the database.

---

## 5. Tests

```bash
./run.sh test                        # 220 pytest tests, temporary database
./venv/bin/python tools/smoke_test.py   # logs in as all four roles
```

Tests never touch `university.db` or `CREDENTIALS.txt`.

---

## 6. If something goes wrong

| Symptom | Fix |
| --- | --- |
| Nothing opens at 5055 | `./run.sh status`, then `./run.sh logs` |
| Port already in use | `./run.sh stop`, then `./run.sh` |
| "PORTAL_FERNET_KEY is not set" | Use `./run.sh`; it sets the key for you |
| "Your form expired" | Reload the page and submit again (stale CSRF token) |
| Login fails after 5 tries | Account locked for 15 minutes; wait, or reset its password as admin |
| `CREDENTIALS.txt does not match` | `./run.sh verify`, then `./run.sh reset` if needed |
| National ID will not decrypt | The Fernet key changed. Re-run `./run.sh reset` |
| Marks are blank | Not entered yet — about a third of enrolments are intentionally empty |
| Want a clean database | `./run.sh reset` |

---

## 7. Restore point (checkpoint)

The project is under git. Before any change you can return to the known-good
state:

```bash
git status                 # what changed
git stash                  # park your changes
git checkout checkpoint-1  # go back to the working checkpoint
git checkout main          # return to the latest work
```

There is also a plain copy at `.checkpoints/university_portal_checkpoint-1.tar.gz`.

---

## 8. Optional: MySQL instead of SQLite

SQLite needs no server, so it is the default. To use MySQL, create the database
once as a MySQL admin, then start the portal with the engine set:

```sql
CREATE DATABASE university_db CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'portal'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON university_db.* TO 'portal'@'localhost';
```

```bash
DB_ENGINE=mysql MYSQL_PASSWORD='your-password' ./run.sh reset   # build tables + data
DB_ENGINE=mysql MYSQL_PASSWORD='your-password' ./run.sh         # start
./run.sh                                                        # back to SQLite
```

Put those variables in a local `.env` file instead of typing them each time
(`run.sh` reads it; `.env` is git-ignored).

---

## 9. Changing code

After editing templates, CSS or Python, the Flask dev server picks changes up
on reload. If a page looks stale, `./run.sh restart`.

Before committing:

```bash
./run.sh test
./run.sh verify
```
