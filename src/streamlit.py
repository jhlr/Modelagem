import pandas as pd, numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import re

try: from . import db
except Exception:
	import db


def safe_rerun():
	fn = getattr(st, "experimental_rerun", None) \
		or getattr(st, "rerun", None)  # fallback to older name if available
	if fn: return fn()
	# fallback: set a flag and stop execution; the client will rerun on next interaction
	st.session_state._needs_rerun = True
	st.stop()

# file is stored at repository root (project parent of src)
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR.parent / "AlteradForms_Diagnostico_de_Sustentabilidade_MODELO.csv"


def resolve_table(name):
	"""Return actual table name in sqlite matching `name` case-insensitively, or None."""
	rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND lower(name)=%s", (name.lower(),), fetch=True)
	if rows:
		return rows[0]['name']
	return None


def load_companies():
	tbl = resolve_table('empresa') or resolve_table('Empresa')
	if not tbl:
		return pd.DataFrame()
	q = f"SELECT id_empresa, nome_fantasia, cnpj, cidade, id_empresa_mae FROM {tbl} ORDER BY id_empresa"
	rows = db.execute(q, fetch=True)
	return pd.DataFrame(rows)


def create_empresa(nome, cnpj, cidade, id_mae):
	tbl = resolve_table('empresa') or resolve_table('Empresa')
	if not tbl:
		raise RuntimeError("Tabela 'Empresa' não encontrada no DB")
	db.execute(
		f"INSERT INTO {tbl} (nome_fantasia, cnpj, cidade, id_empresa_mae) VALUES (%s, %s, %s, %s)",
		(nome, cnpj or None, cidade or None, id_mae or None),
	)


def update_empresa(id_empresa, nome, cnpj, cidade, id_mae):
	tbl = resolve_table('empresa') or resolve_table('Empresa')
	if not tbl:
		raise RuntimeError("Tabela 'Empresa' não encontrada no DB")
	db.execute(
		f"UPDATE {tbl} SET nome_fantasia=%s, cnpj=%s, cidade=%s, id_empresa_mae=%s WHERE id_empresa=%s",
		(nome, cnpj or None, cidade or None, id_mae or None, id_empresa),
	)


def delete_empresa(id_empresa):
	tbl = resolve_table('empresa') or resolve_table('Empresa')
	if not tbl:
		raise RuntimeError("Tabela 'Empresa' não encontrada no DB")
	db.execute(f"DELETE FROM {tbl} WHERE id_empresa=%s", (id_empresa,))


def contagem_sim_por_pergunta_estratificado():
	if not CSV_PATH.exists():
		st.error(f"CSV não encontrado: {CSV_PATH}")
		return pd.DataFrame()

	df = pd.read_csv(CSV_PATH, dtype=str)
	# columns expected: pergunta, resposta, validado (or similar). Try to infer.
	# We'll look for columns containing 'pergunta' and 'resposta' or 'validado'
	cols = [c.lower() for c in df.columns]
	# heuristics
	pergunta_col = next((c for c in df.columns if 'pergunta' in c.lower()), None)
	resposta_col = next((c for c in df.columns if 'resposta' in c.lower() or 'resposta' in c.lower()), None)
	validado_col = next((c for c in df.columns if 'valid' in c.lower()), None)

	# fallback guesses
	if pergunta_col is None:
		pergunta_col = df.columns[0]
	if resposta_col is None:
		# try a column that looks like answer
		resposta_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

	# Normalize
	q = df[pergunta_col].astype(str)
	a = df[resposta_col].astype(str).str.lower()
	v = df[validado_col].astype(str).str.lower() if validado_col else pd.Series([''] * len(df))

	# define 'sim' as responses containing 'sim' substring
	sim_mask = a.str.contains('sim', na=False)
	valid_mask = v.str.contains('sim|true|1', na=False)

	# We'll compute counts manually per pergunta
	df2 = pd.DataFrame({'pergunta': q, 'sim': sim_mask, 'validado': valid_mask})
	res = (
		df2.groupby('pergunta')
		.apply(lambda g: pd.Series({
			'sim_validado': int(((g['sim']) & (g['validado'])).sum()),
			'sim_nao_validado': int(((g['sim']) & (~g['validado'])).sum()),
		}))
		.reset_index()
	)
	return res


