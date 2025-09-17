# 🏗️ Arquitetura de Microserviços - Detecção de Anomalias

## 📋 Visão Geral

Sistema de detecção de anomalias baseado em microserviços, onde cada serviço pode ser escalado independentemente conforme a demanda.

## 🎯 Arquitetura Correta

```
┌─────────────┐    ┌─────────────────┐
│    User     │───▶│   Client App    │
└─────────────┘    └─────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  API Gateway    │  ← Routing & Rate Limiting
                   │ (Nginx/GCP)     │
                   └─────────────────┘
                            │
                ┌───────────┼───────────────┐
                │           │               │
                ▼           ▼               ▼
       ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
       │  Training   │ │  Inference  │ │    Plot     │
       │  Service    │ │  Service    │ │  Service    │
       │             │ │   + Redis   │ │             │
       └─────────────┘ └─────────────┘ └─────────────┘
               │               │               │
               │               │               │
               └───────────────┼───────────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │   Database VM   │
                      │  (PostgreSQL)   │
                      └─────────────────┘
```

## 🔧 Componentes

### 1. **API Gateway**
- **Função**: Routing, Rate Limiting, Authentication
- **Tecnologia**: Nginx (local) / GCP API Gateway (produção)
- **Endpoints**: `/fit`, `/predict`, `/plot`, `/health`

### 2. **Training Service** 
- **Função**: Treina modelos de ML e persiste no banco
- **Porta**: 8000
- **Dependências**: Database VM
- **Autoscaling**: Baseado em requests de treinamento

### 3. **Inference Service**
- **Função**: Predições em tempo real
- **Porta**: 8001  
- **Cache**: Redis interno (parâmetros do modelo)
- **Fallback**: Database VM se cache miss
- **Autoscaling**: Baseado em RPS (target: 180 RPS)

### 4. **Plot Service**
- **Função**: API GET para visualização de dados
- **Porta**: 8002
- **Dependências**: Database VM (read-only)
- **Autoscaling**: Baseado em requests de visualização

### 5. **Database VM**
- **Função**: Persistência de modelos e dados de treinamento
- **Tecnologia**: PostgreSQL 15
- **Schema**: Gerenciado via Alembic migrations
- **Backup**: Configurado para produção

### 6. **HealthCheck Service** (Parte do Monitoring)
- **Função**: Monitora saúde de todos os serviços
- **Porta**: 8003
- **Agregação**: Status consolidado do sistema

## 🚀 Escalabilidade

Cada microserviço pode ser escalado independentemente:

- **Training**: Scale-up durante retreinamento de modelos
- **Inference**: Scale-out para alta frequência (180 RPS)  
- **Plot**: Scale conforme demanda de dashboards
- **Database**: Vertical scaling + read replicas

## 🔄 Fluxos de Dados

### Treinamento:
```
Client → API Gateway → Training Service → Database VM
```

### Predição:
```
Client → API Gateway → Inference Service → Redis Cache
                                        ↓ (cache miss)
                                      Database VM
```

### Visualização:
```
Client → API Gateway → Plot Service → Database VM
```

## 🛠️ Deploy Local

```bash
# Iniciar ambiente completo
docker-compose -f docker-compose.test.yml up --build

# Serviços disponíveis:
# Training:    http://localhost:8000
# Inference:   http://localhost:8001  
# Plot:        http://localhost:8002
# HealthCheck: http://localhost:8003
# API Gateway: http://localhost (porta 80)
```

## 📊 Características Técnicas

- **Database**: PostgreSQL com Alembic migrations
- **Cache**: Redis interno no Inference Service  
- **API Gateway**: Rate limiting e routing
- **Healthchecks**: Endpoint `/healthcheck` em cada serviço
- **Monitoring**: HealthCheck Service agrega status
- **Logs**: Estruturados para observabilidade
- **Performance**: P95 < 100ms, 180 RPS target
