# University Portal Guide — Simple Version

This guide tells you how to run the portal, log in, see the database, and use all the features.
I explain every command simply — what it does and why you run it.

---

## Quick start (first time only)

If this is the first time you're running the portal, do these steps once:

### 1. Open a terminal
- On Mac: Press `Cmd + Space`, type `Terminal`, press Enter
- In the terminal window that opens, type:
  ```bash
  cd ~/Documents/university_portal
  ```
  This changes folder to the portal project.

### 2. Create and activate the virtual environment
```bash
python3 -m venv venv
```
- This creates a isolated Python environment so you don't mess up other Python projects.
- It creates a folder called `venv/`.

```bash
source venv/bin/activate
```
- This "turns on" the virtual environment. You'll see `(venv)` appear at the start of your command prompt.
- Now any Python packages you install will only affect this project.

### 3. Install the required packages
```bash
pip3 install -r requirements.txt
```
- `requirements.txt` lists all the Python packages the portal needs.
- This installs: Flask, Flask-WTF, WTForms, Werkzeug, cryptography, pytest, and PyMySQL.

### 4. Set the two required environment variables
The portal needs two keys to work. Type each line separately:

```bash
export SECRET_KEY="dev-secret-change-me"
```
- This tells Flask how to encrypt your session (your login state).
- You can choose any short string here. Keep it the same for all later steps.

```bash
export PORTAL_FERNET_KEY="Jz5EWERS6MnfMqH3r5LB5bnxb2vEtvK5Wcmut8Q8ncU="
```
- This key encrypts students' national ID numbers in the database.
- **Never change this key** unless you re-run `seed.py` afterward. If you change it, the encrypted IDs become unreadable.

### 5. Build the database and create demo accounts
```bash
python seed.py
```
- This creates the database file `university.db` (SQLite) **or** sets up MySQL tables.
- It creates: 4 departments, 6 teachers, 50 students, 12 courses, 204 enrolments, and 58 user accounts.
- It also writes a file called `CREDENTIALS.txt` with all the usernames and passwords.

```bash
python set_demo_passwords.py
```
- The passwords created by `seed.py` are random and hard to remember.
- This script replaces them with simple demo passwords so you can actually log in.
- It also rewrites `CREDENTIALS.txt` with the demo passwords.

### 6. Verify the passwords match the database
```bash
python set_demo_passwords.py --verify
```
- This reads `CREDENTIALS.txt` and checks every password against the database.
- If it says "matches", you're good to go. If not, re-run `seed.py` and `set_demo_passwords.py`.

### 7. Start the web server
#### Option A: In the terminal (recommended)
```bash
PORT=5055 python3 app.py
```
- `python app.py` starts the Flask web server.
- `PORT=5055` tells it to listen on port 5055 instead of the default 5000.
- **Why 5055?** On macOS, port 5000 is usually taken by AirPlay/ControlCenter. Using 5055 avoids a conflict.

#### Option B: In VS Code
- If you're using Visual Studio Code, you can run the app from the integrated terminal:
  1. Open VS Code
  2. Open the folder `~/Documents/university_portal`
  3. Press `Ctrl + ` (backtick) to open the terminal inside VS Code
  4. Type the same commands as above: `source venv/bin/activate && PORT=5055 python app.py`

### 8. Open the portal in your browser
After the server starts, it will print a URL — usually:
```
 * Running on http://127.0.0.1:5055/ (Press CTRL+C to quit)
```

Open that URL in your web browser (Chrome, Safari, Firefox). You should see the login page.

---

## Logging in

All accounts have the same passwords. You can see them anytime by reading `CREDENTIALS.txt`:

```bash
cat CREDENTIALS.txt
```

| Username | Password | Role | What you can do |
| --- | --- | --- | --- |
| `admin` | `Admin123!` | admin | Everything: users, audit log, login history, backup |
| `hod` | `Hod123!` | HOD | Department students/teachers/courses, reports |
| `T001` … `T006` | `Teacher123!` | teacher | Own courses, enter marks |
| `101` … `150` | `Student123!` | student | Own marks, profile, change password |

### To log in:
1. Go to `http://127.0.0.1:5055/login` in your browser
2. Type a username (e.g., `101`) and password (`Student123!`)
3. Click the login button

### After login:
- **Student (`101`)**: Goes to `/student` — sees own marks, can change password, cannot edit anything
- **Teacher (`T001`)**: Goes to `/teacher` — sees own courses, can enter marks
- **HOD (`hod`)**: Goes to `/hod` — sees department data, can edit students/teachers
- **Admin (`admin`)**: Goes to `/admin` — full access to everything

### To log out:
- Click the logout link/button on any page

---

## Viewing the database in the terminal

You can see all the tables without leaving the terminal. The portal uses SQLite by default (no MySQL server needed).

