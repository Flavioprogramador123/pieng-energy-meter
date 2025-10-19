#!/usr/bin/env python3
"""
Teste TUYA REAL - APENAS dados reais!
"""

import os
import json
from dotenv import load_dotenv

print("=" * 70)
print("   TESTE TUYA REAL - Sem dados fake!")
print("=" * 70)
print()

# Carregar credenciais
load_dotenv()

access_id = os.getenv("TUYA_ACCESS_ID")
access_secret = os.getenv("TUYA_ACCESS_SECRET")
region = os.getenv("TUYA_API_REGION", "us")

if not access_id or not access_secret:
    print("❌ ERRO: Credenciais Tuya não encontradas no .env")
    print()
    print("Configure no arquivo .env:")
    print("  TUYA_ACCESS_ID=sua_access_id")
    print("  TUYA_ACCESS_SECRET=seu_secret")
    print("  TUYA_API_REGION=us")
    exit(1)

print(f"✅ Credenciais encontradas")
print(f"   Região: {region}")
print(f"   Access ID: {access_id[:10]}...")
print()

# Conectar Tuya
try:
    import tinytuya
    
    print("📡 Conectando Tuya Cloud API...")
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=access_id,
        apiSecret=access_secret
    )
    
    # Listar dispositivos
    devices = cloud.getdevices()
    
    if not devices:
        print()
        print("⚠️  Nenhum dispositivo encontrado na conta Tuya!")
        print()
        print("Possíveis causas:")
        print("  1. Credenciais incorretas")
        print("  2. Dispositivos não vinculados à conta IoT")
        print("  3. Região incorreta (US, EU, CN)")
        print()
        print("Acesse: https://iot.tuya.com/")
        exit(0)
    
    print(f"✅ {len(devices)} dispositivo(s) REAL encontrado(s)!")
    print()
    print("=" * 70)
    
    for i, device in enumerate(devices, 1):
        print(f"\n📱 DISPOSITIVO {i}:")
        print(f"   Nome: {device.get('name', 'Sem nome')}")
        print(f"   ID: {device['id']}")
        print(f"   Online: {'🟢 SIM' if device.get('online') else '🔴 NÃO'}")
        print(f"   Categoria: {device.get('category', 'N/A')}")
        print(f"   Produto: {device.get('product_name', 'N/A')}")
        
        # Status atual
        if device.get('online'):
            try:
                status = cloud.getstatus(device['id'])
                print(f"\n   📊 STATUS REAL:")
                if status and 'result' in status:
                    for item in status['result']:
                        code = item.get('code', 'N/A')
                        value = item.get('value', 'N/A')
                        print(f"      {code}: {value}")
                else:
                    print(f"      (Sem dados no momento)")
            except Exception as e:
                print(f"      ⚠️  Erro ao ler status: {e}")
    
    print()
    print("=" * 70)
    print()
    print("💾 Salvando JSON completo dos dispositivos...")
    
    # Salvar JSON
    timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tuya_devices_REAL_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(devices, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Salvo em: {filename}")
    print()
    print("🎯 PRÓXIMO PASSO:")
    print("   Use esses IDs para cadastrar os dispositivos no sistema!")
    print()

except ImportError:
    print("❌ ERRO: tinytuya não instalado")
    print("Execute: pip install tinytuya")
    exit(1)
except Exception as e:
    print(f"❌ ERRO ao conectar Tuya: {e}")
    print()
    print("Verifique:")
    print("  1. Credenciais corretas")
    print("  2. Internet funcionando")
    print("  3. Região correta (US, EU, CN)")
    exit(1)

