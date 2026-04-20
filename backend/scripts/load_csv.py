#!/usr/bin/env python3
"""Carrega dados do CSV para o banco MySQL definido em .env usando o schema em create_db.sql.

Comportamento simples e legível (para trabalho acadêmico):
- Cria uma `Categoria` chamada 'Geral' (Governanca) e uma `Metrica` 'Indicador Geral' se não existirem.
- Para cada linha do CSV: upsert em `Empresa` (por CNPJ), garante uma `Unidade` (id_unidade=1) e insere um `Registro` apontando para a métrica criada.

Uso:
  source .venv/bin/activate
  python3 backend/scripts/load_csv.py ../AlteradForms_Diagnostico_de_Sustentabilidade_MODELO.csv
"""

import sys
import os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import get_conn


CSV_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'AlteradForms_Diagnostico_de_Sustentabilidade_MODELO.csv')


def parse_datetime(val):
    try:
        return pd.to_datetime(val)
    except Exception:
        return None


def get_or_create_categoria_metric(conn):
    cur = conn.cursor()
    # Categoria 'Geral'
    cur.execute("SELECT id_categoria FROM Categoria WHERE descricao=%s", ('Geral',))
    r = cur.fetchone()
    if r:
        id_cat = r[0]
    else:
        cur.execute("INSERT INTO Categoria (descricao, tipo) VALUES (%s,%s)", ('Geral', 'Governanca'))
        id_cat = cur.lastrowid

    # Metrica 'Indicador Geral'
    cur.execute("SELECT id_metrica FROM Metrica WHERE nome=%s", ('Indicador Geral',))
    r = cur.fetchone()
    if r:
        id_met = r[0]
    else:
        cur.execute("INSERT INTO Metrica (nome, descricao, id_categoria) VALUES (%s,%s,%s)", ('Indicador Geral', 'Métrica genérica importada do CSV', id_cat))
        id_met = cur.lastrowid
    cur.close()
    return id_cat, id_met


def get_or_create_empresa(conn, nome, cnpj):
    cur = conn.cursor()
    cur.execute("SELECT id_empresa FROM Empresa WHERE cnpj=%s", (cnpj,))
    r = cur.fetchone()
    if r:
        id_emp = r[0]
    else:
        cur.execute("INSERT INTO Empresa (nome_fantasia, cnpj, cidade) VALUES (%s,%s,%s)", (nome, cnpj, None))
        id_emp = cur.lastrowid
    cur.close()
    return id_emp


def ensure_unidade(conn, id_empresa):
    cur = conn.cursor()
    # We'll use id_unidade = 1 as default unit per company
    cur.execute("SELECT 1 FROM Unidade WHERE id_unidade=%s AND id_empresa=%s", (1, id_empresa))
    if not cur.fetchone():
        cur.execute("INSERT INTO Unidade (id_unidade, id_empresa, nome_unidade, localizacao) VALUES (%s,%s,%s,%s)", (1, id_empresa, 'Matriz', None))
    cur.close()


def insert_registro(conn, data_hora, valor_medido, status, id_unidade, id_empresa, id_metrica):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Registro (data_hora, valor_medido, status, id_unidade, id_empresa, id_metrica) VALUES (%s,%s,%s,%s,%s,%s)",
        (data_hora, valor_medido, status, id_unidade, id_empresa, id_metrica),
    )
    cur.close()


def main(csv_path):
    csv_path = csv_path or CSV_DEFAULT
    if not os.path.exists(csv_path):
        print('CSV não encontrado:', csv_path)
        return

    print('Lendo CSV:', csv_path)
    df = pd.read_csv(csv_path)

    conn = get_conn()
    try:
        id_cat, id_met = get_or_create_categoria_metric(conn)
        print('Categoria id', id_cat, 'Metrica id', id_met)

        inserted = 0
        for _, row in df.iterrows():
            cnpj = str(row.get('cnpj') or '').strip()
            nome = row.get('razao_social') or row.get('nome') or 'Empresa sem nome'
            id_emp = get_or_create_empresa(conn, nome, cnpj)
            ensure_unidade(conn, id_emp)

            # parse data
            dt = parse_datetime(row.get('hora_inicio') or row.get('hora_conclusao'))
            if pd.isna(dt):
                dt = None

            # valor_medido left null (não há métrica numérica direta no CSV)
            valor = None
            status = 'PENDENTE'

            insert_registro(conn, dt, valor, status, 1, id_emp, id_met)
            inserted += 1

        print(f'Inseridos {inserted} registros (empresas/unidades criadas quando necessário).')
    finally:
        conn.close()


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        main(path)
    except Exception as e:
        print('Erro durante import:', e)
        raise
