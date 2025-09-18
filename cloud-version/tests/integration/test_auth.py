#!/usr/bin/env python3
"""
Teste de autenticação Google Cloud sem arquivos JSON
"""
import os
import sys

def test_gcloud_auth():
    """Testar autenticação via gcloud CLI"""
    print("🔐 Testing Google Cloud Authentication")
    print("=" * 50)
    
    # 1. Verificar se GOOGLE_CLOUD_PROJECT está definido
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
        print("Set it with: export GOOGLE_CLOUD_PROJECT='your-project-id'")
        return False
    
    print(f"✅ Project ID: {project_id}")
    
    # 2. Testar BigQuery client
    try:
        sys.path.append('shared')
        from bigquery_client import BigQueryClient
        
        print("🧪 Testing BigQuery connection...")
        
        # Criar client (deve usar gcloud credentials automaticamente)
        bq_client = BigQueryClient(project_id)
        
        # Testar conexão básica
        datasets = list(bq_client.client.list_datasets())
        print(f"✅ BigQuery connection successful")
        print(f"📊 Found {len(datasets)} datasets in project")
        
        # Testar criação de dataset/tabelas
        print("🏗️ Testing dataset/table creation...")
        bq_client.ensure_tables_exist()
        print("✅ Dataset and tables created/verified")
        
        return True
        
    except Exception as e:
        print(f"❌ BigQuery error: {e}")
        print("")
        print("💡 This usually means:")
        print("1. Not authenticated: gcloud auth application-default login")
        print("2. No BigQuery access: Check IAM permissions")
        print("3. Wrong project: gcloud config set project YOUR_PROJECT")
        return False

def test_application_default_credentials():
    """Testar Application Default Credentials"""
    print("\n🔑 Testing Application Default Credentials")
    print("=" * 50)
    
    try:
        from google.auth import default
        
        # Tentar obter credenciais padrão
        credentials, project = default()
        
        print(f"✅ Default credentials found")
        print(f"📋 Project from credentials: {project}")
        print(f"🔐 Credential type: {type(credentials).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ No default credentials: {e}")
        print("")
        print("💡 Run this command:")
        print("   gcloud auth application-default login")
        return False

if __name__ == "__main__":
    print("🧪 Google Cloud Authentication Test")
    print("No service account JSON files required!")
    print("")
    
    success = True
    
    # Teste 1: Application Default Credentials
    if not test_application_default_credentials():
        success = False
    
    # Teste 2: BigQuery client
    if not test_gcloud_auth():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All authentication tests passed!")
        print("🚀 Ready for deployment!")
    else:
        print("❌ Authentication setup needed")
        print("🔧 Run: ./setup-auth.sh")
    
    sys.exit(0 if success else 1)