def render_dashboard():
	st.title('ESG Dashboard')
	st.write('Visualizações estratificadas das respostas')
	df = contagem_sim_por_pergunta_estratificado()
	if df.empty:
		st.info('Nenhum CSV de respostas encontrado — mostrando painel ESG (Kaggle) se disponível.')
	else:
		fig = px.bar(
			df,
			x='pergunta',
			y=['sim_validado', 'sim_nao_validado'],
			title='Contagem de "Sim" por Pergunta (validados vs não validados)',
			labels={'value': 'Contagem', 'pergunta': 'Pergunta'},
		)
		st.plotly_chart(fig, use_container_width=True)

	# ESG (Kaggle) panel
	st.header('ESG (Kaggle) — Overview')
	# check for kaggle tables
	t = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Empresa_kaggle'", fetch=True)
	if not t:
		st.info('Tabelas Kaggle não encontradas no DB.')
		return

	# Load metrics into dataframe
	rows = db.execute(
		'SELECT e.id AS empresa_id, e.ticker, e.name AS empresa_name, e.industry, m.name AS metric, r.value, r.recorded_at FROM Registro_kaggle r JOIN Metrica_kaggle m ON r.metrica_id = m.id JOIN Empresa_kaggle e ON r.empresa_id = e.id',
		fetch=True,
	)
	dfm = pd.DataFrame(rows)
	if dfm.empty:
		st.info('Nenhum registro Kaggle encontrado.')
		return

	# pivot: one row per company with metric columns
	pivot = dfm.pivot_table(index=['empresa_id', 'ticker', 'empresa_name', 'industry'], columns='metric', values='value', aggfunc='mean').reset_index()

	# Sidebar filters
	st.sidebar.subheader('ESG Filters')
	industries = ['All'] + sorted(pivot['industry'].dropna().unique().tolist())
	sel_ind = st.sidebar.selectbox('Industry', industries, index=0)
	top_n = st.sidebar.slider('Top N empresas (por total_score)', 5, 50, 10)

	filt = pivot.copy()
	if sel_ind and sel_ind != 'All':
		filt = filt[filt['industry'] == sel_ind]

	# KPI cards
	cols = st.columns(4)
	metrics = ['environment_score', 'social_score', 'governance_score', 'total_score']
	for c, m in zip(cols, metrics):
		if m in filt.columns:
			val = float(filt[m].mean())
			c.metric(m.replace('_', ' ').title(), f"{val:.1f}")
		else:
			c.metric(m.replace('_', ' ').title(), 'n/a')

	# Top N bar chart (by total_score)
	if 'total_score' in filt.columns:
		top = filt.nlargest(top_n, 'total_score')[['ticker', 'empresa_name', 'total_score']]
		fig_top = px.bar(top.sort_values('total_score'), x='total_score', y='empresa_name', orientation='h', title=f'Top {top_n} empresas por Total Score')
		st.plotly_chart(fig_top, use_container_width=True)

	# Histogram of a selected metric
	metric_choice = st.selectbox('Distribuição — escolha métrica', metrics, index=3)
	if metric_choice in filt.columns:
		fig_hist = px.histogram(filt, x=metric_choice, nbins=30, title=f'Distribuição de {metric_choice}')
		st.plotly_chart(fig_hist, use_container_width=True)

	# Company selector + radar
	st.subheader('Perfil de Empresa (Radar)')
	company_opts = filt[['empresa_id', 'ticker', 'empresa_name']].drop_duplicates()
	sel_comp = st.selectbox('Escolha empresa', options=company_opts['empresa_id'].tolist(), format_func=lambda i: company_opts[company_opts['empresa_id']==i]['ticker'].values[0])
	comp_row = filt[filt['empresa_id'] == sel_comp].iloc[0]
	radar_metrics = [m for m in metrics if m in filt.columns]
	if radar_metrics:
		r = [float(comp_row.get(m) or 0) for m in radar_metrics]
		theta = [m.replace('_', ' ').title() for m in radar_metrics]
		fig_radar = go.Figure(data=go.Scatterpolar(r=r + [r[0]], theta=theta + [theta[0]], fill='toself'))
		fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=False, title=f'Perfil ESG — {comp_row.ticker} ({comp_row.empresa_name})')
		st.plotly_chart(fig_radar, use_container_width=True)

	# Download filtered table
	csv_buf = filt.to_csv(index=False).encode('utf-8')
	st.download_button('Download CSV filtrado', data=csv_buf, file_name='esg_companies.csv', mime='text/csv')


