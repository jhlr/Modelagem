const API_BASE = 'http://127.0.0.1:5001';

async function fetchJson(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Chart instance
let mediaChart = null;
let mediaPieChart = null;

async function loadMediaChart() {
  try {
    const data = await fetchJson('/query/media_por_categoria');
    const labels = data.map(d => d.tipo);
    const values = data.map(d => {
      const v = d.media_valor;
      const n = v === null || v === undefined ? 0 : Number(v);
      return Number.isNaN(n) ? 0 : n;
    });
    const ctx = document.getElementById('mediaChart').getContext('2d');
    if (mediaChart) mediaChart.destroy();
    mediaChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: 'Média', data: values, backgroundColor: 'rgba(54,162,235,0.6)' }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });

    // pie chart: if all zeros, try counts fallback
    const sum = values.reduce((s,v)=>s+v,0);
    const pieEl = document.getElementById('mediaPieChart');
    if (!pieEl) return;
    const pieCtx = pieEl.getContext('2d');
    if (sum === 0) {
      try {
        const counts = await fetchJson('/query/counts_por_categoria');
        const cLabels = counts.map(c=>c.tipo);
        const cValues = counts.map(c=>Number(c.registros)||0);
        const colors = cLabels.map((_,i)=>`hsl(${(i*60)%360},70%,50%)`);
        if (mediaPieChart) mediaPieChart.destroy();
        mediaPieChart = new Chart(pieCtx, { type: 'pie', data: { labels: cLabels, datasets: [{ data: cValues, backgroundColor: colors }] }, options: { responsive: true, maintainAspectRatio: false } });
      } catch (e) {
        // if counts endpoint not available, show empty pie with labels
        const colors = labels.map((_,i)=>`hsl(${(i*60)%360},70%,50%)`);
        if (mediaPieChart) mediaPieChart.destroy();
        mediaPieChart = new Chart(pieCtx, { type: 'pie', data: { labels, datasets: [{ data: values, backgroundColor: colors }] }, options: { responsive: true, maintainAspectRatio: false } });
      }
    } else {
      const colors = labels.map((_,i)=>`hsl(${(i*60)%360},70%,50%)`);
      if (mediaPieChart) mediaPieChart.destroy();
      mediaPieChart = new Chart(pieCtx, { type: 'pie', data: { labels, datasets: [{ data: values, backgroundColor: colors }] }, options: { responsive: true, maintainAspectRatio: false } });
    }
  } catch (err) {
    console.error(err);
    alert('Erro ao carregar dados: ' + err.message);
  }
}

async function loadAuditoria() {
  try {
    const rows = await fetchJson('/query/auditoria');
    const tbody = document.querySelector('#auditoriaTable tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.empresa}</td><td>${r.data_hora}</td><td>${r.valor_medido}</td><td>${r.nome_auditor}</td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
    alert('Erro ao carregar auditoria: ' + err.message);
  }
}

async function loadHierarquia() {
  try {
    const rows = await fetchJson('/query/hierarquia_empresas');
    const tbody = document.querySelector('#hierarquiaTable tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.subsidiaria || ''}</td><td>${r.controladora || ''}</td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
    alert('Erro ao carregar hierarquia: ' + err.message);
  }
}

document.getElementById('refreshChart').addEventListener('click', loadMediaChart);
document.getElementById('loadAuditoria').addEventListener('click', loadAuditoria);
document.getElementById('loadHierarquia').addEventListener('click', loadHierarquia);

// initial load
loadMediaChart();
