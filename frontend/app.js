const API_BASE = 'http://localhost:5000';

async function fetchJson(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Chart instance
let mediaChart = null;

async function loadMediaChart() {
  try {
    const data = await fetchJson('/query/media_por_categoria');
    const labels = data.map(d => d.tipo);
    const values = data.map(d => parseFloat(d.media_valor));
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