def render_empresas():
	st.header('Empresas (CRUD)')
	df = load_companies()
	st.write('Total empresas:', len(df))
	st.dataframe(df)

	st.subheader('Adicionar nova empresa')
	with st.form('add_empresa'):
		nome = st.text_input('Nome fantasia')
		cnpj = st.text_input('CNPJ')
		cidade = st.text_input('Cidade')
		id_mae = st.text_input('ID empresa mãe (opcional)')
		submitted = st.form_submit_button('Adicionar')
		if submitted:
			create_empresa(nome, cnpj, cidade, int(id_mae) if id_mae else None)
			safe_rerun()

	st.subheader('Editar / Apagar')
	ids = df['id_empresa'].tolist() if not df.empty else []
	if ids:
		sel = st.selectbox('Escolha empresa', options=ids)
		row = df[df['id_empresa'] == sel].iloc[0]
		with st.form('edit_empresa'):
			nome2 = st.text_input('Nome fantasia', value=row['nome_fantasia'])
			cnpj2 = st.text_input('CNPJ', value=row['cnpj'] if pd.notna(row['cnpj']) else '')
			cidade2 = st.text_input('Cidade', value=row['cidade'] if pd.notna(row['cidade']) else '')
			id_mae2 = st.text_input('ID empresa mãe', value=str(row['id_empresa_mae']) if pd.notna(row['id_empresa_mae']) else '')
			upd = st.form_submit_button('Atualizar')
			if upd:
				update_empresa(sel, nome2, cnpj2, cidade2, int(id_mae2) if id_mae2 else None)
				safe_rerun()
		if st.button('Apagar empresa selecionada'):
			delete_empresa(sel)
			safe_rerun()


def render_auditoria():
	st.header('Auditoria')
	# check table exists (case-insensitive)
	t = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND lower(name)='auditoria'", fetch=True)
	if not t:
		st.info("Tabela 'Auditoria' não encontrada no DB. Use DB -> Inicializar DB (create_db.sql) ou crie a tabela manualmente.")
		return
	rows = db.execute('SELECT * FROM Auditoria LIMIT 500', fetch=True)
	st.dataframe(pd.DataFrame(rows))


def render_hierarquia():
	st.header('Hierarquia de Empresas')
	tbl = resolve_table('empresa') or resolve_table('Empresa')
	if not tbl:
		st.info("Tabela 'Empresa' não encontrada no DB. Use DB -> Inicializar DB (create_db.sql) ou crie a tabela manualmente.")
		return
	rows = db.execute(f'SELECT id_empresa, nome_fantasia, id_empresa_mae FROM {tbl} ORDER BY id_empresa', fetch=True)
	st.dataframe(pd.DataFrame(rows))


def load_unidades():
	t = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Unidade'", fetch=True)
	if not t:
		return pd.DataFrame()
	rows = db.execute('SELECT id_unidade, id_empresa, nome_unidade, localizacao FROM Unidade ORDER BY id_empresa, id_unidade', fetch=True)
	return pd.DataFrame(rows)


def create_unidade(id_unidade, id_empresa, nome_unidade, localizacao):
	db.execute(
		'INSERT INTO Unidade (id_unidade, id_empresa, nome_unidade, localizacao) VALUES (%s, %s, %s, %s)',
		(id_unidade, id_empresa, nome_unidade or None, localizacao or None),
	)


