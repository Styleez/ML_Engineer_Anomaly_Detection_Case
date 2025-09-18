# Dockerfile para Monitoring Service - Cloud Run (with uv for speed)
FROM python:3.11-slim

# Instalar uv para instalações super rápidas
RUN pip install --no-cache-dir uv

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (para cache do Docker)
COPY monitoring-service/requirements.txt .

# Instalar dependências Python com uv (muito mais rápido)
RUN uv pip install --system --no-cache -r requirements.txt

# Copiar código da aplicação
COPY monitoring-service/main.py .

# Copiar módulos compartilhados
COPY shared /app/shared

# Expor porta
EXPOSE 8080

# Comando para iniciar o serviço
CMD ["python", "main.py"]
