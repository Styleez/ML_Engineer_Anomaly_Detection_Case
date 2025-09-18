# 🏗️ Terraform Infrastructure - Anomaly Detection System

Infrastructure as Code para o sistema de detecção de anomalias no Google Cloud Platform.

## 🚀 Quick Start

```bash
# 1. Configurar .env na pasta principal
cd ..
cp env.example .env
# Editar .env com seus dados

# 2. Deploy automatizado
./terraform-deploy.sh

# 3. Build e deploy dos serviços
gcloud builds submit --config=cloudbuild.yaml
```

## 📋 O que o Terraform Cria

### 🗄️ BigQuery
- **Dataset**: `anomaly_detection`
- **Tabelas**:
  - `trained_models` - Modelos treinados
  - `predictions` - Predições com métricas de latência
  - `training_data` - Dados de treino (arrays)

### ☁️ Cloud Run Services
- **Training Service** (`anomaly-training`)
- **Inference Service** (`anomaly-inference`) 
- **Monitoring Service** (`anomaly-monitoring`)

### 🔐 IAM & Security
- Service accounts automáticos
- Permissões BigQuery
- IAM bindings para Cloud Run

### 💰 Cost Management
- Budget alerts (opcional)
- Monitoring notifications
- Resource limits configuráveis

## 🔧 Manual Deployment

```bash
cd terraform

# 1. Criar terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
# Editar com seus valores

# 2. Initialize
terraform init

# 3. Plan
terraform plan

# 4. Apply
terraform apply
```

## 📊 Variáveis Importantes

### Obrigatórias
```hcl
project_id = "your-gcp-project"
user_email = "your-email@domain.com"
```

### Cloud Run Configuration
```hcl
cloud_run_cpu           = "1"
cloud_run_memory        = "512Mi"
cloud_run_max_instances = 10
cloud_run_concurrency   = 80
```

### Budget Alerts
```hcl
budget_alert_threshold = 50.00
budget_alert_email     = "billing@domain.com"
billing_account_id     = "YOUR-BILLING-ID"
```

## 📈 Outputs

Após deployment, o Terraform fornece:

```bash
# URLs dos serviços
terraform output training_service_url
terraform output inference_service_url
terraform output monitoring_service_url
terraform output dashboard_url

# Exemplos de uso
terraform output curl_examples

# Informações BigQuery
terraform output bigquery_tables
```

## 🏷️ Tags e Particionamento

### BigQuery Tables
- **Partitioning**: Por dia (`created_at`)
- **Clustering**: Por `series_id` (predictions)
- **TTL**: Configurável via `metrics_retention_days`

### Cloud Run
- **Execution Environment**: gen2
- **Auto-scaling**: 0 to `max_instances`
- **CPU**: Only allocated during requests

## 💰 Cost Optimization

### Estimativas (1000 requests/dia):
- **Cloud Run**: $3-5/mês
- **BigQuery**: $0.10-0.50/mês
- **Total**: ~$5-10/mês

### Para Otimizar:
```hcl
# Configuração econômica
cloud_run_cpu           = "0.5"
cloud_run_memory        = "256Mi"
cloud_run_max_instances = 5
metrics_retention_days  = 7
```

## 🔍 Monitoring

O Terraform configura:
- Métricas nativas do Cloud Run
- Budget alerts (opcional)
- Email notifications
- Custom dashboard via monitoring service

## 🧹 Cleanup

```bash
# Destruir infraestrutura
terraform destroy

# Limpar imagens Docker
gcloud container images list --repository=gcr.io/$PROJECT_ID
gcloud container images delete gcr.io/$PROJECT_ID/IMAGE_NAME
```

## 🔐 Security Best Practices

### Para Produção:
```hcl
enable_authentication = true
```

Depois configurar IAM:
```bash
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --member="user:your-email@domain.com" \
  --role="roles/run.invoker"
```

## 🚨 Troubleshooting

### APIs não habilitadas
```bash
gcloud services enable run.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Billing não configurado
```bash
gcloud beta billing accounts list
gcloud beta billing projects link PROJECT_ID --billing-account=BILLING_ID
```

### Permissões insuficientes
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:your-email@domain.com" \
  --role="roles/owner"
```

## 📝 Next Steps

1. **Deploy Services**: `gcloud builds submit --config=../cloudbuild.yaml`
2. **Test System**: Use curl examples from outputs
3. **Monitor Costs**: Google Cloud Console → Billing
4. **Scale Up**: Adjust `cloud_run_max_instances` as needed

## 🏆 Production Checklist

- [ ] Budget alerts configurados
- [ ] Monitoring notifications ativas
- [ ] Backup strategy para BigQuery
- [ ] Authentication habilitada
- [ ] SSL certificates configurados
- [ ] Disaster recovery plan

---

**🎯 Infrastructure as Code = Zero Ops!** ⚡
