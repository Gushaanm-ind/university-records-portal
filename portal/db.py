# university_portal/db.py
"""
Database access for the portal.

Two engines are supported, chosen with the DB_ENGINE environment variable:

    DB_ENGINE=sqlite   (default) one file: university.db, no server needed
    DB_ENGINE=mysql    a running MySQL server (see README / GUIDE)

The rest of the application talks to `get_db()` and uses sqlite3-style calls:

    conn.execute("SELECT ... WHERE id = ?", (id,)).fetchone()
    row["username"]  and  row[0]

so the MySQL branch below wraps a PyMySQL connection in a small adapter that
accepts exactly those calls. That keeps repositories, services and blueprints
identical on both engines instead of rewriting every query.
"""
import os
import sqlite3

from portal.config import Config

ENGINES = ("sqlite", "mysql")


def engine():
    """Which engine this process is configured to use."""
    name = (Config.DB_ENGINE or "sqlite").strip().lower()
    if name not in ENGINES:
        raise ValueError(
            f"DB_ENGINE={Config.DB_ENGINE!r} is not supported. Use 'sqlite' or 'mysql'."
        )
    return name


def using_mysql():
    return engine() == "mysql"


def database_path():
    """Resolve the SQLite database path at call time.

    Reading Config.DATABASE lazily (instead of caching it at import) lets tests
    and tools point the application at a different database file safely.
    """
    return Config.DATABASE


class Row(dict):
    """A result row that behaves like sqlite3.Row.

    The application reads columns by name (`row["username"]`, and Jinja's
    `row.field`) but a few places read by position (`row[0]`), so this keeps
    both working over a MySQL DictCursor.
    """

    __slots__ = ("_values",)

    def __init__(self, data, columns):
        super().__init__(data)
        self._values = tuple(data[column] for column in columns)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)

    def __repr__(self):
        return f"Row({dict.__repr__(self)})"


class MySQLCursor:
    """sqlite3-flavoured cursor over a PyMySQL cursor."""

    def __init__(self, raw):
        self._raw = raw

    @property
    def description(self):
        return self._raw.description

    @property
    def rowcount(self):
        return self._raw.rowcount

    @property
    def lastrowid(self):
        return self._raw.lastrowid

    def _wrap(self, data):
        if data is None:
            return None
        columns = [column[0] for column in self._raw.description] if self._raw.description else []
        return Row(data, columns)

    def fetchone(self):
        return self._wrap(self._raw.fetchone())

    def fetchall(self):
        return [self._wrap(row) for row in self._raw.fetchall()]

    def __iter__(self):
        for row in self._raw:
            yield self._wrap(row)


def _to_mysql_sql(sql):
    """Turn sqlite3 placeholders into PyMySQL ones (the queries have no % literals)."""
    return sql.replace("%", "%%").replace("?", "%s")


def split_statements(script):
    """Split a .sql file into single statements, ignoring -- comments."""
    statements, buffer = [], []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            buffer = []
    tail = "\n".join(buffer).strip().rstrip(";").strip()
    if tail:
        statements.append(tail)
    return statements


class MySQLConnection:
    """A connection object with the sqlite3 methods this project uses."""

    def __init__(self, raw):
        self._raw = raw

    def _cursor(self):
        import pymysql.cursors

        return self._raw.cursor(pymysql.cursors.DictCursor)

    def execute(self, sql, params=None):
        cursor = self._cursor()
        if params:
            cursor.execute(_to_mysql_sql(sql), tuple(params))
        else:
            cursor.execute(sql)
        return MySQLCursor(cursor)

    def executescript(self, script):
        for statement in split_statements(script):
            self.execute(statement)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def _mysql_connect():
    try:
        import pymysql
    except ImportError as error:  # pragma: no cover - setup error
        raise RuntimeError(
            "DB_ENGINE=mysql needs the PyMySQL driver. Install it with:\n"
            "    pip install -r requirements.txt"
        ) from error

    try:
        raw = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except pymysql.err.OperationalError as error:
        raise RuntimeError(
            "Cannot reach MySQL with the current settings "
            f"({Config.MYSQL_USER}@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/"
            f"{Config.MYSQL_DATABASE}).\n"
            "Check that MySQL is running (brew services list) and that "
            "MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE are exported.\n"
            f"Driver said: {error}"
        ) from error
    return MySQLConnection(raw)


def get_db():
    if using_mysql():
        return _mysql_connect()
    conn = sqlite3.connect(database_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def schema_file():
    """The schema for the configured engine."""
    name = "schema_mysql.sql" if using_mysql() else "schema.sql"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def init_db():
    with open(schema_file(), "r", encoding="utf-8") as handle:
        sql = handle.read()
    conn = get_db()
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
