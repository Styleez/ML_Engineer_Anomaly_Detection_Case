# 🐋 Docker Environments for Testing

## Overview

O projeto possui dois ambientes Docker para diferentes propósitos de teste:

## 📋 Ambientes Disponíveis

### 1. `docker-compose.test.yml` (RECOMENDADO para testes)
**Localização**: `./docker-compose.test.yml`
**Propósito**: Simula arquitetura de produção (VM por serviço)

#### Características:
- ✅ **Cada serviço em container separado** (simula VMs)
- ✅ **IPs fixos** simulando rede de produção
- ✅ **Inference Service com Redis interno**
- ✅ **API Gateway (Nginx)** simulando GCP API Gateway
- ✅ **Migrações automáticas** do banco de dados
- ✅ **Healthchecks completos**

#### Portas:
```
localhost:80   → API Gateway (Nginx)
localhost:8000 → Training Service
localhost:8001 → Inference Service  
localhost:8002 → Plot Service
localhost:8003 → HealthCheck Service
localhost:5432 → PostgreSQL
```

#### Como usar:
```bash
# Iniciar ambiente completo
docker-compose -f docker-compose.test.yml up -d

# Executar testes
cd tests && python -m pytest integration/

# Parar ambiente
docker-compose -f docker-compose.test.yml down
```

### 2. `docker-compose.local.yml` (LEGACY - desenvolvimento simples)
**Localização**: `./docker-compose.local.yml`
**Propósito**: Desenvolvimento local básico

#### Características:
- ⚠️ **Portas diferentes** (8001-8004)
- ⚠️ **URLs de healthcheck incorretas**
- ⚠️ **Redis separado** (não interno ao Inference)
- ❌ **Não representa arquitetura de produção**

#### Status: **DEPRECATED** - usar apenas para desenvolvimento local básico

## 🧪 Executando Testes

### Testes Unitários (sempre funcionam):
```bash
cd tests
python -m pytest unit/ -v
```

### Testes de Integração:
```bash
# 1. Iniciar ambiente de teste
docker-compose -f docker-compose.test.yml up -d

# 2. Aguardar serviços ficarem prontos
sleep 30

# 3. Executar testes
cd tests
python -m pytest integration/ -v

# 4. Limpeza
docker-compose -f docker-compose.test.yml down
```

### Testes de Performance:
```bash
cd tests
python -m pytest performance/ -v
```

## 🎯 Recomendação

**Para desenvolvimento e testes**: Use `docker-compose.test.yml`
- Simula ambiente de produção
- Portas corretas (8000-8003)
- Arquitetura correta (Redis interno, API Gateway)
- Testes de integração funcionam corretamente

**Para desenvolvimento rápido**: Use `docker-compose.local.yml` 
- Apenas se precisar de algo muito simples
- Lembre-se de ajustar portas nos testes manuais
