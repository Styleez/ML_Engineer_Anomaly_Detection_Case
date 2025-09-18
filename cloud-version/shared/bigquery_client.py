"""
Cliente BigQuery simplificado
"""
from google.cloud import bigquery
import json
import os
from typing import Dict, List, Optional
import time

class BigQueryClient:
    """Cliente simplificado para BigQuery"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        
        # Se ainda não tem project_id, tentar pegar do gcloud
        if not self.project_id:
            try:
                import subprocess
                result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                                      capture_output=True, text=True, check=True)
                self.project_id = result.stdout.strip()
            except Exception:
                pass
        
        if not self.project_id:
            raise ValueError("No project ID found. Set GOOGLE_CLOUD_PROJECT or configure gcloud.")
        
        # Client will automatically use gcloud CLI credentials or service account from environment
        self.client = bigquery.Client(project=self.project_id)
        self.dataset_id = 'anomaly_detection'
        self.models_table = 'trained_models'
        self.predictions_table = 'predictions'
        self.training_data_table = 'training_data'
        
    def ensure_dataset_exists(self):
        """Criar dataset se não existir"""
        dataset_ref = self.client.dataset(self.dataset_id)
        try:
            self.client.get_dataset(dataset_ref)
        except:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            self.client.create_dataset(dataset, exists_ok=True)
            print(f"Created dataset {self.dataset_id}")
    
    def ensure_tables_exist(self):
        """Criar tabelas se não existirem"""
        self.ensure_dataset_exists()
        
        # Tabela de modelos
        models_schema = [
            bigquery.SchemaField("series_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("model_version", "STRING", mode="REQUIRED"), 
            bigquery.SchemaField("mean_value", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("std_value", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("threshold_value", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("points_used", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("is_active", "BOOLEAN", mode="REQUIRED")
        ]
        
        # Tabela de predições
        predictions_schema = [
            bigquery.SchemaField("series_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timestamp", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("value", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("prediction", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("model_version", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("inference_latency_ms", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("database_latency_ms", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("total_latency_ms", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("created_at", "INTEGER", mode="REQUIRED")
        ]
        
        # Tabela de dados de treino
        training_data_schema = [
            bigquery.SchemaField("series_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("model_version", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timestamps", "INTEGER", mode="REPEATED"),
            bigquery.SchemaField("values", "FLOAT", mode="REPEATED"),
            bigquery.SchemaField("data_points_count", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "INTEGER", mode="REQUIRED")
        ]
        
        # Criar tabelas
        self._create_table_if_not_exists(self.models_table, models_schema)
        self._create_table_if_not_exists(self.predictions_table, predictions_schema)
        self._create_table_if_not_exists(self.training_data_table, training_data_schema)
    
    def _create_table_if_not_exists(self, table_name: str, schema: List[bigquery.SchemaField]):
        """Criar tabela se não existir"""
        table_ref = self.client.dataset(self.dataset_id).table(table_name)
        try:
            self.client.get_table(table_ref)
        except:
            table = bigquery.Table(table_ref, schema=schema)
            self.client.create_table(table)
            print(f"Created table {table_name}")
    
    def save_model(self, series_id: str, model_stats: Dict, version: str, points_used: int) -> bool:
        """Salvar modelo treinado"""
        try:
            # Para testes, pular UPDATE para evitar problemas com streaming buffer
            # Em produção, você pode implementar lógica de versioning diferente
            
            # Inserir novo modelo
            table_ref = self.client.dataset(self.dataset_id).table(self.models_table)
            
            rows = [{
                "series_id": series_id,
                "model_version": version,
                "mean_value": model_stats["mean"],
                "std_value": model_stats["std"],
                "threshold_value": model_stats["threshold"],
                "points_used": points_used,
                "created_at": time.time(),
                "is_active": True
            }]
            
            errors = self.client.insert_rows_json(table_ref, rows)
            return len(errors) == 0
            
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def get_active_model(self, series_id: str) -> Optional[Dict]:
        """Buscar modelo ativo"""
        try:
            query = f"""
            SELECT model_version, mean_value, std_value, threshold_value
            FROM `{self.project_id}.{self.dataset_id}.{self.models_table}`
            WHERE series_id = @series_id AND is_active = true
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("series_id", "STRING", series_id)
                ]
            )
            
            results = self.client.query(query, job_config=job_config).result()
            
            for row in results:
                return {
                    "model_version": row.model_version,
                    "mean": row.mean_value,
                    "std": row.std_value,
                    "threshold": row.threshold_value
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting model: {e}")
            return None
    
    def log_prediction(self, series_id: str, timestamp: int, value: float, 
                      prediction: bool, model_version: str, 
                      inference_latency_ms: float = None,
                      database_latency_ms: float = None,
                      total_latency_ms: float = None) -> bool:
        """Log predição"""
        try:
            table_ref = self.client.dataset(self.dataset_id).table(self.predictions_table)
            
            # Garantir tipos corretos - usar apenas campos essenciais
            row = {
                "series_id": str(series_id),
                "timestamp": int(timestamp),
                "value": float(value),
                "prediction": bool(prediction),
                "model_version": str(model_version),
                "created_at": int(time.time())
            }
            
            print(f"Logging prediction: {row}")  # Debug
            
            errors = self.client.insert_rows_json(table_ref, [row])
            
            if errors:
                print(f"BigQuery insert errors: {errors}")
                return False
            
            print(f"✅ Prediction logged successfully")  # Debug
            return True
            
        except Exception as e:
            print(f"Error logging prediction: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_next_version(self, series_id: str) -> str:
        """Gerar próxima versão do modelo"""
        try:
            query = f"""
            SELECT model_version
            FROM `{self.project_id}.{self.dataset_id}.{self.models_table}`
            WHERE series_id = @series_id
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("series_id", "STRING", series_id)
                ]
            )
            
            results = self.client.query(query, job_config=job_config).result()
            
            for row in results:
                current_version = row.model_version
                if current_version.startswith('v'):
                    try:
                        version_num = int(current_version[1:])
                        return f"v{version_num + 1}"
                    except:
                        pass
            
            return "v1"
            
        except Exception as e:
            print(f"Error getting next version: {e}")
            return "v1"
    
    def save_training_data(self, series_id: str, model_version: str, 
                          timestamps: List[int], values: List[float]) -> bool:
        """Salvar dados de treino"""
        try:
            table_ref = self.client.dataset(self.dataset_id).table(self.training_data_table)
            
            rows = [{
                "series_id": series_id,
                "model_version": model_version,
                "timestamps": timestamps,
                "values": values,
                "data_points_count": len(timestamps),
                "created_at": int(time.time())
            }]
            
            errors = self.client.insert_rows_json(table_ref, rows)
            return len(errors) == 0
            
        except Exception as e:
            print(f"Error saving training data: {e}")
            return False
