import pandas as pd, numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
try:
	# when imported as package (src.streamlit)
	from . import db
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


def load_companies():
	rows = db.execute(
		"SELECT id_empresa, nome_fantasia, cnpj, cidade, id_empresa_mae FROM empresa ORDER BY id_empresa",
		fetch=True,
	)
	return pd.DataFrame(rows)


def create_empresa(nome, cnpj, cidade, id_mae):
	db.execute(
		"INSERT INTO empresa (nome_fantasia, cnpj, cidade, id_empresa_mae) VALUES (%s, %s, %s, %s)",
		(nome, cnpj or None, cidade or None, id_mae or None),
	)


def update_empresa(id_empresa, nome, cnpj, cidade, id_mae):
	db.execute(
		"UPDATE empresa SET nome_fantasia=%s, cnpj=%s, cidade=%s, id_empresa_mae=%s WHERE id_empresa=%s",
		(nome, cnpj or None, cidade or None, id_mae or None, id_empresa),
	)


def delete_empresa(id_empresa):
	db.execute("DELETE FROM empresa WHERE id_empresa=%s", (id_empresa,))


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
	rows = db.execute('SELECT * FROM auditoria LIMIT 500', fetch=True)
	st.dataframe(pd.DataFrame(rows))


def render_hierarquia():
	st.header('Hierarquia de Empresas')
	rows = db.execute(
		'SELECT id_empresa, nome_fantasia, id_empresa_mae FROM empresa ORDER BY id_empresa',
		fetch=True,
	)
	st.dataframe(pd.DataFrame(rows))


def main():
	st.sidebar.title('Navegação')
	page = st.sidebar.radio('Ir para', ['Dashboard', 'Empresas', 'Auditoria', 'Hierarquia', 'DB'])

	if page == 'Dashboard':
		render_dashboard()
	elif page == 'Empresas':
		render_empresas()
	elif page == 'Auditoria':
		render_auditoria()
	elif page == 'Hierarquia':
		render_hierarquia()
	elif page == 'DB':
		st.header('Inicializar / Inspecionar DB')
		if st.button('Inicializar DB (create_db.sql)'):
			sql_path = BASE_DIR / 'create_db.sql'
			db.init_db(str(sql_path))
			st.success('init_db executado (ver backend.log se preciso)')
		st.write('DB path (sqlite fallback):', db.SQLITE_PATH if hasattr(db, 'SQLITE_PATH') else 'n/a')


if __name__ == '__main__':
	main()
