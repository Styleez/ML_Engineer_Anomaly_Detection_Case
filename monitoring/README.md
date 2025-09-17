# 📊 Monitoramento e Análise de Performance

## 🎯 Métricas Coletadas

### Latência
- **Inferência Isolada**: Tempo gasto apenas na predição
  - Métrica: `inference_latency_seconds`
  - Labels: `series_id`, `model_version`
  - Target: P95 < 100ms

- **Logging Isolado**: Tempo gasto na persistência
  - Métrica: `logging_latency_seconds`
  - Labels: `series_id`, `model_version`
  - Análise: Identificar impacto do logging

- **Total**: Tempo total da requisição
  - Métrica: `prediction_latency_seconds`
  - Labels: `series_id`, `model_version`
  - Target: P95 < 100ms

### Cache
- **Hit/Miss Rate**: Eficiência do cache
  - Métrica: `cache_operations_total`
  - Labels: `operation` (`hit`/`miss`), `series_id`
  - Target: Hit Rate > 80%

### Model Usage
- **Predições**: Volume de uso por modelo
  - Métrica: `model_predictions_total`
  - Labels: `series_id`, `model_version`, `is_anomaly`
  - Target: 180 RPS sustentado

### System Health
- **Active Models**: Modelos ativos no sistema
  - Métrica: `active_models`
  - Labels: `series_id`

## 🔍 Dashboards

### 1. Performance Overview
- Latência (P95, média) por modelo
- Throughput (RPS) por modelo
- Cache hit/miss rate
- Anomaly detection rate

### 2. System Health
- CPU/Memory por serviço
- Network I/O
- Disk usage
- Error rates

## 🚀 Como Usar

### Iniciar Monitoramento
```bash
# Na VM-6 (Monitoring)
cd monitoring
docker-compose up -d
```

### Acessar Dashboards
- **Grafana**: http://VM-6-IP:3000
  - User: admin
  - Pass: admin

### Executar Testes de Carga
```bash
# Instalar dependências
cd tests/performance
pip install -r requirements.txt

# Executar testes
python load_test.py
```

## 📈 Análise de Performance

### Métricas Principais
1. **Latência**
   - P95 < 100ms (requisito)
   - Breakdown: Inferência vs. Logging
   - Alertas se P95 > 90ms

2. **Throughput**
   - Target: 180 RPS
   - Monitorar por `series_id`
   - Alertas se < 160 RPS

3. **Cache Efficiency**
   - Hit Rate > 80%
   - TTL: 1h para modelos
   - TTL: 5min para predições

### Alertas Configurados
- P95 latência > 100ms
- Error rate > 1%
- Cache hit rate < 80%
- RPS < 160

## 🔧 Troubleshooting

### Alta Latência
1. Verificar breakdown (inferência vs. logging)
2. Checar cache hit rate
3. Monitorar conexões de banco
4. Verificar CPU/Memory

### Baixo Throughput
1. Verificar connection pool
2. Checar CPU/Memory
3. Monitorar network I/O
4. Validar cache size

### Cache Issues
1. Verificar Redis memory
2. Ajustar TTL se necessário
3. Monitorar eviction rate
4. Verificar key distribution

## 📝 Logs

### Estrutura
```json
{
  "event": "prediction_metrics",
  "series_id": "sensor_123",
  "model_version": "v1",
  "latency_inference_ms": 45.2,
  "latency_logging_ms": 12.3,
  "latency_total_ms": 58.7,
  "cache_hit": true,
  "anomaly": false
}
```

### Retenção
- Prometheus: 15 dias
- Logs: 30 dias
- Métricas agregadas: 90 dias

## 🔄 Próximos Passos

1. **Otimização**
   - Se logging > 30% do tempo total:
     → Implementar async queue
   - Se cache miss > 20%:
     → Aumentar TTL ou cache size

2. **Escalabilidade**
   - Se RPS > 160:
     → Adicionar réplicas
   - Se latência > 90ms P95:
     → Otimizar queries/cache

3. **Monitoramento**
   - Adicionar tracing distribuído
   - Expandir métricas de negócio
   - Criar dashboards por cliente
