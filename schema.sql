-- university_portal/schema.sql
-- University database in 3NF (follows Unit C Experiment 5 design)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    national_id_enc BLOB
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    department_id INTEGER NOT NULL REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id  INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    marks      INTEGER CHECK (marks IS NULL OR marks BETWEEN 0 AND 100),
    PRIMARY KEY (student_id, course_id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student','teacher','hod','admin')),
    student_id INTEGER REFERENCES students(id),
    teacher_id INTEGER REFERENCES teachers(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    actor_username TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    target_label TEXT,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    ip_address TEXT
);

CREATE TABLE IF NOT EXISTS login_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    logged_in_at TEXT NOT NULL,
    success INTEGER NOT NULL,
    ip_address TEXT
);

CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course  ON enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_audit_occurred      ON audit_log(occurred_at);
CREATE INDEX IF NOT EXISTS idx_login_username      ON login_history(username);
