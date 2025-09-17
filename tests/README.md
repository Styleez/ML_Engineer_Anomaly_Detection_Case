# 🧪 Test Suite

Estrutura de testes organizados e reutilizáveis para todos os serviços.

## 📂 Estrutura

```
tests/
├── conftest.py              # Fixtures globais e configuração
├── pytest.ini              # Configuração do pytest
├── requirements.txt         # Dependências de teste
├── unit/                    # Testes unitários
│   ├── test_training_service.py
│   ├── test_inference_service.py
│   └── test_plot_service.py
├── integration/             # Testes de integração
│   └── test_end_to_end.py
└── utils/                   # Utilitários reutilizáveis
    └── test_helpers.py
```

## 🚀 Execução dos Testes

### Testes unitários (funcionando)
```bash
python scripts/run_unit_tests_only.py
# ou manualmente:
pytest tests/unit/test_ml_algorithm.py tests/unit/test_services_simplified.py -v
```

### Todos os testes (com alguns problemas de setup)
```bash
python scripts/run_tests.py
```

### Apenas testes unitários (todos, incluindo com problemas)
```bash
python scripts/run_tests.py unit
# ou
pytest tests/unit/ -v
```

### Apenas testes de integração
```bash
python scripts/run_tests.py integration  
# ou
pytest tests/integration/ -v
```

### Testes específicos
```bash
# Teste específico
pytest tests/unit/test_training_service.py::TestTrainingService::test_fit_model_success -v

# Por marcadores
pytest -m "not integration" -v  # Apenas não-integração
pytest -m "database" -v         # Apenas testes que usam BD
```

## 🏗️ Fixtures Reutilizáveis

### `conftest.py`
- `test_db`: Sessão de banco de dados de teste
- `mock_redis`: Mock do Redis
- `sample_training_data`: Dados de treinamento de exemplo
- `sample_prediction_data`: Dados de predição de exemplo
- `trained_model_in_db`: Modelo já treinado no banco

### `test_helpers.py`
- `DataGenerator`: Gera dados de teste (normal, com anomalias, constante)
- `ServiceTester`: Helpers para testar serviços
- `TestValidator`: Validação de formatos de resposta

## 🧪 Tipos de Teste

### 1. Testes Unitários
Testam cada serviço isoladamente com mocks:

```python
def test_fit_model_success(self, training_client, sample_training_data):
    response = training_client.post("/fit/test_series", json=sample_training_data)
    assert response.status_code == 200
```

### 2. Testes de Integração
Testam o fluxo completo entre serviços:

```python
def test_complete_workflow(self):
    # 1. Train model
    train_response = requests.post(f"{training_url}/fit/{series_id}", json=data)
    
    # 2. Make prediction  
    predict_response = requests.post(f"{inference_url}/predict/{series_id}", json=pred_data)
    
    # 3. Get plot
    plot_response = requests.get(f"{plot_url}/plot?series_id={series_id}")
```

## 📊 Cenários de Teste

### Training Service
- ✅ Treinamento bem-sucedido
- ✅ Dados inválidos (tamanhos diferentes, poucos pontos)
- ✅ Valores constantes (falha esperada)
- ✅ Criação de registros no banco
- ✅ Health check

### Inference Service  
- ✅ Predição com modelo em cache
- ✅ Cache miss (modelo não encontrado)
- ✅ Dados inválidos
- ✅ Detecção de anomalias
- ✅ Cache de resultados
- ✅ Health check com Redis

### Plot Service
- ✅ Recuperação de dados de treinamento
- ✅ Versão específica vs. mais recente
- ✅ Séries inexistentes
- ✅ Estrutura correta dos dados
- ✅ Health check

### Integração End-to-End
- ✅ Fluxo completo: train → predict → plot
- ✅ Consistência de versões
- ✅ Tratamento de erros
- ✅ Health checks de todos os serviços
- ✅ Predições concorrentes

## 🔧 Configuração

### Pré-requisitos
```bash
# Instalar dependências de teste
pip install -r tests/requirements.txt

# Para testes de integração, serviços devem estar rodando:
make start  # ou docker-compose up
```

### Variáveis de Ambiente
```bash
export ENVIRONMENT=test
export DATABASE_URL=sqlite:///./test.db
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

## 📈 Métricas de Teste

### Coverage
```bash
pytest --cov=services/ --cov-report=html tests/
```

### Performance
```bash
pytest --benchmark-only tests/
```

### Relatórios
```bash
pytest --html=reports/report.html --self-contained-html tests/
```

## 🐛 Debug

### Logs detalhados
```bash
pytest -v -s --log-cli-level=DEBUG tests/
```

### Parar no primeiro erro
```bash
pytest -x tests/
```

### Rodar teste específico em debug
```bash
pytest tests/unit/test_training_service.py::TestTrainingService::test_fit_model_success -v -s --pdb
```

## ✅ Checklist de Testes

Antes de fazer deploy:

- [ ] Todos os testes unitários passam
- [ ] Todos os testes de integração passam  
- [ ] Coverage > 80%
- [ ] Performance dentro dos requisitos (P95 < 100ms)
- [ ] Health checks funcionando
- [ ] Tratamento de erros validado
