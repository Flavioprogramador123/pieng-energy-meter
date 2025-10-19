#!/usr/bin/env python3
"""
Testa o endpoint da API de métricas
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("   🧪 TESTE - API DE MÉTRICAS")
print("=" * 80)
print()

# 1. Listar dispositivos
print("📋 1. Listando dispositivos...")
try:
    r = requests.get(f"{BASE_URL}/api/devices")
    devices = r.json()
    print(f"✅ {len(devices)} dispositivo(s) encontrado(s)")
    for d in devices:
        print(f"   • ID {d['id']}: {d['name']} ({d['device_type']})")
    print()
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)

if not devices:
    print("⚠️  Nenhum dispositivo cadastrado!")
    exit(1)

# Usar o primeiro dispositivo (Wifi Plug)
device_id = devices[0]['id']
device_name = devices[0]['name']

print(f"📊 2. Buscando métricas do dispositivo '{device_name}' (ID {device_id})...")
print()

# Métricas para testar
metrics_to_test = ['energy_wh', 'voltage', 'current', 'power']

for metric in metrics_to_test:
    try:
        r = requests.get(f"{BASE_URL}/api/metrics", params={
            'device_id': device_id,
            'metric': metric,
            'limit': 5
        })
        
        if r.status_code == 200:
            data = r.json()
            print(f"✅ {metric}:")
            print(f"   • Total de medições: {len(data)}")
            
            if data:
                print(f"   • Última medição:")
                print(f"      - Valor: {data[0]['value']}")
                print(f"      - Timestamp: {data[0]['timestamp']}")
            else:
                print(f"   ⚠️  Nenhuma medição encontrada")
        else:
            print(f"❌ {metric}: HTTP {r.status_code}")
        
        print()
    
    except Exception as e:
        print(f"❌ {metric}: Erro - {e}")
        print()

print("=" * 80)
print("   🔍 TESTE DE URL EXATA DO DASHBOARD")
print("=" * 80)
print()

# Testar a URL exata que o dashboard usa
url = f"{BASE_URL}/api/metrics?device_id={device_id}&metric=voltage&limit=100"
print(f"URL: {url}")
print()

try:
    r = requests.get(url)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"✅ {len(data)} medição(ões) retornada(s)")
        
        if data:
            print()
            print("📊 Primeiras 3 medições:")
            for i, m in enumerate(data[:3]):
                print(f"   {i+1}. Valor: {m['value']:.2f}, Timestamp: {m['timestamp']}")
        else:
            print("⚠️  Array vazio retornado!")
    else:
        print(f"❌ Erro HTTP {r.status_code}")
        print(f"Resposta: {r.text}")

except Exception as e:
    print(f"❌ Erro: {e}")

print()
print("=" * 80)
print("   ✅ TESTE CONCLUÍDO")
print("=" * 80)
print()

