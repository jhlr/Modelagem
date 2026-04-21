# Backend (Flask) — ESG model

Instalação rápida:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edite .env com credenciais do MySQL
python app.py
```

Inicializar banco (após configurar `.env`):

```bash
curl -X POST http://localhost:5000/init-db
```

Endpoints principais:
- `POST /init-db` — cria banco e tabelas a partir de `create_db.sql` (requer usuário com privilégios)
- `POST /empresa` — criar empresa (JSON: nome_fantasia, cnpj, cidade, id_empresa_mae)
- `PUT /empresa/<id>` — atualizar empresa
- `DELETE /empresa/<id>` — deletar empresa
- `POST /registro` — criar registro (data_hora, valor_medido, status, id_unidade, id_empresa, id_metrica)
- `PUT /registro/<id>` — atualizar registro
- `DELETE /registro/<id>` — deletar registro
- Consultas de exemplo:
  - `GET /query/auditoria`
  - `GET /query/media_por_categoria`
  - `GET /query/registros_sem_evidencia`
  - `GET /query/hierarquia_empresas`
- Gráfico:
  - `GET /plot/media_por_categoria.png`

Observações:
- SQL executado é explícito nas rotas (strings). `init-db` usa `create_db.sql`.
- Ajuste `.env` com credenciais antes de executar.
