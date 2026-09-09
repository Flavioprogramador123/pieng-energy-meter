#!/usr/bin/env python3
"""
Teste de dispositivo ONLINE - Dados REAIS
"""

import os
import json
from dotenv import load_dotenv

print("=" * 70)
print("   TESTE DISPOSITIVO ONLINE - DADOS REAIS")
print("=" * 70)
print()

# Carregar credenciais
load_dotenv()

access_id = os.getenv("TUYA_ACCESS_ID")
access_secret = os.getenv("TUYA_ACCESS_SECRET")
region = os.getenv("TUYA_API_REGION", "us")

if not access_id or not access_secret:
    print("❌ Credenciais não encontradas")
    exit(1)

try:
    import tinytuya
    
    # Dispositivo ONLINE detectado
    device_id = "04708305d8bfc017c02e"
    device_name = "Controle ekaza"
    
    print(f"📱 Testando: {device_name}")
    print(f"   ID: {device_id}")
    print()
    
    # Conectar
    print("📡 Conectando Tuya Cloud API...")
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=access_id,
        apiSecret=access_secret
    )
    
    # Buscar informações do dispositivo
    print()
    print("🔍 Buscando informações do dispositivo...")
    devices = cloud.getdevices()
    
    device_info = None
    for d in devices:
        if d['id'] == device_id:
            device_info = d
            break
    
    if device_info:
        print(f"✅ Dispositivo encontrado!")
        print(f"   Nome: {device_info.get('name', 'N/A')}")
        print(f"   Online: {'🟢 SIM' if device_info.get('online') else '🔴 NÃO'}")
        print(f"   Categoria: {device_info.get('category', 'N/A')}")
        print(f"   Produto: {device_info.get('product_name', 'N/A')}")
    else:
        print("⚠️  Dispositivo não encontrado na lista")
    
    # Tentar ler STATUS REAL
    print()
    print("=" * 70)
    print("   📊 LENDO STATUS REAL DO DISPOSITIVO")
    print("=" * 70)
    print()
    
    try:
        status = cloud.getstatus(device_id)
        
        if status and 'result' in status:
            print(f"✅ Status obtido com sucesso!")
            print()
            print("📊 DADOS REAIS:")
            print()
            
            for item in status['result']:
                code = item.get('code', 'N/A')
                value = item.get('value', 'N/A')
                print(f"   {code}: {value}")
            
            # Salvar JSON
            print()
            print("💾 Salvando dados...")
            with open(f"device_{device_id}_status_REAL.json", 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
            print(f"✅ Salvo em: device_{device_id}_status_REAL.json")
        
        elif status and 'success' in status and not status['success']:
            print(f"⚠️  API retornou erro:")
            print(f"   {status.get('msg', 'Erro desconhecido')}")
        
        else:
            print(f"⚠️  Resposta inesperada:")
            print(json.dumps(status, indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"❌ Erro ao ler status: {e}")
    
    # Procurar MEDIDORES de energia
    print()
    print("=" * 70)
    print("   🔍 PROCURANDO MEDIDORES DE ENERGIA")
    print("=" * 70)
    print()
    
    energy_categories = ['cz', 'dlq', 'pc']  # Categorias de medidores
    energy_devices = []
    
    for d in devices:
        category = d.get('category', '')
        name = d.get('name', 'Sem nome')
        online = d.get('online', False)
        
        # Procurar por palavras-chave
        keywords = ['meter', 'medidor', 'energy', 'energia', 'plug', 'power', 'potencia']
        is_energy = any(kw in name.lower() for kw in keywords) or category in energy_categories
        
        if is_energy:
            status_icon = "🟢" if online else "🔴"
            energy_devices.append({
                'name': name,
                'id': d['id'],
                'online': online,
                'category': category
            })
            print(f"{status_icon} {name}")
            print(f"   ID: {d['id']}")
            print(f"   Categoria: {category}")
            print(f"   Online: {'SIM' if online else 'NÃO'}")
            print()
    
    if not energy_devices:
        print("⚠️  Nenhum medidor de energia encontrado")
        print()
        print("Dispositivos disponíveis:")
        for d in devices[:10]:  # Mostrar primeiros 10
            print(f"   - {d.get('name', 'N/A')} ({d.get('category', 'N/A')})")
    else:
        print(f"✅ {len(energy_devices)} medidor(es) encontrado(s)")
        
        # Tentar ler medidores online
        for meter in energy_devices:
            if meter['online']:
                print()
                print(f"📊 Testando leitura: {meter['name']}")
                try:
                    meter_status = cloud.getstatus(meter['id'])
                    if meter_status and 'result' in meter_status:
                        print(f"   ✅ Dados obtidos:")
                        for item in meter_status['result']:
                            print(f"      {item.get('code')}: {item.get('value')}")
                except Exception as e:
                    print(f"   ⚠️  Erro: {e}")
    
    print()
    print("=" * 70)
    print("   ✅ TESTE CONCLUÍDO")
    print("=" * 70)
    print()

except ImportError:
    print("❌ tinytuya não instalado")
    exit(1)
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)


