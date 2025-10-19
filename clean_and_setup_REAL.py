#!/usr/bin/env python3
"""
LIMPA banco e cadastra APENAS dispositivos REAIS
"""

import sqlite3
import requests
import json
from pathlib import Path

print("=" * 70)
print("   LIMPEZA TOTAL + CADASTRO APENAS REAL")
print("=" * 70)
print()

# 1. LIMPAR BANCO
print("🧹 LIMPANDO BANCO DE DADOS...")

db_path = "data/app.db"

if Path(db_path).exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Deletar TUDO
    cursor.execute("DELETE FROM alarm_events")
    cursor.execute("DELETE FROM alarm_rules")
    cursor.execute("DELETE FROM measurements")
    cursor.execute("DELETE FROM devices")
    cursor.execute("DELETE FROM clients")
    
    conn.commit()
    conn.close()
    
    print("✅ Banco limpo!")
else:
    print("⚠️  Banco não existe (será criado)")

print()

# 2. AGUARDAR BACKEND REINICIAR
print("⏳ Aguardando backend...")
import time
time.sleep(3)

API_BASE = "http://localhost:8000/api"

# 3. CRIAR CLIENTE REAL
print("📝 Criando cliente REAL...")

client_data = {
    "name": "PIENG Energy - Cliente Real",
    "external_id": "REAL001"
}

try:
    response = requests.post(f"{API_BASE}/clients", json=client_data, timeout=5)
    
    if response.status_code == 200:
        client = response.json()
        client_id = client['id']
        print(f"✅ Cliente criado: ID {client_id}")
    else:
        print(f"❌ Erro {response.status_code}: {response.text}")
        exit(1)

except Exception as e:
    print(f"❌ Erro: {e}")
    print("   Backend não está respondendo!")
    exit(1)

print()

# 4. CADASTRAR WIFI PLUG (Medidor de energia REAL)
print("📊 Cadastrando: Wifi Plug (DADOS REAIS)")

wifi_plug = {
    "client_id": client_id,
    "name": "Wifi Plug - Medidor Real",
    "device_type": "tuya",
    "active": True,
    "config": {
        "device_id": "ebbef04296002afe3ecxcg",
        "device_name": "Wifi Plug",
        "category": "cz",
        "has_energy_monitoring": True,
        "metrics": {
            "add_ele": "Energia acumulada (kWh)",
            "cur_current": "Corrente (A)",
            "cur_power": "Potência (W)",
            "cur_voltage": "Tensão (V)",
            "switch_1": "Estado (on/off)"
        }
    }
}

try:
    response = requests.post(f"{API_BASE}/devices", json=wifi_plug, timeout=5)
    
    if response.status_code == 200:
        device = response.json()
        wifi_plug_id = device['id']
        print(f"✅ Wifi Plug cadastrado: ID {wifi_plug_id}")
        print(f"   Métricas: energia, tensão, corrente, potência")
    else:
        print(f"❌ Erro {response.status_code}: {response.text}")

except Exception as e:
    print(f"❌ Erro: {e}")

print()

# 5. CADASTRAR DVR (Interruptor REAL)
print("🔌 Cadastrando: Dvr (DADOS REAIS)")

dvr = {
    "client_id": client_id,
    "name": "Dvr - Interruptor Real",
    "device_type": "tuya",
    "active": True,
    "config": {
        "device_id": "73634132ec94cb8039a6",
        "device_name": "Dvr",
        "category": "cz",
        "has_energy_monitoring": False,
        "metrics": {
            "switch_1": "Estado (on/off)",
            "relay_status": "Status do relé"
        }
    }
}

try:
    response = requests.post(f"{API_BASE}/devices", json=dvr, timeout=5)
    
    if response.status_code == 200:
        device = response.json()
        dvr_id = device['id']
        print(f"✅ Dvr cadastrado: ID {dvr_id}")
        print(f"   Métricas: switch, relay_status")
    else:
        print(f"❌ Erro {response.status_code}: {response.text}")

except Exception as e:
    print(f"❌ Erro: {e}")

print()

# 6. VERIFICAR
print("=" * 70)
print("   📋 DISPOSITIVOS NO SISTEMA")
print("=" * 70)
print()

try:
    response = requests.get(f"{API_BASE}/devices", timeout=5)
    
    if response.status_code == 200:
        devices = response.json()
        
        if len(devices) == 0:
            print("⚠️  Nenhum dispositivo cadastrado")
        else:
            print(f"✅ {len(devices)} dispositivo(s) REAL:")
            print()
            
            for d in devices:
                active_icon = "🟢" if d['active'] else "🔴"
                print(f"{active_icon} {d['name']}")
                print(f"   ID: {d['id']} | Tipo: {d['device_type']}")
                
                if d['config']:
                    config = json.loads(d['config']) if isinstance(d['config'], str) else d['config']
                    if 'device_id' in config:
                        print(f"   Tuya ID: {config['device_id'][:15]}...")
                print()

except Exception as e:
    print(f"❌ Erro: {e}")

print("=" * 70)
print("   ✅ SETUP CONCLUÍDO - APENAS DADOS REAIS!")
print("=" * 70)
print()
print("🎯 Dashboard: http://localhost:8000/api/dashboard")
print()

