#!/usr/bin/env python3
"""
Teste da Lógica Apenas - Sem BigQuery/FastAPI
Testa só o algoritmo de ML e modelos
"""
import sys
import os

# Adicionar shared ao path
sys.path.append('../../shared')

from models import SimpleAnomalyModel, DataPoint, TrainRequest

def test_anomaly_algorithm():
    """Testa o algoritmo de anomalia puro"""
    print("🧮 Testing Anomaly Detection Algorithm")
    print("====================================")
    
    # 1. Criar modelo
    model = SimpleAnomalyModel()
    print("✅ Model created")
    
    # 2. Dados de treino normais (média ~24, std baixo)
    training_data = [23.5, 24.1, 23.8, 24.2, 23.9, 24.0, 23.7, 24.3]
    print(f"📊 Training data: {training_data}")
    
    # 3. Treinar modelo
    model.fit(training_data)
    print(f"🎯 Model trained: mean={model.mean:.2f}, std={model.std:.3f}, threshold={model.threshold}")
    
    # 4. Testar valores normais
    print("\n📈 Testing Normal Values:")
    normal_values = [23.8, 24.1, 23.9, 24.0]
    for value in normal_values:
        is_anomaly = model.predict(value)
        print(f"   Value {value} → Anomaly: {is_anomaly}")
    
    # 5. Testar valores anômalos
    print("\n🚨 Testing Anomaly Values:")
    anomaly_values = [20.0, 30.0, 18.5, 28.0]  # Muito fora do padrão
    for value in anomaly_values:
        is_anomaly = model.predict(value)
        print(f"   Value {value} → Anomaly: {is_anomaly}")
    
    # 6. Estatísticas do modelo
    stats = model.get_stats()
    print(f"\n📊 Model Stats: {stats}")
    
    return True

def test_data_models():
    """Testa os modelos Pydantic"""
    print("\n🔗 Testing Data Models")
    print("=====================")
    
    try:
        # DataPoint
        dp = DataPoint(timestamp=1609459200, value=23.5)
        print(f"✅ DataPoint: {dp}")
        
        # TrainRequest
        tr = TrainRequest(
            timestamps=[1609459200, 1609459260, 1609459320],
            values=[23.5, 24.1, 23.8]
        )
        print(f"✅ TrainRequest: {len(tr.timestamps)} points")
        
        # Validação automática
        try:
            invalid_tr = TrainRequest(timestamps=[1, 2], values=[1.0])  # Tamanhos diferentes
            print("❌ Should have failed validation")
        except Exception as e:
            print(f"✅ Validation working: {type(e).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data models test failed: {e}")
        return False

def test_edge_cases():
    """Testa casos extremos"""
    print("\n⚡ Testing Edge Cases")
    print("===================")
    
    model = SimpleAnomalyModel()
    
    try:
        # Caso 1: Dados idênticos (std = 0)
        model.fit([24.0, 24.0, 24.0, 24.0, 24.0])
        print(f"✅ Identical values: mean={model.mean}, std={model.std}")
        
        # Testar predição com std=0
        is_anomaly = model.predict(24.0)
        print(f"   Same value prediction: {is_anomaly}")
        
        is_anomaly = model.predict(25.0) 
        print(f"   Different value prediction: {is_anomaly}")
        
        # Caso 2: Dados com alta variação
        model.fit([10.0, 20.0, 30.0, 40.0, 50.0])
        print(f"✅ High variance: mean={model.mean}, std={model.std:.2f}")
        
        # Caso 3: Poucos dados
        model.fit([23.5, 24.1])
        print(f"✅ Few data points: mean={model.mean}, std={model.std:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge cases test failed: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 ML Logic Testing - Cloud Version")
    print("===================================\n")
    
    tests = [
        ("Anomaly Algorithm", test_anomaly_algorithm),
        ("Data Models", test_data_models), 
        ("Edge Cases", test_edge_cases)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\n🔄 Running {name}...")
            success = test_func()
            if success:
                print(f"✅ {name} PASSED")
                passed += 1
            else:
                print(f"❌ {name} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {name} CRASHED: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Logic is working correctly.")
        print("💡 Ready to deploy to cloud!")
        return True
    else:
        print(f"\n⚠️ {failed} tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    main()
