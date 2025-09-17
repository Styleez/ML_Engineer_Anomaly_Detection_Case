#!/usr/bin/env python3
"""
Script para inicializar o banco de dados localmente
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.database import init_database, engine
from shared.database.models import TrainedModel, PredictionLog, TrainingData
from sqlalchemy import text
import time

def wait_for_database(max_retries=30):
    """Aguarda o banco estar disponível"""
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
        except Exception as e:
            print(f"⏳ Waiting for database... attempt {i+1}/{max_retries}")
            time.sleep(2)
    
    raise Exception("❌ Database not available after maximum retries")

def create_tables():
    """Cria as tabelas no banco"""
    try:
        init_database()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def insert_sample_data():
    """Insere dados de exemplo para teste"""
    from shared.database.database import get_db_session
    from datetime import datetime
    
    try:
        with get_db_session() as db:
            # Dados de treinamento de exemplo
            base_timestamp = int(datetime.utcnow().timestamp()) - 7200  # 2 horas atrás
            training_timestamps = [base_timestamp + i * 60 for i in range(100)]  # 100 pontos, 1 por minuto
            training_values = [42.5 + i * 0.01 + (i % 10) * 0.2 for i in range(100)]  # Valores variados
            
            sample_training_data = TrainingData(
                series_id="sensor_001",
                model_version="1.0",
                timestamps=training_timestamps,
                values=training_values,
                data_points_count=100
            )
            
            db.add(sample_training_data)
            
            # Modelo de exemplo
            sample_model = TrainedModel(
                series_id="sensor_001",
                model_type="anomaly_detection",
                mean=42.5,
                std=2.1,
                threshold=3.0,
                model_version="1.0",
                training_points=100,
                training_data_stats={
                    "count": 100,
                    "mean": 42.5,
                    "std": 2.1,
                    "min": 38.2,
                    "max": 47.8,
                    "start_time": training_timestamps[0],
                    "end_time": training_timestamps[-1]
                }
            )
            
            db.add(sample_model)
            
            # Algumas predições de exemplo
            base_timestamp = int(datetime.utcnow().timestamp()) - 3600  # 1 hora atrás
            
            predictions = [
                PredictionLog(
                    series_id="sensor_001",
                    timestamp=base_timestamp + i * 60,  # A cada minuto
                    value=42.5 + (i % 10) * 0.5,  # Valores variados
                    is_anomaly=(i % 15 == 0),  # Anomalia a cada 15 pontos
                    confidence=0.95 if (i % 15 == 0) else 0.85,
                    deviation=3.2 if (i % 15 == 0) else 1.1,
                    model_version="1.0"
                ) for i in range(50)
            ]
            
            db.add_all(predictions)
            
        print("✅ Sample data inserted successfully!")
        
    except Exception as e:
        print(f"❌ Error inserting sample data: {e}")
        raise

def main():
    """Função principal"""
    print("🚀 Initializing database...")
    
    # Aguarda o database
    wait_for_database()
    
    # Cria as tabelas
    create_tables()
    
    # Insere dados de exemplo
    insert_sample_data()
    
    print("🎉 Database initialization complete!")

if __name__ == "__main__":
    main()
