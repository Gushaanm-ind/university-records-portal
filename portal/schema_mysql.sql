-- university_portal/schema_mysql.sql
-- The same 3NF university database as schema.sql, for MySQL 8.0.16+ / 9+ / 26+.
--
-- Differences from the SQLite file, and why:
--   * AUTO_INCREMENT instead of AUTOINCREMENT.
--   * VARCHAR(n) instead of TEXT for anything UNIQUE or indexed: MySQL cannot
--     index an unbounded TEXT column.
--   * utf8mb4_bin collation: MySQL's default collation is case-insensitive,
--     which would let "Admin" log in as "admin". Binary collation keeps the
--     case-sensitive behaviour the SQLite database has.
--   * Timestamp columns are VARCHAR(32): the application stores ISO strings
--     such as 2026-11-04T12:01:52.219134, which MySQL DATETIME rejects.
--   * InnoDB enforces foreign keys by itself, so there is no PRAGMA to set.

CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS teachers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    staff_code VARCHAR(16) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    phone VARCHAR(32) NOT NULL,
    department_id INT NOT NULL,
    CONSTRAINT fk_teacher_department FOREIGN KEY (department_id) REFERENCES departments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(16) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    department_id INT NOT NULL,
    national_id_enc BLOB NULL,
    CONSTRAINT fk_student_department FOREIGN KEY (department_id) REFERENCES departments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    title VARCHAR(120) NOT NULL,
    credits INT NOT NULL CHECK (credits > 0),
    teacher_id INT NOT NULL,
    department_id INT NOT NULL,
    CONSTRAINT fk_course_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(id),
    CONSTRAINT fk_course_department FOREIGN KEY (department_id) REFERENCES departments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS enrollments (
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    marks INT NULL CHECK (marks IS NULL OR marks BETWEEN 0 AND 100),
    PRIMARY KEY (student_id, course_id),
    INDEX idx_enrollments_student (student_id),
    INDEX idx_enrollments_course (course_id),
    CONSTRAINT fk_enrollment_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_enrollment_course FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('student','teacher','hod','admin')),
    student_id INT NULL,
    teacher_id INT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    failed_attempts INT NOT NULL DEFAULT 0,
    locked_until VARCHAR(32) NULL,
    last_login_at VARCHAR(32) NULL,
    last_seen_at VARCHAR(32) NULL,
    CONSTRAINT fk_user_student FOREIGN KEY (student_id) REFERENCES students(id),
    CONSTRAINT fk_user_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    occurred_at VARCHAR(32) NOT NULL,
    actor_username VARCHAR(64) NOT NULL,
    actor_role VARCHAR(16) NOT NULL,
    action VARCHAR(32) NOT NULL,
    target_type VARCHAR(32) NULL,
    target_id INT NULL,
    target_label VARCHAR(120) NULL,
    field_changed VARCHAR(64) NULL,
    old_value TEXT NULL,
    new_value TEXT NULL,
    ip_address VARCHAR(64) NULL,
    INDEX idx_audit_occurred (occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS login_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    logged_in_at VARCHAR(32) NOT NULL,
    success TINYINT(1) NOT NULL,
    ip_address VARCHAR(64) NULL,
    INDEX idx_login_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