def update_unidade(old_id_unidade, old_id_empresa, id_unidade, id_empresa, nome_unidade, localizacao):
	db.execute(
		'UPDATE Unidade SET id_unidade=%s, id_empresa=%s, nome_unidade=%s, localizacao=%s WHERE id_unidade=%s AND id_empresa=%s',
		(id_unidade, id_empresa, nome_unidade or None, localizacao or None, old_id_unidade, old_id_empresa),
	)


def delete_unidade(id_unidade, id_empresa):
	db.execute('DELETE FROM Unidade WHERE id_unidade=%s AND id_empresa=%s', (id_unidade, id_empresa))


def render_unidades():
	st.header('Unidades (CRUD)')
	df = load_unidades()
	if df.empty:
		st.info('Tabela `Unidade` não encontrada ou sem registros. Use o botão DB->Inicializar DB se necessário.')
		return

	st.write('Total unidades:', len(df))
	st.dataframe(df)

	st.subheader('Adicionar nova unidade')
	with st.form('add_unidade'):
		id_un = st.number_input('ID Unidade', min_value=1, value=1)
		id_emp = st.number_input('ID Empresa', min_value=1, value=1)
		nome = st.text_input('Nome unidade')
		loc = st.text_input('Localização')
		submitted = st.form_submit_button('Adicionar')
		if submitted:
			create_unidade(int(id_un), int(id_emp), nome, loc)
			safe_rerun()

	st.subheader('Editar / Apagar')
	ids = df[['id_unidade', 'id_empresa']].apply(lambda r: f"{r['id_unidade']}|{r['id_empresa']}", axis=1).tolist()
	if ids:
		sel = st.selectbox('Escolha unidade (id_unidade|id_empresa)', options=ids)
		id_u, id_e = sel.split('|')
		row = df[(df['id_unidade'] == int(id_u)) & (df['id_empresa'] == int(id_e))].iloc[0]
		with st.form('edit_unidade'):
			id_un2 = st.number_input('ID Unidade', min_value=1, value=int(row['id_unidade']))
			id_emp2 = st.number_input('ID Empresa', min_value=1, value=int(row['id_empresa']))
			nome2 = st.text_input('Nome unidade', value=row['nome_unidade'] if pd.notna(row['nome_unidade']) else '')
			loc2 = st.text_input('Localização', value=row['localizacao'] if pd.notna(row['localizacao']) else '')
			upd = st.form_submit_button('Atualizar')
			if upd:
				update_unidade(int(id_u), int(id_e), int(id_un2), int(id_emp2), nome2, loc2)
				safe_rerun()
		if st.button('Apagar unidade selecionada'):
			delete_unidade(int(id_u), int(id_e))
			safe_rerun()


