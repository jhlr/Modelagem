PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Empresa_kaggle (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT UNIQUE,
  name TEXT,
  exchange TEXT,
  industry TEXT,
  weburl TEXT,
  cik TEXT
);

CREATE TABLE IF NOT EXISTS Categoria_kaggle (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS Metrica_kaggle (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  categoria_id INTEGER NOT NULL REFERENCES Categoria_kaggle(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  unit TEXT,
  UNIQUE(categoria_id, name)
);

CREATE TABLE IF NOT EXISTS Registro_kaggle (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  empresa_id INTEGER NOT NULL REFERENCES Empresa_kaggle(id) ON DELETE CASCADE,
  metrica_id INTEGER NOT NULL REFERENCES Metrica_kaggle(id) ON DELETE CASCADE,
  value REAL,
  recorded_at TEXT,
  source_row INTEGER
);

CREATE TABLE IF NOT EXISTS ImportAudit_kaggle (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imported_at TEXT DEFAULT (datetime('now')),
  source_file TEXT,
  row_count INTEGER,
  metric_records INTEGER
);
