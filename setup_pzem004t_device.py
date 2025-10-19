#!/usr/bin/env python3
"""
Cadastra dispositivo PZEM-004T no sistema
Suporta Modbus RTU (Serial) e Modbus TCP (via conversor)
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"{' ' * ((80 - len(title)) // 2)}{title}")
    print("=" * 80 + "\n")

def create_client(client_name: str):
    url = f"{BASE_URL}/api/clients"
    payload = {"name": client_name, "external_id": f"CLIENT_{client_name.upper().replace(' ', '_')}"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        client = response.json()
        print(f"✅ Cliente criado: ID {client['id']}")
        return client['id']
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao criar cliente: {e}")
        return None

def create_device(client_id: int, device_name: str, device_type: str, config: dict):
    url = f"{BASE_URL}/api/devices"
    payload = {
        "client_id": client_id,
        "name": device_name,
        "device_type": device_type,
        "active": True,
        "config": config
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        device = response.json()
        print(f"✅ {device_name} cadastrado: ID {device['id']}")
        return device['id']
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao cadastrar {device_name}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Resposta do servidor: {e.response.text}")
        return None

def setup_pzem004t_devices():
    print_header("📊 CADASTRO DE DISPOSITIVOS PZEM-004T")
    
    print("Escolha o tipo de conexão:\n")
    print("1. Modbus RTU (Serial - RS485 direto)")
    print("2. Modbus TCP (RS485 via Elfin-EW11A / USR-G771)")
    print()
    
    choice = input("Digite 1 ou 2: ").strip()
    
    if choice not in ['1', '2']:
        print("❌ Opção inválida!")
        return
    
    print()
    
    # Criar ou usar cliente existente
    client_name = input("Nome do cliente (ex: 'Fidelco Montagem'): ").strip()
    if not client_name:
        client_name = "Cliente Padrão"
    
    print()
    client_id = create_client(client_name)
    if not client_id:
        return
    
    print()
    device_name = input("Nome do dispositivo (ex: 'PZEM-004T - Sala de Montagem'): ").strip()
    if not device_name:
        device_name = "PZEM-004T - Sem Nome"
    
    print()
    
    if choice == '1':
        # Modbus RTU (Serial)
        print("📋 CONFIGURAÇÃO MODBUS RTU (Serial):\n")
        
        port = input("Porta COM (ex: COM3, /dev/ttyUSB0) [COM3]: ").strip() or "COM3"
        slave_id = input("Slave ID [1]: ").strip() or "1"
        baudrate = input("Baudrate [9600]: ").strip() or "9600"
        timeout = input("Timeout (segundos) [0.5]: ").strip() or "0.5"
        
        config = {
            "port": port,
            "slave_id": int(slave_id),
            "baudrate": int(baudrate),
            "timeout": float(timeout),
            "driver": "pzem004t",
            "base": 0
        }
        
        device_type = "modbus"
        
        print()
        print("📝 Configuração:")
        print(json.dumps(config, indent=2))
        print()
        
        confirm = input("Confirmar cadastro? (s/n): ").strip().lower()
        if confirm != 's':
            print("❌ Cadastro cancelado!")
            return
        
        print()
        create_device(client_id, device_name, device_type, config)
    
    else:
        # Modbus TCP
        print("📋 CONFIGURAÇÃO MODBUS TCP (Conversor RS485→WiFi/Ethernet):\n")
        
        host = input("IP do conversor (ex: 192.168.1.100): ").strip()
        if not host:
            print("❌ IP obrigatório!")
            return
        
        port = input("Porta Modbus [502]: ").strip() or "502"
        slave_id = input("Slave ID [1]: ").strip() or "1"
        timeout = input("Timeout (segundos) [3.0]: ").strip() or "3.0"
        
        config = {
            "host": host,
            "port": int(port),
            "slave_id": int(slave_id),
            "timeout": float(timeout),
            "driver": "pzem004t",
            "base": 0
        }
        
        device_type = "modbus_tcp"
        
        print()
        print("📝 Configuração:")
        print(json.dumps(config, indent=2))
        print()
        
        confirm = input("Confirmar cadastro? (s/n): ").strip().lower()
        if confirm != 's':
            print("❌ Cadastro cancelado!")
            return
        
        print()
        create_device(client_id, device_name, device_type, config)
    
    print()
    print_header("✅ CADASTRO CONCLUÍDO")
    
    print("🎯 Próximos passos:")
    print("   1. O poller vai coletar dados a cada 30 segundos")
    print("   2. Veja o dashboard: http://localhost:8000/api/dashboard")
    print("   3. Verifique os logs: type data\\audit.log")
    print()
    
    print("📊 Métricas coletadas do PZEM-004T:")
    print("   • voltage (V)")
    print("   • current (A)")
    print("   • power (W)")
    print("   • energy_wh (Wh)")
    print()

if __name__ == "__main__":
    setup_pzem004t_devices()