def render_consultas():
	st.header('Consultas pré-definidas')

	# Define 4 queries (one includes a join)
	queries = {
		'1 - Contagem de empresas por cidade': {
			'sql': 'SELECT cidade, COUNT(*) AS total_empresas FROM Empresa GROUP BY cidade ORDER BY total_empresas DESC',
			'type': 'bar_city',
			'tables': ['Empresa']
		},
		'2 - Unidades por empresa (join Empresa <> Unidade)': {
			'sql': 'SELECT e.id_empresa AS empresa_id, e.nome_fantasia AS empresa_nome, COUNT(u.id_unidade) AS total_unidades FROM Empresa e LEFT JOIN Unidade u ON e.id_empresa = u.id_empresa GROUP BY e.id_empresa, e.nome_fantasia ORDER BY total_unidades DESC',
			'type': 'bar_company',
			'tables': ['Empresa', 'Unidade']
		},
		'3 - Média de valores por métrica (Registro <> Metrica)': {
			'sql': 'SELECT m.id_metrica AS metrica_id, m.nome AS metrica_nome, AVG(r.valor_medido) AS media_valor FROM Registro r JOIN Metrica m ON r.id_metrica = m.id_metrica GROUP BY m.id_metrica, m.nome ORDER BY media_valor DESC',
			'type': 'bar_metric',
			'tables': ['Registro', 'Metrica']
		},
		'4 - Últimos registros validados (detalhado)': {
			'sql': "SELECT id_registro, data_hora, valor_medido, status, id_unidade, id_empresa, id_metrica FROM Registro WHERE status='VALIDADO' ORDER BY data_hora DESC LIMIT 200",
			'type': 'table_records',
			'tables': ['Registro']
		}
	}

	choice = st.selectbox('Escolha consulta', options=list(queries.keys()))
	q = queries[choice]
	st.code(q['sql'])

	# Resolve required tables and substitute actual table names from sqlite_master
	required = q.get('tables', [])
	missing = []
	resolved_map = {}
	for tname in required:
		res = resolve_table(tname)
		if not res:
			missing.append(tname)
		else:
			resolved_map[tname] = res
	if missing:
		st.info(f"Consultas requerem tabelas ausentes: {', '.join(missing)}. Use DB -> Inicializar DB (create_db.sql) ou crie as tabelas manualmente.")
		return

	# substitute occurrences of the original table names with resolved names (word-boundary safe)
	sql = q['sql']
	for orig, real in resolved_map.items():
		pattern = re.compile(r"\b" + re.escape(orig) + r"\b", flags=re.IGNORECASE)
		sql = pattern.sub(real, sql)

	# Try executing; if fails, show message
	try:
		rows = db.execute(sql, fetch=True)
	except Exception as e:
		st.error(f'Erro executando consulta: {e}')
		st.info('Verifique se as tabelas existem e o esquema é compatível. Use DB -> Inicializar DB se for o caso.')
		return

	df = pd.DataFrame(rows)
	if df.empty:
		st.info('Consulta retornou 0 linhas.')
		return

	# Render results and simple chart per type
	st.subheader('Resultados')
	st.dataframe(df)

	if q['type'] == 'bar_city':
		if 'cidade' in df.columns and 'total_empresas' in df.columns:
			fig = px.bar(df.sort_values('total_empresas'), x='total_empresas', y='cidade', orientation='h', title='Empresas por cidade')
			st.plotly_chart(fig, use_container_width=True)
	elif q['type'] == 'bar_company':
		if 'empresa_nome' in df.columns and 'total_unidades' in df.columns:
			fig = px.bar(df.nlargest(20, 'total_unidades').sort_values('total_unidades'), x='total_unidades', y='empresa_nome', orientation='h', title='Top empresas por número de unidades')
			st.plotly_chart(fig, use_container_width=True)
	elif q['type'] == 'bar_metric':
		if 'metrica_nome' in df.columns and 'media_valor' in df.columns:
			fig = px.bar(df.sort_values('media_valor'), x='media_valor', y='metrica_nome', orientation='h', title='Média de valor por métrica')
			st.plotly_chart(fig, use_container_width=True)
	elif q['type'] == 'table_records':
		if 'valor_medido' in df.columns:
			fig = px.histogram(df, x='valor_medido', nbins=30, title='Histograma de valores medidos (validados)')
			st.plotly_chart(fig, use_container_width=True)



def main():
	st.sidebar.title('Navegação')
	page = st.sidebar.radio('Ir para', ['Dashboard', 'Empresas', 'Unidades', 'Consultas', 'Auditoria', 'Hierarquia', 'DB'])

	if page == 'Dashboard':
		render_dashboard()
	elif page == 'Empresas':
		render_empresas()
	elif page == 'Unidades':
		render_unidades()
	elif page == 'Consultas':
		render_consultas()
	elif page == 'Auditoria':
		render_auditoria()
	elif page == 'Hierarquia':
		render_hierarquia()
	elif page == 'DB':
		st.header('Inicializar / Inspecionar DB')
		if st.button('Inicializar DB (create_sqlite.sql)'):
			# prefer sqlite-compatible sql if present
			sql_path = BASE_DIR / 'create_sqlite.sql'
			if not sql_path.exists():
				sql_path = BASE_DIR / 'create_db.sql'
			db.init_db(str(sql_path))
			st.success(f'init_db executado usando {sql_path.name} (ver backend.log se preciso)')
		st.write('DB path (sqlite fallback):', db.SQLITE_PATH if hasattr(db, 'SQLITE_PATH') else 'n/a')


if __name__ == '__main__':
	main()
