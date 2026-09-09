#!/usr/bin/env python3
"""
Monitor Tuya - Aguarda dispositivos ficarem ONLINE
APENAS dados REAIS!
"""

import os
import time
from dotenv import load_dotenv

print("=" * 70)
print("   MONITOR TUYA - Aguardando dispositivos ONLINE")
print("=" * 70)
print()

# Carregar credenciais
load_dotenv()

access_id = os.getenv("TUYA_ACCESS_ID")
access_secret = os.getenv("TUYA_ACCESS_SECRET")
region = os.getenv("TUYA_API_REGION", "us")

if not access_id or not access_secret:
    print("❌ ERRO: Credenciais não encontradas no .env")
    exit(1)

try:
    import tinytuya
    
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=access_id,
        apiSecret=access_secret
    )
    
    print("✅ Conectado ao Tuya Cloud")
    print()
    print("🔍 Procurando medidores de energia...")
    print()
    
    # IDs dos medidores identificados
    energy_meters = {
        "eb12907d3f923984f1wntb": "WIFI dual meter",
        "ebbef04296002afe3ecxcg": "Wifi Plug"
    }
    
    print("📊 Medidores configurados:")
    for device_id, name in energy_meters.items():
        print(f"   - {name} ({device_id[:10]}...)")
    print()
    print("⏳ Monitorando a cada 10 segundos... (Ctrl+C para parar)")
    print("   Ligue os medidores físicos para aparecerem aqui!")
    print()
    
    iteration = 0
    while True:
        iteration += 1
        print(f"\r🔄 Verificação #{iteration}...", end="", flush=True)
        
        try:
            devices = cloud.getdevices()
            
            online_count = 0
            for device in devices:
                if device['id'] in energy_meters and device.get('online'):
                    online_count += 1
                    name = energy_meters[device['id']]
                    
                    print(f"\n\n🟢 ONLINE DETECTADO: {name}")
                    print(f"   ID: {device['id']}")
                    
                    # Tentar ler status
                    try:
                        status = cloud.getstatus(device['id'])
                        if status and 'result' in status:
                            print(f"\n   📊 DADOS REAIS:")
                            for item in status['result']:
                                code = item.get('code', 'N/A')
                                value = item.get('value', 'N/A')
                                print(f"      {code}: {value}")
                        else:
                            print(f"      (Aguardando primeiras leituras...)")
                    except Exception as e:
                        print(f"      ⚠️  Erro ao ler: {e}")
                    
                    print()
            
            if online_count == 0:
                pass  # Continua monitorando
            elif online_count == len(energy_meters):
                print("\n\n✅ TODOS OS MEDIDORES ONLINE!")
                print("🎯 Pressione Ctrl+C para parar o monitor")
                print()
        
        except Exception as e:
            print(f"\n⚠️  Erro na verificação: {e}")
        
        time.sleep(10)

except KeyboardInterrupt:
    print("\n\n⏹️  Monitor parado pelo usuário")
    print()
except ImportError:
    print("❌ ERRO: tinytuya não instalado")
    print("Execute: pip install tinytuya")
    exit(1)
except Exception as e:
    print(f"❌ ERRO: {e}")
    exit(1)


