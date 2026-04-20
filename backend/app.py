from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from db import execute, init_db
import os
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

app = Flask(__name__)
CORS(app)


@app.route('/init-db', methods=['POST'])
def route_init_db():
    sql_path = os.path.join(os.path.dirname(__file__), 'create_db.sql')
    try:
        init_db(sql_path)
        return jsonify({'status': 'ok', 'msg': 'db initialized'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


# CRUD Empresa (insertion, update, delete)
@app.route('/empresa', methods=['POST'])
def create_empresa():
    data = request.json or {}
    sql = "INSERT INTO Empresa (nome_fantasia, cnpj, cidade, id_empresa_mae) VALUES (%s,%s,%s,%s)"
    params = (data.get('nome_fantasia'), data.get('cnpj'), data.get('cidade'), data.get('id_empresa_mae'))
    execute(sql, params)
    return jsonify({'status': 'created'})


@app.route('/empresa/<int:id_empresa>', methods=['PUT'])
def update_empresa(id_empresa):
    data = request.json or {}
    sql = "UPDATE Empresa SET nome_fantasia=%s, cnpj=%s, cidade=%s, id_empresa_mae=%s WHERE id_empresa=%s"
    params = (data.get('nome_fantasia'), data.get('cnpj'), data.get('cidade'), data.get('id_empresa_mae'), id_empresa)
    execute(sql, params)
    return jsonify({'status': 'updated'})


@app.route('/empresa/<int:id_empresa>', methods=['DELETE'])
def delete_empresa(id_empresa):
    sql = "DELETE FROM Empresa WHERE id_empresa=%s"
    execute(sql, (id_empresa,))
    return jsonify({'status': 'deleted'})


# CRUD Registro (insertion, update, delete)
@app.route('/registro', methods=['POST'])
def create_registro():
    data = request.json or {}
    sql = "INSERT INTO Registro (data_hora, valor_medido, status, id_unidade, id_empresa, id_metrica) VALUES (%s,%s,%s,%s,%s,%s)"
    params = (data.get('data_hora'), data.get('valor_medido'), data.get('status','PENDENTE'), data.get('id_unidade'), data.get('id_empresa'), data.get('id_metrica'))
    execute(sql, params)
    return jsonify({'status': 'created'})


@app.route('/registro/<int:id_registro>', methods=['PUT'])
def update_registro(id_registro):
    data = request.json or {}
    sql = "UPDATE Registro SET data_hora=%s, valor_medido=%s, status=%s WHERE id_registro=%s"
    params = (data.get('data_hora'), data.get('valor_medido'), data.get('status'), id_registro)
    execute(sql, params)
    return jsonify({'status': 'updated'})


@app.route('/registro/<int:id_registro>', methods=['DELETE'])
def delete_registro(id_registro):
    sql = "DELETE FROM Registro WHERE id_registro=%s"
    execute(sql, (id_registro,))
    return jsonify({'status': 'deleted'})


### Queries required (at least 4) ###

@app.route('/query/auditoria', methods=['GET'])
def query_auditoria():
    sql = (
        "SELECT e.nome_fantasia AS empresa, r.data_hora, r.valor_medido, a.nome AS nome_auditor "
        "FROM Registro r "
        "JOIN Empresa e ON r.id_empresa = e.id_empresa "
        "JOIN Auditoria_Registro ar ON r.id_registro = ar.id_registro "
        "JOIN Auditoria ad ON ar.id_auditoria = ad.id_auditoria "
        "JOIN Auditor a ON ad.cpf_auditor = a.cpf "
        "WHERE r.status = 'VALIDADO'"
    )
    rows = execute(sql, fetch=True)
    return jsonify(rows)


@app.route('/query/media_por_categoria', methods=['GET'])
def query_media():
    sql = (
        "SELECT c.tipo, AVG(r.valor_medido) AS media_valor "
        "FROM Registro r "
        "JOIN Metrica m ON r.id_metrica = m.id_metrica "
        "JOIN Categoria c ON m.id_categoria = c.id_categoria "
        "GROUP BY c.tipo"
    )
    rows = execute(sql, fetch=True)
    return jsonify(rows)


@app.route('/query/registros_sem_evidencia', methods=['GET'])
def query_sem_evidencia():
    # assumes table Evidencia may exist; if not, return empty list
    sql = (
        "SELECT id_registro, valor_medido, data_hora "
        "FROM Registro "
        "WHERE valor_medido > 80 "
        "AND id_registro NOT IN (SELECT id_registro FROM Evidencia)"
    )
    try:
        rows = execute(sql, fetch=True)
    except Exception:
        rows = []
    return jsonify(rows)


@app.route('/query/hierarquia_empresas', methods=['GET'])
def query_hierarquia():
    sql = (
        "SELECT sub.nome_fantasia AS subsidiaria, mae.nome_fantasia AS controladora "
        "FROM Empresa sub "
        "LEFT JOIN Empresa mae ON sub.id_empresa_mae = mae.id_empresa"
    )
    rows = execute(sql, fetch=True)
    return jsonify(rows)


@app.route('/plot/media_por_categoria.png', methods=['GET'])
def plot_media_por_categoria():
    data = execute(
        "SELECT c.tipo, AVG(r.valor_medido) AS media_valor FROM Registro r JOIN Metrica m ON r.id_metrica = m.id_metrica JOIN Categoria c ON m.id_categoria = c.id_categoria GROUP BY c.tipo",
        fetch=True,
    )
    if not data:
        abort(404)
    df = pd.DataFrame(data)
    fig, ax = plt.subplots(figsize=(6,4))
    ax.bar(df['tipo'], df['media_valor'])
    ax.set_title('Média de valor por categoria')
    ax.set_ylabel('media_valor')
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
