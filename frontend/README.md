# Frontend (Dashboard)

Abra `index.html` diretamente no navegador ou sirva a pasta com um servidor estático:

```bash
cd frontend
python3 -m http.server 8000
# abrir http://localhost:8000
```

O dashboard consome os endpoints em `http://localhost:5000` fornecidos pelo backend.

Se o backend estiver em outra origem, ajuste `API_BASE` em `app.js`.
