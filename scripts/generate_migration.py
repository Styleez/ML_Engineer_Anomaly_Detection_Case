#!/usr/bin/env python3
"""
Generate Alembic migration automatically from SQLAlchemy models
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

def generate_migration():
    """Generate migration using alembic autogenerate"""
    print("🔄 Generating Alembic migration from SQLAlchemy models...")
    
    # Change to migrations directory
    migrations_dir = project_root / "shared" / "database" / "migrations"
    os.chdir(migrations_dir)
    
    # Set environment variables
    os.environ["PYTHONPATH"] = f"{project_root}:{project_root}/shared"
    
    try:
        # Generate migration
        result = subprocess.run([
            "alembic", "revision", "--autogenerate", 
            "-m", "Auto-generated from SQLAlchemy models"
        ], capture_output=True, text=True, check=True)
        
        print("✅ Migration generated successfully!")
        print(f"Output: {result.stdout}")
        
        # List generated files
        versions_dir = migrations_dir / "versions"
        migration_files = list(versions_dir.glob("*.py"))
        if migration_files:
            latest_migration = max(migration_files, key=lambda f: f.stat().st_mtime)
            print(f"📁 Latest migration: {latest_migration.name}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating migration: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False
    
    return True

if __name__ == "__main__":
    generate_migration()
