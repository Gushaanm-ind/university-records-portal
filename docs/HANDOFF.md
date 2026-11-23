# HANDOFF — read this first

State of `university_portal` at the point this file was written, what is proven,
what is still open, and the exact commands to check it yourself. Written so that
another agent (or a person) can continue without re-deriving anything.

---

## 1. What the project is

A Flask + Jinja2 + SQLite university portal (DBMS practical, 25GAX303 Unit C).
Four roles — student, teacher, HOD, admin — enforced in the service layer, with an
audit trail, login history, reports, and a generated `CREDENTIALS.txt`.

Two database engines now work:

| `DB_ENGINE` | Storage | Needs a server? |
| --- | --- | --- |
| unset or `sqlite` (default) | `university.db` (116 KB) | no |
| `mysql` | MySQL database `university_db` | yes, on 127.0.0.1:3306 |

## 2. Verified facts (measured, not assumed)

- **220 pytest tests pass** on SQLite: `pytest -q` → `220 passed`.
- **Smoke test passes** on SQLite: `python scripts/smoke_test.py` → `SMOKE TEST PASSED`, four roles.
- **Live logins work**: all four roles return 200 on `/admin`, `/hod`, `/teacher`, `/student`.
- **CREDENTIALS.txt matches the database**: `python scripts/set_demo_passwords.py --verify` → OK.
- **Data**: 58 users (1 admin, 1 HOD, 6 teachers, 50 students), 50 students, 12 courses,
  204 enrolments, 4 departments.
- **MySQL is live and verified** (server 26.7.0, `portal@127.0.0.1:3306/university_db`):
  `scripts/seed.py` → 8 tables, 58 users, 50 students, 6 teachers, 12 courses, 204 enrolments,
  4 departments; `set_demo_passwords.py --verify` → matches; `scripts/show_tables.py --list`
  reads MySQL through `information_schema`; `SMOKE_ALLOW_MYSQL=1 python scripts/smoke_test.py` →
  **SMOKE TEST PASSED** (all 4 roles, all pages); live logins on port 5055 → admin/hod/
  T001/101 each land on their dashboard, student gets **403** on `/admin`, a wrong
  password writes `login_history.success = 0`.
- **MySQL credentials in use**: user `portal`, password `PortalDev123!`, database
  `university_db` (local demo values; change them in the env exports and in MySQL
  together). The database/user were created by the owner with root access.

## 3. Environment this was built in

```bash
cd ~/Documents/university_portal
./run.sh            # venv + packages + keys + seed + server + browser, one command
```

The launcher (`run.sh`) sets these itself for local use:

```bash
source venv/bin/activate          # Python 3.9.6
export SECRET_KEY="dev-secret-change-me"
export PORTAL_FERNET_KEY="Jz5EWERS6MnfMqH3r5LB5bnxb2vEtvK5Wcmut8Q8ncU="
```

Keep that Fernet key: it encrypted `students.national_id_enc` in `university.db`.
Changing it makes existing ID numbers undecryptable (the app reports that plainly).

Python 3.9.6 and pip 21.2.4. Installed: Flask 3.1.1, Flask-WTF 1.2.1, WTForms 3.2.1,
Werkzeug 3.1.3, cryptography 43.0.3, **PyMySQL 1.2.3**, pytest 8.4.2.

The Mac already has Homebrew MySQL 26.7.0 installed and running (`brew services list`
shows `mysql started`, `mysqld` listening on 3306). **Do not reinstall it.** `root`
requires a password that is not in this repository, so a database administrator
must create the portal's database and user once (see §5).

## 4. How to run the checks

```bash
# full suite (about 2m20s)
pytest -q

# one module
pytest tests/test_login_history.py -q

# end-to-end login as all four roles against a temporary database
python scripts/smoke_test.py

# database in the terminal
python scripts/show_tables.py --list
python scripts/show_tables.py --table users --limit 5
python scripts/show_tables.py --sql "SELECT role, COUNT(*) AS n FROM users GROUP BY role"

# credential file vs database
python scripts/set_demo_passwords.py --verify
```

The test suite builds its own database in a temp directory (`tests/conftest.py`),
so running it never touches `university.db` or `CREDENTIALS.txt`.

## 5. The MySQL run — done, and how to repeat it

The database and user already exist on this Mac, so nothing privileged is needed
from here on:

```bash
export DB_ENGINE=mysql MYSQL_USER=portal MYSQL_PASSWORD='PortalDev123!' MYSQL_DATABASE=university_db
python scripts/seed.py                          # rebuild tables + sample data
export SMOKE_ALLOW_MYSQL=1
python scripts/smoke_test.py              # 4 roles, every page
python scripts/set_demo_passwords.py           # restore demo passwords (smoke overwrote 4)
python scripts/set_demo_passwords.py --verify
PORT=5055 python app.py
```

Expected numbers after `scripts/seed.py`: users 58, students 50, teachers 6, courses 12,
enrolments 204, departments 4, `audit_log`/`login_history` empty until the site is used.

Rebuilding from scratch (needs root) — this is what was run, and it is idempotent
as written:

```sql
DROP DATABASE IF EXISTS university_db;
CREATE DATABASE university_db CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
DROP USER IF EXISTS 'portal'@'localhost';
CREATE USER 'portal'@'localhost' IDENTIFIED BY 'PortalDev123!';
GRANT ALL PRIVILEGES ON university_db.* TO 'portal'@'localhost';
FLUSH PRIVILEGES;
```

**If `scripts/seed.py` ever fails**, read the *first* error:

