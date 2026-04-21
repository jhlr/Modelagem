-- Create schema for ESG model (cleaned)
DROP DATABASE IF EXISTS esg_db;
CREATE DATABASE esg_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE esg_db;

-- EMPRESA
CREATE TABLE Empresa (
    id_empresa INT PRIMARY KEY AUTO_INCREMENT,
    nome_fantasia VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    cidade VARCHAR(100),
    id_empresa_mae INT,
    CONSTRAINT fk_empresa_mae FOREIGN KEY (id_empresa_mae)
        REFERENCES Empresa(id_empresa) ON DELETE SET NULL
) ENGINE=InnoDB;

-- UNIDADE (Dependente)
CREATE TABLE Unidade (
    id_unidade INT,
    id_empresa INT,
    nome_unidade VARCHAR(255),
    localizacao VARCHAR(255),
    PRIMARY KEY (id_unidade, id_empresa),
    CONSTRAINT fk_unidade_empresa FOREIGN KEY (id_empresa)
        REFERENCES Empresa(id_empresa) ON DELETE CASCADE
) ENGINE=InnoDB;

-- CATEGORIA ESG
CREATE TABLE Categoria (
    id_categoria INT PRIMARY KEY AUTO_INCREMENT,
    descricao VARCHAR(255) UNIQUE NOT NULL,
    tipo ENUM('Ambiental', 'Social', 'Governanca') NOT NULL
) ENGINE=InnoDB;

-- METRICA
CREATE TABLE Metrica (
    id_metrica INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255),
    descricao TEXT,
    id_categoria INT,
    CONSTRAINT fk_metrica_cat FOREIGN KEY (id_categoria) 
        REFERENCES Categoria(id_categoria)
) ENGINE=InnoDB;

-- REGISTRO DE COLETA
CREATE TABLE Registro (
    id_registro INT PRIMARY KEY AUTO_INCREMENT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    valor_medido DECIMAL(10,2),
    status ENUM('PENDENTE', 'VALIDADO', 'REJEITADO') DEFAULT 'PENDENTE',
    id_unidade INT,
    id_empresa INT,
    id_metrica INT,
    CONSTRAINT fk_reg_unidade FOREIGN KEY (id_unidade, id_empresa)
        REFERENCES Unidade(id_unidade, id_empresa),
    CONSTRAINT fk_reg_metrica FOREIGN KEY (id_metrica)
        REFERENCES Metrica(id_metrica)
) ENGINE=InnoDB;

-- AUDITOR E AUDITORIA
CREATE TABLE Auditor (
    cpf VARCHAR(14) PRIMARY KEY,
    nome VARCHAR(255),
    registro_profissional VARCHAR(50) UNIQUE
) ENGINE=InnoDB;

CREATE TABLE Auditoria (
    id_auditoria INT PRIMARY KEY AUTO_INCREMENT,
    data_realizacao DATE,
    parecer_final TEXT,
    cpf_auditor VARCHAR(14),
    CONSTRAINT fk_auditoria_auditor FOREIGN KEY (cpf_auditor) 
        REFERENCES Auditor(cpf)
) ENGINE=InnoDB;

-- RELAÇÃO N:M AUDITORIA <-> REGISTRO
CREATE TABLE Auditoria_Registro (
    id_auditoria INT,
    id_registro INT,
    PRIMARY KEY (id_auditoria, id_registro),
    CONSTRAINT fk_rel_auditoria FOREIGN KEY (id_auditoria) REFERENCES Auditoria(id_auditoria),
    CONSTRAINT fk_rel_registro FOREIGN KEY (id_registro) REFERENCES Registro(id_registro)
) ENGINE=InnoDB;
