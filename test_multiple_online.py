#!/usr/bin/env python3
"""
Teste MÚLTIPLOS dispositivos ONLINE - Dados REAIS
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

print("=" * 70)
print("   TESTE MÚLTIPLOS DISPOSITIVOS ONLINE - DADOS REAIS")
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
    
    # Dispositivos ONLINE detectados
    devices_to_test = [
        {
            "id": "04708305d8bfc017c02e",
            "name": "Controle ekaza",
            "category": "wnykq",
            "type": "Controle Universal"
        },
        {
            "id": "eb9a1c787c60d712fazces",
            "name": "PC473_OUYOU",
            "category": "tdq",
            "type": "Interruptor Inteligente"
        }
    ]
    
    print("📱 Dispositivos para testar:")
    for d in devices_to_test:
        print(f"   - {d['name']} ({d['type']})")
    print()
    
    # Conectar
    print("📡 Conectando Tuya Cloud API...")
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=access_id,
        apiSecret=access_secret
    )
    print("✅ Conectado!")
    print()
    
    # Buscar todos os dispositivos
    print("🔍 Buscando lista completa de dispositivos...")
    all_devices = cloud.getdevices()
    print(f"✅ {len(all_devices)} dispositivos na conta")
    print()
    
    # Testar cada dispositivo
    results = []
    
    for device_to_test in devices_to_test:
        device_id = device_to_test["id"]
        device_name = device_to_test["name"]
        
        print("=" * 70)
        print(f"   📱 TESTANDO: {device_name}")
        print("=" * 70)
        print()
        
        # Buscar info do dispositivo
        device_info = None
        for d in all_devices:
            if d['id'] == device_id:
                device_info = d
                break
        
        if device_info:
            online_status = device_info.get('online', False)
            status_icon = "🟢" if online_status else "🔴"
            
            print(f"✅ Dispositivo encontrado!")
            print(f"   Nome: {device_info.get('name', 'N/A')}")
            print(f"   Status: {status_icon} {'ONLINE' if online_status else 'OFFLINE'}")
            print(f"   Categoria: {device_info.get('category', 'N/A')}")
            print(f"   Produto: {device_info.get('product_name', 'N/A')}")
            print()
            
            # Tentar ler STATUS REAL
            print("📊 Lendo STATUS REAL...")
            try:
                status = cloud.getstatus(device_id)
                
                if status and 'result' in status:
                    result_data = status['result']
                    
                    if len(result_data) > 0:
                        print(f"✅ {len(result_data)} dados obtidos!")
                        print()
                        print("📊 DADOS REAIS:")
                        
                        for item in result_data:
                            code = item.get('code', 'N/A')
                            value = item.get('value', 'N/A')
                            print(f"   {code}: {value}")
                        
                        # Salvar resultado
                        results.append({
                            "device_id": device_id,
                            "device_name": device_name,
                            "online": online_status,
                            "timestamp": datetime.now().isoformat(),
                            "data": result_data
                        })
                        
                        # Salvar JSON individual
                        filename = f"device_{device_id}_REAL.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(status, f, indent=2, ensure_ascii=False)
                        print()
                        print(f"💾 Salvo em: {filename}")
                    
                    else:
                        print("⚠️  Nenhum dado disponível no momento")
                        results.append({
                            "device_id": device_id,
                            "device_name": device_name,
                            "online": online_status,
                            "timestamp": datetime.now().isoformat(),
                            "data": []
                        })
                
                else:
                    print(f"⚠️  Resposta inesperada da API")
                    if status:
                        print(json.dumps(status, indent=2, ensure_ascii=False))
            
            except Exception as e:
                print(f"❌ Erro ao ler status: {e}")
                results.append({
                    "device_id": device_id,
                    "device_name": device_name,
                    "online": online_status,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })
        
        else:
            print(f"⚠️  Dispositivo {device_id} não encontrado na lista")
        
        print()
    
    # Procurar medidores de energia ONLINE
    print("=" * 70)
    print("   🔍 PROCURANDO MEDIDORES DE ENERGIA ONLINE")
    print("=" * 70)
    print()
    
    energy_categories = ['cz', 'dlq', 'pc', 'kg']
    energy_keywords = ['meter', 'medidor', 'energy', 'energia', 'plug', 'power', 'potencia', 'wifi']
    
    online_energy_devices = []
    
    for d in all_devices:
        category = d.get('category', '')
        name = d.get('name', 'Sem nome')
        online = d.get('online', False)
        
        # Verificar se é medidor
        is_energy = (
            category in energy_categories or
            any(kw in name.lower() for kw in energy_keywords)
        )
        
        if is_energy and online:
            print(f"🟢 ONLINE: {name}")
            print(f"   ID: {d['id']}")
            print(f"   Categoria: {category}")
            
            online_energy_devices.append(d)
            
            # Tentar ler dados REAIS
            try:
                print(f"   📊 Lendo dados REAIS...")
                meter_status = cloud.getstatus(d['id'])
                
                if meter_status and 'result' in meter_status:
                    meter_data = meter_status['result']
                    
                    if len(meter_data) > 0:
                        print(f"   ✅ {len(meter_data)} dados obtidos:")
                        
                        for item in meter_data:
                            code = item.get('code', 'N/A')
                            value = item.get('value', 'N/A')
                            print(f"      • {code}: {value}")
                        
                        # Este é um medidor COM DADOS!
                        results.append({
                            "device_id": d['id'],
                            "device_name": name,
                            "online": True,
                            "category": category,
                            "is_energy_meter": True,
                            "timestamp": datetime.now().isoformat(),
                            "data": meter_data
                        })
                        
                        # Salvar
                        filename = f"energy_meter_{d['id']}_REAL.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(meter_status, f, indent=2, ensure_ascii=False)
                        print(f"      💾 Salvo: {filename}")
                    else:
                        print(f"      ⚠️  Sem dados no momento")
                else:
                    print(f"      ⚠️  Resposta vazia")
            
            except Exception as e:
                print(f"      ❌ Erro: {e}")
            
            print()
    
    if not online_energy_devices:
        print("⚠️  Nenhum medidor de energia ONLINE no momento")
        print()
        print("📋 Medidores identificados (OFFLINE):")
        
        for d in all_devices:
            category = d.get('category', '')
            name = d.get('name', 'Sem nome')
            online = d.get('online', False)
            
            is_energy = (
                category in energy_categories or
                any(kw in name.lower() for kw in energy_keywords)
            )
            
            if is_energy and not online:
                print(f"   🔴 {name} (ID: {d['id'][:10]}...)")
    
    # Salvar resumo geral
    print()
    print("=" * 70)
    print("   💾 SALVANDO RESUMO GERAL")
    print("=" * 70)
    print()
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_devices": len(all_devices),
        "devices_tested": len(devices_to_test),
        "results": results
    }
    
    summary_file = f"tuya_test_summary_REAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Resumo salvo: {summary_file}")
    print()
    print(f"📊 Estatísticas:")
    print(f"   Total de dispositivos: {len(all_devices)}")
    print(f"   Dispositivos testados: {len(devices_to_test)}")
    print(f"   Medidores online: {len(online_energy_devices)}")
    print(f"   Resultados coletados: {len(results)}")
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