### List all tables with row counts
```bash
python tools/show_tables.py --list
```
- Shows: `departments 4`, `teachers 6`, `students 50`, `courses 12`, `enrollments 204`, `users 58`, `audit_log 0`, `login_history 0`

### Show the default 5 tables (department, teacher, student, course, enrollment)
```bash
python tools/show_tables.py
```
- Prints nice formatted tables like you'd see in a practical manual

### Show one table at a time
```bash
python tools/show_tables.py --table users
python tools/show_tables.py --table users --limit 5   # shows first 5 rows only
python tools/show_tables.py --table audit_log --limit 10
python tools/show_tables.py --table login_history --limit 10
```

### Run your own SQL query
```bash
python tools/show_tables.py --sql "SELECT role, COUNT(*) FROM users GROUP BY role"
```
- You can only use `SELECT`, `WITH`, or `PRAGMA` — no `DELETE` or `UPDATE` (to protect the database).

### Using the MySQL command line (if you're on the MySQL engine)
If you switched to MySQL (see the "MySQL mode" section below), you can use the MySQL client:

```bash
mysql -u portal -p university_db
```
- You'll be prompted for the portal password (`PortalDev123!` by default).
- Then you can type SQL commands:
  ```sql
  SHOW TABLES;
  SELECT * FROM students LIMIT 5;
  SELECT role, COUNT(*) FROM users GROUP BY role;
  QUIT
  ```

---

## MySQL mode (alternative to SQLite)

The portal can also run against a real MySQL server instead of the SQLite file. This requires a MySQL server to be running.

### One-time setup (only needs to be done once)

**Step 1: Create the database and user** (run these once in a MySQL terminal)
```sql
CREATE DATABASE university_db CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'portal'@'localhost' IDENTIFIED BY 'PortalDev123!';
GRANT ALL PRIVILEGES ON university_db.* TO 'portal'@'localhost';
FLUSH PRIVILEGES;
```
- `CREATE DATABASE university_db` — creates the database named `university_db`
- `CREATE USER 'portal'@'localhost' IDENTIFIED BY 'PortalDev123!'` — creates a user named `portal` with password `PortalDev123!`
- `GRANT ALL PRIVILEGES ...` — gives that user full access to the database
- The `utf8mb4_bin` collation makes usernames case-sensitive (so `Admin` ≠ `admin`)

**Step 2: Point the portal at MySQL**
Type these environment variables:
```bash
export DB_ENGINE=mysql
export MYSQL_USER=portal
export MYSQL_PASSWORD='PortalDev123!'
export MYSQL_HOST=127.0.0.1          # usually doesn't need changing
export MYSQL_PORT=3306                 # default MySQL port
export MYSQL_DATABASE=university_db    # the database we just created
```

**Step 3: Rebuild the MySQL data**
```bash
python seed.py
```
- This creates the same tables in MySQL that exist in SQLite.

```bash
python set_demo_passwords.py --verify
```
- Checks that `CREDENTIALS.txt` matches the MySQL database.

**Step 4: Start the app**
```bash
PORT=5055 python app.py
```
- Same as before. The portal now connects to MySQL instead of the SQLite file.

**Step 5: Switch back to SQLite (if wanted)**
```bash
unset DB_ENGINE
```
- This tells the portal to go back to using the `university.db` SQLite file.
- The SQLite file is never deleted when MySQL mode is active.

---

## Running the test suite

The portal has 220 tests that check everything works.

### Run all tests
```bash
pytest -q
```
- This runs all 220 tests.
- You should see `220 passed` at the end.
- The tests use a temporary database, so your `university.db` and `CREDENTIALS.txt` are untouched.

### Run the smoke test (logs in as all four roles)
```bash
python tools/smoke_test.py
```
- This tries to log in as admin, HOD, teacher, and student.
- You should see `SMOKE TEST PASSED` with four `PASS` rows.

### Run tests three times to confirm stability
```bash
for i in 1 2 3; do echo "=== Run $i ==="; pytest -q; done
```
- Runs the suite three times in a row.
- Good for confirming the portal is stable.

---

## Stopping the server

When you're done, stop the server:

### If you started it in the terminal
- Press `Ctrl + C` in the terminal where the server is running

### If you started it in the background
```bash
kill %1
```
- This stops the process running on port 5055.

### Check if the port is free
```bash
lsof -nP -iTCP:5055 -sTCP:LISTEN
```
- If it shows nothing, the port is free.
- If it shows a process, use `kill <process_id>` to stop it.

---

## Resetting everything (fresh start)

If you want to start completely fresh:

```bash
python seed.py && python set_demo_passwords.py
```
- Rebuilds the database and sets demo passwords.

```bash
python set_demo_passwords.py --verify
```
- Verifies the credentials file matches.

### To wipe everything and rebuild from scratch
```bash
rm -f university.db
python seed.py && python set_demo_passwords.py
```
- `rm -f university.db` deletes the SQLite database file.
- Then `seed.py` creates a fresh one.
- Then `set_demo_passwords.py` sets the demo passwords.

