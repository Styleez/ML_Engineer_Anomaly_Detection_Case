-- Inicialização do banco de dados para testes
-- Este script é executado automaticamente pelo PostgreSQL

-- Criar as tabelas principais
CREATE TABLE IF NOT EXISTS trained_models (
    id SERIAL PRIMARY KEY,
    series_id VARCHAR(255) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_parameters JSONB NOT NULL,
    threshold FLOAT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    CONSTRAINT uq_series_version UNIQUE (series_id, model_version)
);

CREATE TABLE IF NOT EXISTS prediction_logs (
    id SERIAL PRIMARY KEY,
    series_id VARCHAR(255) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    timestamp BIGINT NOT NULL,
    value FLOAT NOT NULL,
    prediction BOOLEAN NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS training_data (
    id SERIAL PRIMARY KEY,
    series_id VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    timestamp BIGINT NOT NULL,
    value FLOAT NOT NULL,
    created_at BIGINT NOT NULL
);

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_trained_models_series_id ON trained_models(series_id);
CREATE INDEX IF NOT EXISTS idx_trained_models_active ON trained_models(is_active);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_series_id ON prediction_logs(series_id);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_created_at ON prediction_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_training_data_series_version ON training_data(series_id, version);
CREATE INDEX IF NOT EXISTS idx_training_data_created_at ON training_data(created_at);

-- Inserir dados de teste básicos (opcional)
-- INSERT INTO trained_models (series_id, model_version, model_parameters, threshold, created_at, updated_at)
-- VALUES ('test_series', 'v1', '{"mean": 42.0, "std": 2.0}', 3.0, extract(epoch from now()), extract(epoch from now()))
-- ON CONFLICT (series_id, model_version) DO NOTHING;
