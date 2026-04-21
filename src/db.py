import os, sqlite3
from dotenv import load_dotenv

load_dotenv()

# MySQL config (used when available)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'esg_db'),
}

# Path for local sqlite fallback DB
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, 'dev_esg.db')

# Try to import mysql.connector lazily; if unavailable we'll use sqlite
try:
    import mysql.connector as mysql_connector  # type: ignore
    HAS_MYSQL = True
except Exception:
    HAS_MYSQL = False


def get_conn():
    """Return a DB connection. Prefer MySQL if available and reachable, otherwise fallback to sqlite for local testing."""
    if HAS_MYSQL:
        try:
            return mysql_connector.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                autocommit=True,
            )
        except Exception:
            # fallback to sqlite if mysql server not reachable
            pass

    # sqlite fallback
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(query, params=None, fetch=False):
    conn = get_conn()
    # detect sqlite connection by attribute
    is_sqlite = hasattr(conn, 'execute') and not getattr(conn, 'is_connected', False)

    if is_sqlite:
        # sqlite uses ? placeholders; convert simple %s occurrences to ?
        q = query.replace('%s', '?')
        cur = conn.cursor()
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

    # else assume mysql connector
    cur = conn.cursor(dictionary=True)
    cur.execute(query, params or ())
    if fetch:
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    cur.close()
    conn.close()
    return None


def init_db(sql_path='create_db.sql'):
    # Initialize DB schema. Try MySQL first; if not available use sqlite file.
    if HAS_MYSQL:
        try:
            host_conn = mysql_connector.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                autocommit=True,
            )
            cur = host_conn.cursor()
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            for stmt in sql.split(';'):
                stmt = stmt.strip()
                if not stmt:
                    continue
                cur.execute(stmt)
            cur.close()
            host_conn.close()
            return
        except Exception:
            # fall through to sqlite
            pass

    # sqlite init
    conn = sqlite3.connect(SQLITE_PATH)
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
