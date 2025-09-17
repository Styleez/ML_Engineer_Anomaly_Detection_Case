# 🚀 Setup Local - Anomaly Detection System

## Pré-requisitos

- Docker & Docker Compose
- Python 3.11+ (para scripts)
- Make (opcional, para comandos simplificados)

## 🏃‍♂️ Quick Start

```bash
# 1. Setup completo (uma única vez)
make quick-start

# 2. Aguardar serviços subirem (~30s)

# 3. Inicializar banco de dados
make db-init

# 4. Testar sistema
make test
```

## 📋 Comandos Disponíveis

```bash
make help          # Ver todos os comandos
make setup          # Construir imagens Docker
make start          # Iniciar serviços
make stop           # Parar serviços
make restart        # Reiniciar serviços
make logs           # Ver logs de todos os serviços
make status         # Status dos containers
make test           # Executar testes
make clean          # Limpar tudo
make urls           # Ver URLs dos serviços
```

## 🌐 URLs dos Serviços

Após `make start`:

- **Training Service**: http://localhost:8001/docs
- **Inference Service**: http://localhost:8002/docs
- **Plot Service**: http://localhost:8003/docs
- **HealthCheck Service**: http://localhost:8004/docs

## 🗄️ Banco de Dados

- **PostgreSQL**: `localhost:5432`
- **Usuário**: `postgres`
- **Senha**: `password`
- **Database**: `anomaly_detection`

### Conectar ao Banco

```bash
make debug-db
# ou
psql postgresql://postgres:password@localhost:5432/anomaly_detection
```

## 🔧 Cache Redis

- **URL**: `localhost:6379`
- **Database**: 0

## 🧪 Testando o Sistema

### 1. Teste Automático
```bash
make test
```

### 2. Teste Manual

#### Treinar Modelo (conforme especificação)
```bash
curl -X POST "http://localhost:8001/fit/sensor_001" \
     -H "Content-Type: application/json" \
     -d '{
       "timestamps": [1700000000, 1700000060, 1700000120],
       "values": [42.1, 42.3, 41.9]
     }'
```

#### Fazer Predição (conforme especificação)
```bash
curl -X POST "http://localhost:8002/predict/sensor_001" \
     -H "Content-Type: application/json" \
     -d '{
       "timestamp": "1700000180",
       "value": 50.5
     }'
```

#### Ver Série de Treinamento (Plot)
```bash
# Versão mais recente
curl "http://localhost:8003/plot?series_id=sensor_001"

# Versão específica
curl "http://localhost:8003/plot?series_id=sensor_001&version=1.0"
```

#### Health Check Sistema (conforme especificação)
```bash
curl "http://localhost:8001/healthcheck"
```

## 📊 Monitoramento

### Ver Logs em Tempo Real
```bash
make logs                # Todos os serviços
make logs-training       # Apenas training
make logs-inference      # Apenas inference
make logs-plot          # Apenas plot
make logs-health        # Apenas healthcheck
```

### Status dos Serviços
```bash
make status
```

## 🐛 Debug

### Conectar nos Containers
```bash
make debug-training     # Training service
make debug-inference    # Inference service
make debug-plot        # Plot service
make debug-db          # PostgreSQL
```

### Verificar Health Checks
```bash
# Todos de uma vez
curl http://localhost:8004/v1/healthcheck

# Individuais
curl http://localhost:8001/v1/training/healthcheck
curl http://localhost:8002/v1/inference/healthcheck
curl http://localhost:8003/v1/plot/healthcheck
curl http://localhost:8004/health
```

## 🔄 Fluxo Completo de Teste

1. **Iniciar Sistema**
   ```bash
   make quick-start
   ```

2. **Aguardar Serviços** (~30 segundos)

3. **Inicializar Dados**
   ```bash
   make db-init
   ```

4. **Executar Testes**
   ```bash
   make test
   ```

5. **Verificar Logs** (se houver problemas)
   ```bash
   make logs
   ```

## 🆘 Troubleshooting

### Serviço não inicia
```bash
make logs-[service]  # Ver logs específicos
make status          # Ver status dos containers
```

### Database connection error
```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Reinicializar banco
make stop
make start
make db-init
```

### Cache issues
```bash
# Limpar Redis
docker exec -it anomaly_redis redis-cli FLUSHALL

# Ou reiniciar tudo
make restart
```

### Limpar e recomeçar
```bash
make clean           # Remove tudo
make quick-start     # Reconstrói e inicia
make db-init        # Reinicializa dados
```

## 📈 Performance

O sistema local deve atender:
- **Training**: ~2-5 segundos para modelos pequenos
- **Inference**: < 100ms P95
- **Plot**: < 500ms para 100 pontos

Para testar performance:
```bash
# Múltiplas predições
for i in {1..10}; do 
  time curl -X POST "http://localhost:8002/v1/predict/sensor_001" \
       -H "Content-Type: application/json" \
       -d '{"timestamp": "'$(date +%s)'", "value": 42.5}'
done
```
