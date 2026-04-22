-- SQLite schema for ESG app (compatible with sqlite3)
PRAGMA foreign_keys = ON;

-- Empresa
CREATE TABLE IF NOT EXISTS Empresa (
    id_empresa INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_fantasia TEXT NOT NULL,
    cnpj TEXT UNIQUE,
    cidade TEXT,
    id_empresa_mae INTEGER
);

-- Unidade (composite PK)
CREATE TABLE IF NOT EXISTS Unidade (
    id_unidade INTEGER NOT NULL,
    id_empresa INTEGER NOT NULL,
    nome_unidade TEXT,
    localizacao TEXT,
    PRIMARY KEY (id_unidade, id_empresa),
    FOREIGN KEY (id_empresa) REFERENCES Empresa(id_empresa) ON DELETE CASCADE
);

-- Categoria
CREATE TABLE IF NOT EXISTS Categoria (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT UNIQUE NOT NULL,
    tipo TEXT
);

-- Metrica
CREATE TABLE IF NOT EXISTS Metrica (
    id_metrica INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT,
    id_categoria INTEGER,
    FOREIGN KEY (id_categoria) REFERENCES Categoria(id_categoria)
);

-- Registro
CREATE TABLE IF NOT EXISTS Registro (
    id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora TEXT DEFAULT (datetime('now')),
    valor_medido REAL,
    status TEXT DEFAULT 'PENDENTE',
    id_unidade INTEGER,
    id_empresa INTEGER,
    id_metrica INTEGER,
    FOREIGN KEY (id_empresa) REFERENCES Empresa(id_empresa),
    FOREIGN KEY (id_metrica) REFERENCES Metrica(id_metrica)
);

-- Auditor
CREATE TABLE IF NOT EXISTS Auditor (
    cpf TEXT PRIMARY KEY,
    nome TEXT,
    registro_profissional TEXT UNIQUE
);

-- Auditoria
CREATE TABLE IF NOT EXISTS Auditoria (
    id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT,
    data_realizacao TEXT,
    parecer_final TEXT,
    cpf_auditor TEXT,
    FOREIGN KEY (cpf_auditor) REFERENCES Auditor(cpf)
);

-- Auditoria_Registro (many-to-many)
CREATE TABLE IF NOT EXISTS Auditoria_Registro (
    id_auditoria INTEGER,
    id_registro INTEGER,
    PRIMARY KEY (id_auditoria, id_registro),
    FOREIGN KEY (id_auditoria) REFERENCES Auditoria(id_auditoria),
    FOREIGN KEY (id_registro) REFERENCES Registro(id_registro)
);
