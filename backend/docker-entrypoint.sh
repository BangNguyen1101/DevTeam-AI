#!/bin/sh
# Wait for SQL Server, create the database if needed, migrate, then serve.
set -e

python - <<'PY'
import time

import pyodbc

from app.core.config import get_settings

s = get_settings()
conn_str = (
    f"DRIVER={{{s.db_driver}}};SERVER={s.db_server};DATABASE=master;UID={s.db_user};"
    f"PWD={s.db_password.get_secret_value()};TrustServerCertificate=yes"
)
for attempt in range(60):
    try:
        conn = pyodbc.connect(conn_str, autocommit=True, timeout=5)
        break
    except pyodbc.Error as exc:
        print(f"Waiting for SQL Server ({attempt + 1}/60): {exc.args[0]}", flush=True)
        time.sleep(3)
else:
    raise SystemExit("SQL Server is not reachable")
if conn.execute("SELECT DB_ID(?)", s.db_name).fetchval() is None:
    conn.execute(f"CREATE DATABASE [{s.db_name}]")
    print(f"Created database {s.db_name}", flush=True)
PY

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
