# Cloud Version - Anomaly Detection System

Versão simplificada do sistema de detecção de anomalias para Google Cloud Platform.

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Training       │    │  Inference      │    │  Monitoring     │
│  Service        │    │  Service        │    │  Service        │
│  (Cloud Run)    │    │  (Cloud Run)    │    │  (Cloud Run)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   BigQuery      │
                    │   Database      │
                    └─────────────────┘
```

## 🚀 Quick Start

### Pré-requisitos

1. **Google Cloud CLI** configurado:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **APIs habilitadas**:
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable bigquery.googleapis.com
   ```

3. **Configurar variáveis**:
   ```bash
   cp env.example .env
   # Edite .env com suas configurações
   ```

### Deploy Rápido

```bash
# 1. Testar localmente
make test-all

# 2. Deploy com Terraform (infraestrutura)
make terraform-deploy

# 3. Deploy dos serviços
make deploy-all
```

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── local/              # Testes sem deploy
│   ├── test_logic_only.py       # Algoritmo ML
│   ├── test_training_local.py   # Training com datasets
│   ├── test_inference_local.py  # Inference com modelos
│   └── test_monitoring_local.py # Dashboard e plots
└── integration/        # Testes com serviços
    ├── test_auth.py             # Autenticação
    └── test_local.py            # Integração local
```

### Comandos de Teste

```bash
# Testes individuais
make test-logic        # Algoritmo ML puro
make test-training     # Training com datasets reais
make test-inference    # Inference com modelos treinados  
make test-monitoring   # Dashboard e visualizações

# Todos os testes
make test-all          # Executa todos os testes locais
```

### Datasets Testados

Os testes usam datasets reais da pasta `../dataset/`:
- `machine_temperature.csv` - Temperatura de máquinas
- `synthetic_cpu_spikes.csv` - Picos de CPU sintéticos  
- `ambient_temperature_system_failure.csv` - Falhas de sistema

## 🔧 Desenvolvimento

### Deploy Individual

```bash
# Testar + deploy específico
make dev-training      # Training service
make dev-inference     # Inference service  
make dev-monitoring    # Monitoring service

# Ou deploy direto
make deploy-training
make deploy-inference
make deploy-monitoring
```

### Workflow Recomendado

1. **Desenvolver**: Edite código dos serviços
2. **Testar**: `make test-all` (sempre local primeiro!)
3. **Deploy**: `make deploy-SERVICO` ou `make deploy-all`
4. **Verificar**: `make status`

## 📊 Monitoramento

### Dashboard

Acesse o dashboard em: `https://anomaly-monitoring-[hash].us-central1.run.app/dashboard`

Funcionalidades:
- 📈 Plots interativos dos dados de treinamento
- 📊 Métricas de latência e throughput
- 🔍 Uso de modelos por série temporal
- ⚡ Visualização em tempo real

### Endpoints

**Training Service:**
- `POST /fit/{series_id}` - Treinar modelo
- `GET /healthcheck` - Health check

**Inference Service:**
- `POST /predict/{series_id}` - Predizer anomalia
- `GET /healthcheck` - Health check

**Monitoring Service:**
- `GET /dashboard` - Dashboard interativo
- `GET /plot?series_id=X&version=Y` - Plot específico
- `GET /metrics/latency` - Métricas de latência
- `GET /metrics/throughput` - Métricas de throughput
- `GET /metrics/model-usage` - Uso de modelos

## 🗄️ Dados

### BigQuery

Tabelas criadas automaticamente:
- `trained_models` - Modelos treinados
- `predictions` - Logs de predições  
- `training_data` - Dados de treinamento

### Algoritmo

**3-Sigma Rule**: Detecta anomalias quando `|valor - média| > 3 * desvio_padrão`

## 🛠️ Comandos Úteis

```bash
# Status dos serviços
make status

# Logs em tempo real
gcloud run services logs tail anomaly-training --region=us-central1

# Limpeza
make clean

# Terraform
make terraform-plan    # Ver mudanças
make terraform-apply   # Aplicar infraestrutura
make terraform-destroy # Destruir recursos
```

## 🔐 Configuração

### Variáveis de Ambiente (.env)

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json  # Opcional
EMAIL=your-email@domain.com
```

### Terraform Variables

```bash
# terraform/terraform.tfvars
project_id = "your-project-id"
region     = "us-central1"
email      = "your-email@domain.com"
```

## 📈 Performance

### Métricas Típicas

- **Training**: ~2-5s para 30 pontos
- **Inference**: ~100-300ms por predição
- **Monitoring**: Dashboard carrega em ~1-2s

### Escalabilidade

- **Cloud Run**: Auto-scaling 0-1000 instâncias
- **BigQuery**: Suporta petabytes de dados
- **Concorrência**: 1000+ requests simultâneas

## 🚨 Troubleshooting

### Problemas Comuns

1. **BigQuery permissions**:
   ```bash
   gcloud auth application-default login
   ```

2. **Cloud Build timeout**:
   ```bash
   gcloud builds submit --timeout=20m
   ```

3. **Testes falhando**:
   ```bash
   # Verificar datasets
   ls ../dataset/
   
   # Verificar paths
   cd tests/local && python test_logic_only.py
   ```

### Logs

```bash
# Serviços
gcloud run services logs tail SERVICE_NAME --region=us-central1

# Cloud Build
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

## 📚 Recursos

- [Google Cloud Run](https://cloud.google.com/run/docs)
- [BigQuery](https://cloud.google.com/bigquery/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

---

**💡 Dica**: Execute sempre `make test-all` antes de fazer deploy!