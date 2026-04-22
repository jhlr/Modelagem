#!/usr/bin/env python3
from pathlib import Path
import csv
import argparse
import sys
from src import db

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_SQL = Path(__file__).resolve().parent / 'create_esg_kaggle.sql'
DATA_CSV = BASE_DIR / 'dataset' / 'data.csv'

CATEGORY_NAME = 'esg'
METRICS = ['environment_score', 'social_score', 'governance_score', 'total_score']


def ensure_schema():
    if not SCHEMA_SQL.exists():
        raise FileNotFoundError(f"Schema SQL not found: {SCHEMA_SQL}")
    db.init_db(str(SCHEMA_SQL))


def ensure_categoria(name):
    r = db.execute('SELECT id FROM Categoria_kaggle WHERE name = ?;', (name,), fetch=True)
    if r:
        return r[0]['id']
    db.execute('INSERT INTO Categoria_kaggle (name) VALUES (?);', (name,))
    r2 = db.execute('SELECT id FROM Categoria_kaggle WHERE name = ?;', (name,), fetch=True)
    return r2[0]['id']


def ensure_metrica(categoria_id, name):
    r = db.execute('SELECT id FROM Metrica_kaggle WHERE categoria_id = ? AND name = ?;', (categoria_id, name), fetch=True)
    if r:
        return r[0]['id']
    db.execute('INSERT INTO Metrica_kaggle (categoria_id, name, unit) VALUES (?, ?, ?);', (categoria_id, name, None))
    r2 = db.execute('SELECT id FROM Metrica_kaggle WHERE categoria_id = ? AND name = ?;', (categoria_id, name), fetch=True)
    return r2[0]['id']


def upsert_empresa(row):
    ticker = (row.get('ticker') or '').strip()
    if not ticker:
        return None
    existing = db.execute('SELECT id FROM Empresa_kaggle WHERE ticker = ?;', (ticker,), fetch=True)
    if existing:
        eid = existing[0]['id']
        db.execute('UPDATE Empresa_kaggle SET name = ?, exchange = ?, industry = ?, weburl = ?, cik = ? WHERE id = ?;'
                   , (row.get('name'), row.get('exchange'), row.get('industry'), row.get('weburl'), row.get('cik'), eid))
        return eid
    db.execute('INSERT INTO Empresa_kaggle (ticker, name, exchange, industry, weburl, cik) VALUES (?, ?, ?, ?, ?, ?);',
               (ticker, row.get('name'), row.get('exchange'), row.get('industry'), row.get('weburl'), row.get('cik')))
    new = db.execute('SELECT id FROM Empresa_kaggle WHERE ticker = ?;', (ticker,), fetch=True)
    return new[0]['id']


def insert_registro(empresa_id, metrica_id, value, recorded_at, source_row):
    db.execute('INSERT INTO Registro_kaggle (empresa_id, metrica_id, value, recorded_at, source_row) VALUES (?, ?, ?, ?, ?);',
               (empresa_id, metrica_id, value, recorded_at, source_row))


def run(limit=None, dry_run=False):
    ensure_schema()
    categoria_id = ensure_categoria(CATEGORY_NAME)
    metrica_map = {}
    for m in METRICS:
        metrica_map[m] = ensure_metrica(categoria_id, m)

    if not DATA_CSV.exists():
        print(f"Data CSV not found: {DATA_CSV}")
        sys.exit(1)

    with open(DATA_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if limit and limit > 0:
        rows = rows[:limit]

    total_rows = len(rows)
    metric_records = 0

    for idx, row in enumerate(rows, start=1):
        ticker = (row.get('ticker') or '').strip()
        if not ticker:
            continue
        if dry_run:
            # Count but do not write
            for m in METRICS:
                v = row.get(m)
                if v is None or v == '':
                    continue
                try:
                    float(v)
                    metric_records += 1
                except Exception:
                    continue
            continue

        empresa_id = upsert_empresa(row)
        if not empresa_id:
            continue
        for m in METRICS:
            v = row.get(m)
            if v is None or v == '':
                continue
            try:
                val = float(v)
            except Exception:
                # sometimes values have commas or other formatting
                try:
                    val = float(v.replace(',', ''))
                except Exception:
                    continue
            metrica_id = metrica_map.get(m)
            insert_registro(empresa_id, metrica_id, val, row.get('last_processing_date'), idx)
            metric_records += 1

    if not dry_run:
        db.execute('INSERT INTO ImportAudit_kaggle (source_file, row_count, metric_records) VALUES (?, ?, ?);', (str(DATA_CSV), total_rows, metric_records))

    print(f"Processed rows: {total_rows}, metric records counted/inserted: {metric_records}, dry_run={dry_run}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=50, help='Limit number of rows to process; 0 means all')
    p.add_argument('--dry-run', action='store_true', help='Do not write to DB')
    args = p.parse_args()
    limit = args.limit if args.limit and args.limit > 0 else None
    run(limit=limit, dry_run=args.dry_run)
