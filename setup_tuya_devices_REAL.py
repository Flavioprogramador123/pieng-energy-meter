#!/usr/bin/env python3
"""
Cadastra dispositivos Tuya REAIS no sistema
APENAS dispositivos com dados confirmados!
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

print("=" * 70)
print("   CADASTRAR DISPOSITIVOS TUYA REAIS")
print("=" * 70)
print()

# 1. Criar cliente
print("📝 Criando cliente...")

client_data = {
    "name": "PIENG Energy Monitor - Real",
    "external_id": "PIENG001"
}

try:
    response = requests.post(f"{API_BASE}/clients", json=client_data)
    
    if response.status_code == 200:
        client = response.json()
        client_id = client['id']
        print(f"✅ Cliente criado: ID {client_id}")
    else:
        print(f"⚠️  Cliente pode já existir, tentando usar ID 1")
        client_id = 1

except Exception as e:
    print(f"⚠️  Erro ao criar cliente: {e}")
    print(f"   Usando client_id = 1")
    client_id = 1

print()

# 2. Cadastrar Wifi Plug (com medição de energia)
print("📊 Cadastrando: Wifi Plug (medidor de energia)")

wifi_plug = {
    "client_id": client_id,
    "name": "Wifi Plug - Medidor REAL",
    "device_type": "tuya",
    "active": True,
    "config": {
        "device_id": "ebbef04296002afe3ecxcg",
        "device_name": "Wifi Plug",
        "category": "cz",
        "has_energy_monitoring": True,
        "metrics": [
            "switch_1",
            "add_ele",
            "cur_current",
            "cur_power", 
            "cur_voltage"
        ]
    }
}

try:
    response = requests.post(f"{API_BASE}/devices", json=wifi_plug)
    
    if response.status_code == 200:
        device = response.json()
        print(f"✅ Wifi Plug cadastrado: ID {device['id']}")
        print(f"   Métricas: energia, tensão, corrente, potência")
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Erro: {e}")

print()

# 3. Cadastrar Dvr (interruptor simples)
print("🔌 Cadastrando: Dvr (interruptor)")

dvr = {
    "client_id": client_id,
    "name": "Dvr - Interruptor REAL",
    "device_type": "tuya",
    "active": True,
    "config": {
        "device_id": "73634132ec94cb8039a6",
        "device_name": "Dvr",
        "category": "cz",
        "has_energy_monitoring": False,
        "metrics": [
            "switch_1",
            "relay_status"
        ]
    }
}

try:
    response = requests.post(f"{API_BASE}/devices", json=dvr)
    
    if response.status_code == 200:
        device = response.json()
        print(f"✅ Dvr cadastrado: ID {device['id']}")
        print(f"   Métricas: switch, relay_status")
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Erro: {e}")

print()

# 4. Verificar dispositivos cadastrados
print("=" * 70)
print("   📋 VERIFICANDO DISPOSITIVOS CADASTRADOS")
print("=" * 70)
print()

try:
    response = requests.get(f"{API_BASE}/devices")
    
    if response.status_code == 200:
        devices = response.json()
        
        print(f"✅ {len(devices)} dispositivo(s) no sistema:")
        print()
        
        for d in devices:
            device_type_icon = "📊" if d['device_type'] == 'tuya' else "⚙️"
            active_icon = "🟢" if d['active'] else "🔴"
            
            print(f"{device_type_icon} {active_icon} {d['name']}")
            print(f"   ID: {d['id']}")
            print(f"   Tipo: {d['device_type']}")
            print(f"   Cliente: {d['client_id']}")
            
            if 'config' in d and d['config']:
                config = json.loads(d['config']) if isinstance(d['config'], str) else d['config']
                if 'device_id' in config:
                    print(f"   Tuya ID: {config['device_id'][:10]}...")
            
            print()
    
    else:
        print(f"❌ Erro ao listar dispositivos: {response.status_code}")

except Exception as e:
    print(f"❌ Erro: {e}")

print("=" * 70)
print("   ✅ CADASTRO CONCLUÍDO")
print("=" * 70)
print()
print("🎯 Próximo passo:")
print("   1. Criar poller Tuya no backend")
print("   2. Ver dados no dashboard: http://localhost:8000/api/dashboard")
print()