---

## Troubleshooting (common problems and fixes)

| Problem | Fix |
| --- | --- |
| `PORTAL_FERNET_KEY is not set` and the app exits | Run the `export PORTAL_FERNET_KEY="..."` line from section 4 |
| Browser shows 403 with no portal | Port 5000 is taken by AirPlay. Use `PORT=5055 python app.py` instead |
| `Address already in use` | Another server is already on port 5055. Use `lsof -nP -iTCP:5055 -sTCP:LISTEN` to see it, then `kill <pid>` |
| "Your form expired" page | The CSRF token aged out. Reload the page and submit again |
| `Incorrect username or password` for a known-correct password | Account locked after 5 failed tries. Wait 15 minutes, or admin can clear it |
| `CREDENTIALS.txt does not match` from `--verify` | Re-run `python set_demo_passwords.py`, which rewrites the file from the database |
| Marks show `NULL` | Not entered yet — that's intentional for about a third of enrolments |
| `unable to decrypt` on an ID number | `PORTAL_FERNET_KEY` differs from when the data was written. Re-run `seed.py` with the current key |
| `python: command not found` | Use `python3`, and first activate the venv: `source venv/bin/activate` |
| `220 passed` but smoke test fails | Rerun: `python seed.py && python set_demo_passwords.py && pytest -q && python tools/smoke_test.py` |
| Student login not working | Confirmed working on both SQLite and MySQL. Make sure you're using demo password `Student123!` |

---

## File summary (what each file does)

| File | What it does |
| --- | --- |
| `app.py` | Creates the Flask app, starts the web server |
| `config.py` | Reads environment variables (secret key, Fernet key, timeouts) |
| `db.py` | Connects to the database (SQLite or MySQL), runs SQL queries |
| `schema.sql` | The SQLite database structure (8 tables) |
| `schema_mysql.sql` | The MySQL version of the 8 tables |
| `seed.py` | Builds the sample data, writes `CREDENTIALS.txt` |
| `set_demo_passwords.py` | Sets simple demo passwords, rewrites `CREDENTIALS.txt` |
| `credentials.py` | Single writer/verifier for `CREDENTIALS.txt` |
| `security.py` | Password hashing, Fernet encryption |
| `audit.py` | Writes audit trail entries |
| `repositories/` | SQL queries for each table (users, students, teachers, etc.) |
| `services/` | Business rules (auth, permissions, reports, etc.) |
| `blueprints/` | Web routes per role (`auth`, `student`, `teacher`, `hod`, `admin`) |
| `templates/` | HTML pages (login, student page, error pages, etc.) |
| `static/style.css` | Styling for the web pages |
| `tests/` | 220 pytest test cases |
| `tools/smoke_test.py` | End-to-end login check for all four roles |
| `tools/show_tables.py` | Prints database tables in the terminal |
| `CREDENTIALS.txt` | Generated list of demo accounts (username, password, role) |
| `university.db` | The SQLite database file (created by `seed.py`) |
| `GUIDE.md` | This guide — step-by-step instructions |
| `README.md` | Reference documentation |
| `HANDOFF.md` | Record of all changes made during this session |

---

## Most used commands (cheat sheet)

| Action | Command |
| --- | --- |
| Go to project folder | `cd ~/Documents/university_portal` |
| Activate venv | `source venv/bin/activate` |
| Set keys | `export SECRET_KEY="dev-secret-change-me"`<br>`export PORTAL_FERNET_KEY="Jz5EWERS6MnfMqH3r5LB5bnxb2vEtvK5Wcmut8Q8ncU="` |
| Build database | `python seed.py && python set_demo_passwords.py` |
| Verify passwords | `python set_demo_passwords.py --verify` |
| Start server | `PORT=5055 python app.py` |
| View tables | `python tools/show_tables.py --list` |
| Run tests | `pytest -q` |
| Smoke test | `python tools/smoke_test.py` |
| Logout/server stop | `Ctrl + C` in the terminal |
| Switch to MySQL | `export DB_ENGINE=mysql`<br>`export MYSQL_USER=portal`<br>`export MYSQL_PASSWORD='PortalDev123!'` |
| Go back to SQLite | `unset DB_ENGINE` |

---

## That's it!

You now have everything you need to run the portal, log in, see the database, and use all features. 

**Remember the golden rules:**
1. Always keep the same `PORTAL_FERNET_KEY` or re-seed afterward
2. Use `PORT=5055` because port 5000 is usually taken on Mac
3. Student password is always `Student123!`
4. Run `python set_demo_passwords.py --verify` anytime you're unsure if passwords match
5. Five wrong password attempts lock an account for 15 minutes

If you get stuck, check the "Troubleshooting" table above — it covers the most common problems.

Need help? Look at `CREDENTIALS.txt` for the demo passwords, or re-run `python seed.py && python set_demo_passwords.py` for a fresh start.