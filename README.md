# 🤖 Anomaly Detection API

A high-performance microservices-based anomaly detection system for time series data using 3-sigma algorithm.

## 🚀 Quick Start

```bash
# 1. Start all services
make start

# 2. Run all tests  
make test-all

# 3. Check status
make status
```

## 🎯 What It Does

- **Real-time anomaly detection** with P95 < 100ms latency
- **Model training** and versioning
- **Interactive dashboard** with visualizations
- **Redis caching** for performance
- **PostgreSQL** for persistence

## 🏗️ Architecture

| Service | Port | Purpose |
|---------|------|---------|
| **Training** | 8000 | Train models (`/fit/{series_id}`) |
| **Inference** | 8001 | Real-time predictions (`/predict/{series_id}`) |
| **Monitoring** | 8002 | Dashboard & plots (`/dashboard`) |

## 📖 Usage Examples

### Train a Model
```bash
curl -X POST "http://localhost:8000/fit/temp_sensor" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamps": [1609459200, 1609459260, 1609459320],
    "values": [23.5, 24.1, 23.8],
    "threshold": 3.0
  }'
```

### Make Predictions
```bash
curl -X POST "http://localhost:8001/predict/temp_sensor" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "1609459500",
    "value": 25.5
  }'
```

### View Dashboard
Open http://localhost:8002/dashboard

## 🧪 Testing

- **Unit Tests**: 38/38 passing
- **Integration Tests**: 23/23 passing
- **Performance**: 180+ RPS, P95 < 100ms

```bash
# Individual test types
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
make perf-light
```

## 🛠️ Development

```bash
# Manual start
docker-compose -f docker-compose.test.yml up -d --build

# Check health
curl http://localhost:8000/healthcheck
curl http://localhost:8001/healthcheck  
curl http://localhost:8002/healthcheck

# Stop services
make stop
```

## 📁 Project Structure

```
services/
├── training_service/     # Model training (:8000)
├── inference_service/    # Real-time predictions (:8001)
└── monitoring_service/   # Dashboard & monitoring (:8002)

shared/
├── database/            # SQLAlchemy models
├── models/              # Pydantic schemas
└── utils/               # Shared utilities

tests/
├── unit/                # Unit tests (38)
├── integration/         # Integration tests (23)
└── performance/         # Load testing

dataset/                 # Sample CSV data
api_docs/               # OpenAPI specification
```

## 📊 Performance

- **Throughput**: 200+ RPS
- **Latency**: P95 ~95ms
- **Architecture**: Scalable microservices
- **Caching**: Redis for model parameters
- **Database**: PostgreSQL with connection pooling

## 🔧 Requirements

- Docker & Docker Compose
- Python 3.11+ (for local testing)

## ⚙️ Environment Configuration

The system uses environment variables for configuration. For production deployment:

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your settings:
   ```bash
   # Required variables
   DATABASE_URL=postgresql://user:password@host:5432/database
   ENVIRONMENT=production
   
   # Optional optimizations
   DB_POOL_SIZE=20
   REDIS_HOST=localhost
   ```

**Key Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `ENVIRONMENT` - `development|test|production`
- `REDIS_HOST/PORT` - Redis configuration for caching
- `DB_POOL_SIZE` - Database connection pool size

**Note:** For Docker deployment (`make start`), environment variables are pre-configured in `docker-compose.test.yml`.