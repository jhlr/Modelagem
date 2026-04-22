import sqlite3
from pathlib import Path

# Use sqlite3 only. Database file is at repository root `dev_esg.db`.
BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = str(BASE_DIR / "dev_esg.db")


def get_conn():
    """Return a sqlite3 connection, creating parent dir if necessary."""
    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(query, params=None, fetch=False):
    conn = get_conn()
    cur = conn.cursor()
    # sqlite uses ? placeholders; convert simple %s occurrences to ?
    q = query.replace("%s", "?")
    cur.execute(q, params or ())
    if fetch:
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.commit()
        conn.close()
        return rows
    cur.close()
    conn.commit()
    conn.close()
    return None


def init_db(sql_path='create_db.sql'):
    """Initialize sqlite DB using statements from `sql_path`.

    Ignores statements that sqlite cannot execute.
    """
    conn = get_conn()
    cur = conn.cursor()
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            cur.execute(stmt)
        except Exception:
            # ignore statements incompatible with sqlite
            continue
    conn.commit()
    cur.close()
    conn.close()
