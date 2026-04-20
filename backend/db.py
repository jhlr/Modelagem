import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'esg_db'),
}


def get_conn():
    return mysql.connector.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        autocommit=True,
    )


def execute(query, params=None, fetch=False):
    conn = get_conn()
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
    # initialize DB by running script (requires privileges)
    host_conn = mysql.connector.connect(
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
