#!/usr/bin/env bash
# University Portal — one-command launcher.
#
#   ./run.sh            start (or reuse) the portal and open the browser
#   ./run.sh -n         same, but do not open the browser
#   ./run.sh stop       stop the server
#   ./run.sh restart    restart the server
#   ./run.sh status     show whether it is running
#   ./run.sh logs       last 60 lines of the server log
#   ./run.sh verify     check the demo data and CREDENTIALS.txt
#   ./run.sh test       run the 220-test suite
#   ./run.sh reset      rebuild the database from scratch
#
# Everything the guide used to make you type by hand — virtualenv, pip install,
# environment keys, seeding, port — happens here. Override any value with an
# environment variable or a local .env file: PORT, SECRET_KEY,
# PORTAL_FERNET_KEY, DB_ENGINE, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD,
# MYSQL_DATABASE.
set -u

cd "$(dirname "$0")" || exit 1

# --- optional local overrides ------------------------------------------------
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# Ignore an inherited PORT that is empty, 0 or not a number (some shells and
# IDEs export PORT=0, which makes Flask bind a random port).
case "${PORT:-}" in
  ''|0|*[!0-9]*) PORT=5055 ;;
  *) PORT="$PORT" ;;

esac
HOST="127.0.0.1"
RUN_DIR=".run"
PID_FILE="$RUN_DIR/portal.pid"
LOG_FILE="$RUN_DIR/portal.log"
PY="venv/bin/python"
URL="http://$HOST:$PORT/login"

export PORT
# Demo defaults only; set real values for anything beyond local use.
export SECRET_KEY="${SECRET_KEY:-dev-secret-change-me}"
export PORTAL_FERNET_KEY="${PORTAL_FERNET_KEY:-Jz5EWERS6MnfMqH3r5LB5bnxb2vEtvK5Wcmut8Q8ncU=}"

info() { printf '  %s\n' "$*"; }

open_browser() {
  [ "${NO_OPEN:-0}" = "1" ] && return 0
  if command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1
  else
    info "Open $URL in your browser."
  fi
}

http_ready() {
  curl -fsS --max-time 2 -o /dev/null "$URL" >/dev/null 2>&1
}

pid_alive() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

# Whatever is listening on our port, if anything.
port_pid() {
  lsof -nP -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1
}

# True only for a python app.py started from this project, so stop/restart can
# never kill an unrelated program that happens to use the same port.
is_portal_pid() {
  local pid="$1" cwd
  [ -n "$pid" ] || return 1
  cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
  [ "$cwd" = "$PWD" ] || return 1
  ps -o command= -p "$pid" 2>/dev/null | grep -q "app\.py" || return 1
  return 0
}

# The running portal: our pid file first, so a restart always owns its process.
running_pid() {
  if pid_alive; then
    cat "$PID_FILE"
    return 0
  fi
  local pid
  pid="$(port_pid)"
  if is_portal_pid "$pid"; then
    printf '%s\n' "$pid"
    return 0
  fi
  return 1
}

kill_pid() {
  local pid="$1" tries=0
  kill "$pid" 2>/dev/null
  while kill -0 "$pid" 2>/dev/null && [ "$tries" -lt 40 ]; do
    sleep 0.25
    tries=$((tries + 1))
  done
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
  return 0
}

ensure_venv() {
  if [ ! -x "$PY" ]; then
    info "Creating the virtual environment (first run only)..."
    python3 -m venv venv || { echo "Could not create venv. Is python3 installed?" >&2; exit 1; }
  fi
}

ensure_deps() {
  # Cheap import check instead of running pip on every launch.
  if ! "$PY" -c "import flask, flask_wtf, cryptography, pymysql" >/dev/null 2>&1; then
    info "Installing Python packages (first run only)..."
    "$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
    "$PY" -m pip install --quiet -r requirements.txt || { echo "pip install failed." >&2; exit 1; }
  fi
}

ensure_db() {
  [ "${DB_ENGINE:-sqlite}" = "mysql" ] && return 0
  if [ ! -s university.db ]; then
    info "Creating the demo database and accounts (first run only)..."
    "$PY" seed.py >/dev/null || { echo "seed.py failed." >&2; exit 1; }
    "$PY" set_demo_passwords.py >/dev/null || { echo "set_demo_passwords.py failed." >&2; exit 1; }
  fi
}

start() {
  ensure_venv
  ensure_deps
  ensure_db
  mkdir -p "$RUN_DIR"

  if http_ready; then
    local pid
    pid="$(running_pid)" && echo "$pid" >"$PID_FILE"
    echo "Portal is already running -> $URL"
    open_browser
    return 0
  fi

  info "Starting the portal ..."
  nohup "$PY" app.py >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"

  local tries=0
  while [ "$tries" -lt 40 ]; do
    http_ready && break
    sleep 0.25
    tries=$((tries + 1))
  done

  if http_ready; then
    echo "Ready -> $URL   (pid $(cat "$PID_FILE"))"
    echo "Stop it with: ./run.sh stop"
    open_browser
  else
    echo "The portal did not start. Last log lines:" >&2
    tail -n 20 "$LOG_FILE" >&2
    return 1
  fi
}

stop() {
  local pid
  if pid="$(running_pid)"; then
    kill_pid "$pid"
    rm -f "$PID_FILE"
    echo "Portal stopped."
    return 0
  fi
  if [ -f "$PID_FILE" ]; then
    rm -f "$PID_FILE"
    echo "Portal was not running (removed a stale pid file)."
    return 0
  fi
  if [ -n "$(port_pid)" ]; then
    echo "Port $PORT belongs to another program; the portal was left alone." >&2
    echo "Free the port or run with PORT=<another number> ./run.sh" >&2
    return 1
  fi
  echo "Portal is not running."
}

status() {
  local pid
  if http_ready; then
    echo "Running -> $URL"
    if pid="$(running_pid)"; then echo "  pid $pid"; fi
    echo "  log: $LOG_FILE"
  elif pid="$(running_pid)"; then
    echo "Starting ... (pid $pid)"
  else
    echo "Stopped. Start it with: ./run.sh"
  fi
}

verify() {
  ensure_venv
  ensure_deps
  echo "Tables:"
  "$PY" tools/show_tables.py --list
  echo
  echo "Accounts vs CREDENTIALS.txt:"
  "$PY" set_demo_passwords.py --verify
}

reset() {
  stop
  echo "Rebuilding the database from scratch ..."
  rm -f university.db
  ensure_venv
  ensure_deps
  "$PY" seed.py && "$PY" set_demo_passwords.py && "$PY" set_demo_passwords.py --verify
}

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
}

case "${1:-start}" in
  start|up|"") start ;;
  -n|--no-open) NO_OPEN=1; export NO_OPEN; start ;;
  stop|down) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) tail -n 60 "$LOG_FILE" 2>/dev/null || echo "No log yet. Start the portal first." ;;
  verify|check) verify ;;
  test|tests) ensure_venv; ensure_deps; "$PY" -m pytest -q ;;
  reset|seed) reset ;;
  -h|--help|help) usage ;;
  *) echo "Unknown option: $1" >&2; echo; usage; exit 1 ;;
esac