- `Every derived table must have its own alias` — MySQL-only rule; SQLite allows
  `FROM (SELECT …)` with no alias. Fixed once already in `services/reports.py`.
- `Duplicate key name 'idx_…'` — a `CREATE INDEX` re-run. Indexes must be declared
  inside `CREATE TABLE` (they are now); MySQL has no `CREATE INDEX IF NOT EXISTS`.
- `Can't connect … (Errno 61)` — the server is not listening on TCP. Check
  `lsof -nP -iTCP:3306 -sTCP:LISTEN`. If it prints nothing while `ps aux | grep mysqld`
  shows `--skip-grant-tables --skip-networking`, MySQL is in recovery mode: kill that
  process and run `brew services start mysql`.
- `Access denied for user 'portal'` — wrong password, or the user was created for a
  different host (`'portal'@'localhost'` only).

**Still not done, and not claimed: MySQL test-suite coverage.** `tests/conftest.py`
isolates tests by copying the SQLite file, which has no MySQL equivalent, so the 220
tests currently exercise SQLite only. The design to implement: one template database
per session, snapshot its rows in Python, then per test `TRUNCATE` (FK checks off) and
re-insert the snapshot. Until that exists and `DB_ENGINE=mysql pytest -q` is green, do
not describe the suite as engine-agnostic.

## 6. What changed while adding the dual backend

| File | Change |
| --- | --- |
| `config.py` | `DB_ENGINE` + five `MYSQL_*` settings (host, port, user, password, database) |
| `db.py` | `engine()`, `using_mysql()`, `Row` (dict + positional), `MySQLConnection`/`MySQLCursor` adapter, `schema_file()`, `init_db()` picks the right schema |
| `schema_mysql.sql` | New: same 8 tables for MySQL (`AUTO_INCREMENT`, `VARCHAR`, `utf8mb4_bin`, InnoDB, FKs, indexes, CHECKs) |
| `scripts/seed.py` | `_reset_data()` (MySQL: `SET FOREIGN_KEY_CHECKS=0` + `TRUNCATE`; SQLite: `DELETE` + `sqlite_sequence` reset), `INSERT IGNORE` vs `INSERT OR IGNORE` |
| `credentials.py` | Uses `get_db()`; engine-aware roll-number ordering (`CAST(… AS SIGNED)`); header names the MySQL database |
| `scripts/show_tables.py` | Follows `DB_ENGINE`; `information_schema` + `SHOW CREATE TABLE` on MySQL, `sqlite_master` on SQLite; same output format |
| `requirements.txt` | `PyMySQL==1.2.3` |
| `README.md`, `GUIDE.md` | MySQL section: create database/user, env vars, seed, switch back |

Nothing else was touched: templates, blueprints, services, repositories and audit
rules are byte-identical on both engines.

## 7. Traps that already bit once (do not re-introduce)

- **Case sensitivity.** MySQL's default collation is case-insensitive; tables use
  `utf8mb4_bin` so `Admin` ≠ `admin`, matching SQLite. Removing it changes login behaviour.
- **Timestamps are ISO strings** (`2026-11-04T12:01:52.219134`), so those columns are
  `VARCHAR(32)`. MySQL `DATETIME` rejects the `T` separator.
- **Rows are read both ways**: `row["username"]` and `row[0]`. `db.Row` supports both.
  A plain `DictCursor` dict would break `row[0]` in `audit.py` and `show_tables.py`.
- **`sqlite_sequence`** has no MySQL equivalent; `TRUNCATE` resets `AUTO_INCREMENT`.
- **`INSERT OR IGNORE`** is SQLite syntax; MySQL wants `INSERT IGNORE`.
- **No `%` literals in SQL** — the adapter escapes `%` before translating `?` to `%s`.
  If someone adds a `LIKE '%abc%'` inline literal, behaviour changes.
- **Ports**: macOS AirPlay owns 5000. Run the app with `PORT=5055`.
- **Seed clears `audit_log` and `login_history`** on purpose: target ids restart, so
  old rows would name the wrong people.

## 8. Checkpoints and rollback

The project is a git repository (initialised after the UI work). Restore points:

- Tag `checkpoint-1` — commit `1840be3`, the verified working state: redesigned UI,
  220 tests passing, SQLite data intact (58 users, 50 students, 204 enrolments).
- `.checkpoints/university_portal_checkpoint-1.tar.gz` — plain copy of the same
  state, venv excluded, in case git itself is damaged.

```bash
git stash                  # park uncommitted work
git checkout checkpoint-1  # go back to the known-good state
git checkout main          # return to the latest commits
```

`university.db` and `CREDENTIALS.txt` are git-ignored (regenerate with
`./run.sh reset`), so checking out a tag never overwrites the live data. To switch
back from MySQL, `unset DB_ENGINE`.

## 9. Useful inventory

```
app.py  run.sh  README.md  requirements.txt
portal/  config.py  db.py  schema.sql  schema_mysql.sql  seed-less package of app code
  credentials.py  security.py  audit.py
  blueprints/ (auth, student, teacher, hod, admin, dashboard)
  repositories/ (users, objects, audit, departments)
  services/ (permissions, edits, reports, user_management)
  templates/  static/
scripts/ (seed.py, set_demo_passwords.py, show_tables.py, smoke_test.py)
tests/ (11 files, 220 cases)
docs/ (GUIDE.md, REFERENCE.md, HANDOFF.md)
CREDENTIALS.txt  university.db
```

Demo accounts: `admin`/`Admin123!`, `hod`/`Hod123!`, `T001`…`T006`/`Teacher123!`,
`101`…`150`/`Student123!`. Usernames are roll numbers or staff codes.
