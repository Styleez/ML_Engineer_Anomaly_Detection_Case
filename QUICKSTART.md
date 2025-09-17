# 🚀 Guia de Início Rápido - Anomaly Detection API

Este guia permite que qualquer pessoa configure e teste o sistema completo em poucos minutos.

## 📋 Pré-requisitos

- **Docker Desktop** instalado e rodando
- **Git** para clonar o repositório
- **PowerShell** (Windows) ou **Terminal** (Linux/Mac)

## 🚀 Implantação em 3 Passos

### 1. Clone o Repositório
```bash
git clone <repository-url>
cd ML_Engineer_Anomaly_Detection_Case
```

### 2. Inicie o Sistema Completo
```bash
# Windows (PowerShell)
docker-compose -f docker-compose.test.yml up -d

# Linux/Mac
docker-compose -f docker-compose.test.yml up -d
```

### 3. Aguarde Inicialização (2-3 minutos)
O sistema criará e iniciará automaticamente:
- 🗄️ **PostgreSQL** (Banco de dados)
- 🏃‍♂️ **Migrações** (Criação de tabelas)
- 🎯 **Training Service** (porta 8000)
- ⚡ **Inference Service** (porta 8001) + Redis interno
- 📊 **Plot Service** (porta 8002)
- 🏥 **HealthCheck Service** (porta 8003)
- 🌐 **API Gateway** (porta 80)

## ✅ Verificação Rápida

### Verificar Status dos Serviços
```bash
docker ps
```
**Resultado esperado**: Todos containers com status `Up X minutes (healthy)`

### Testar Endpoints
```bash
# Windows (PowerShell)
(Invoke-WebRequest -Uri "http://localhost:8000/healthcheck").StatusCode  # Training: 200
(Invoke-WebRequest -Uri "http://localhost:8001/healthcheck").StatusCode  # Inference: 200
(Invoke-WebRequest -Uri "http://localhost:8002/healthcheck").StatusCode  # Plot: 200
(Invoke-WebRequest -Uri "http://localhost:8003/healthcheck").StatusCode  # HealthCheck: 200

# Linux/Mac
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthcheck  # 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/healthcheck  # 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/healthcheck  # 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/healthcheck  # 200
```

## 🧪 Teste de Integração Completo

Execute o teste automatizado que verifica todo o workflow:

```bash
python tests/integration/test_plot_service_workflow.py
```

**Resultado esperado**:
```
================================================ 10 passed in ~1s =================================================
🎉 Plot Service integration test PASSED!
```

Este teste valida:
- ✅ Treinamento de múltiplas versões (v1, v2, v3)
- ✅ Persistência de dados de treinamento
- ✅ Consulta por versão específica e mais recente
- ✅ Integridade dos dados
- ✅ Tratamento de erros

## 📚 Exemplo Prático de Uso

### 1. Treinar um Modelo
```bash
# Windows (PowerShell)
$body = '{"timestamps": [1386029700, 1386030000, 1386030300], "values": [75.5, 76.2, 77.1], "threshold": 3.0}'
Invoke-WebRequest -Uri "http://localhost:8000/fit/sensor_001" -Method Post -Body $body -ContentType "application/json"

# Linux/Mac
curl -X POST "http://localhost:8000/fit/sensor_001" \
  -H "Content-Type: application/json" \
  -d '{"timestamps": [1386029700, 1386030000, 1386030300], "values": [75.5, 76.2, 77.1], "threshold": 3.0}'
```

**Resposta esperada**:
```json
{
  "timestamp": 1758128924,
  "version": "v1", 
  "model_version": "v1",
  "series_id": "sensor_001",
  "points_used": 3
}
```

### 2. Fazer Predição
```bash
# Windows (PowerShell)
$body = '{"timestamp": "1386030600", "value": 85.5}'
Invoke-WebRequest -Uri "http://localhost:8001/predict/sensor_001" -Method Post -Body $body -ContentType "application/json"

# Linux/Mac
curl -X POST "http://localhost:8001/predict/sensor_001" \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "1386030600", "value": 85.5}'
```

### 3. Consultar Dados de Treinamento
```bash
# Versão mais recente
curl "http://localhost:8002/plot?series_id=sensor_001"

# Versão específica
curl "http://localhost:8002/plot?series_id=sensor_001&version=v1"
```

## 🔧 Troubleshooting

### Container Unhealthy
```bash
# Verificar logs
docker logs plot_service
docker logs training_service
docker logs inference_service
```

### Reinicar Serviços
```bash
# Parar tudo
docker-compose -f docker-compose.test.yml down

# Remover volumes (reset completo)
docker volume rm ml_engineer_anomaly_detection_case_postgres_data

# Iniciar novamente
docker-compose -f docker-compose.test.yml up -d
```

### Portas em Uso
Se alguma porta estiver ocupada, edite `docker-compose.test.yml` e altere o mapeamento:
```yaml
ports:
  - "8010:8000"  # Muda de 8000 para 8010
```

## 🎯 Arquitetura do Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Training      │    │   Inference     │    │     Plot        │
│   Service       │    │   Service       │    │   Service       │
│   (Port 8000)   │    │   (Port 8001)   │    │   (Port 8002)   │
│                 │    │   + Redis       │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴───────────┐
                    │      PostgreSQL        │
                    │     (Port 5432)        │
                    │   - trained_models     │
                    │   - training_data      │
                    │   - prediction_logs    │
                    └─────────────────────────┘
```

## 📊 Métricas de Performance

O sistema atende aos requisitos:
- **Throughput**: 180+ RPS
- **Latência P95**: < 100ms
- **Versionamento**: v1, v2, v3, ...
- **Persistência**: Dados e modelos salvos
- **Cache**: Redis para inferências rápidas

## 🚀 Próximos Passos

1. **Explorar APIs**: Use o sistema com seus próprios dados
2. **Monitoramento**: Acesse `/healthcheck` em cada serviço
3. **Escalabilidade**: Cada serviço pode ser escalado independentemente
4. **Produção**: Configure API Gateway e load balancer externos

---

**🎉 Sistema pronto para produção!** Qualquer dúvida, consulte os logs ou execute os testes de integração.
