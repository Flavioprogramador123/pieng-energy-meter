#!/usr/bin/env python3
"""
Sistema de Cadastro Interativo de Dispositivos
PIENG Energy Meter - 4 Engines
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"{' ' * ((80 - len(title)) // 2)}{title}")
    print("=" * 80 + "\n")

def create_client(client_name: str):
    """Cria um novo cliente"""
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

def list_clients():
    """Lista clientes existentes"""
    try:
        response = requests.get(f"{BASE_URL}/api/clients")
        response.raise_for_status()
        return response.json()
    except:
        return []

def create_device(client_id: int, device_name: str, device_type: str, config: dict):
    """Cadastra um novo dispositivo"""
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

def main():
    print_header("📱 CADASTRO DE DISPOSITIVOS - PIENG ENERGY METER")
    
    print("🚀 ENGINES DISPONÍVEIS:\n")
    print("1. Tuya Cloud API (Medidores WiFi)")
    print("2. PZEM-004T via Modbus RTU (Serial RS485)")
    print("3. PZEM-004T via Modbus TCP (Conversor WiFi/4G)")
    print("4. Eastron SDM630 via Modbus RTU (Serial RS485)")
    print("5. Eastron SDM630 via Modbus TCP (Conversor WiFi/4G)")
    print("6. Dispositivo Modbus Genérico")
    print()
    
    choice = input("Qual dispositivo você quer cadastrar? (1-6): ").strip()
    
    if choice not in ['1', '2', '3', '4', '5', '6']:
        print("❌ Opção inválida!")
        return
    
    print()
    
    # Selecionar ou criar cliente
    clients = list_clients()
    
    if clients:
        print("📋 Clientes existentes:\n")
        for i, client in enumerate(clients):
            print(f"{i+1}. {client['name']} (ID {client['id']})")
        print(f"{len(clients)+1}. Criar novo cliente")
        print()
        
        client_choice = input(f"Selecione o cliente (1-{len(clients)+1}): ").strip()
        
        try:
            idx = int(client_choice) - 1
            if 0 <= idx < len(clients):
                client_id = clients[idx]['id']
                print(f"✅ Usando cliente: {clients[idx]['name']}")
            else:
                client_name = input("\nNome do novo cliente: ").strip()
                if not client_name:
                    client_name = "Cliente Padrão"
                client_id = create_client(client_name)
                if not client_id:
                    return
        except ValueError:
            print("❌ Opção inválida!")
            return
    else:
        client_name = input("Nome do cliente: ").strip()
        if not client_name:
            client_name = "Cliente Padrão"
        client_id = create_client(client_name)
        if not client_id:
            return
    
    print()
    device_name = input("Nome do dispositivo: ").strip()
    if not device_name:
        device_name = "Dispositivo Sem Nome"
    
    print()
    
    config = {}
    device_type = ""
    
    # Configuração específica por tipo
    if choice == '1':
        # Tuya
        print("📋 TUYA CLOUD API\n")
        print("⚠️  Execute primeiro: python test_tuya_real.py")
        print("   Para ver os IDs dos seus dispositivos Tuya\n")
        
        tuya_device_id = input("Device ID Tuya (ex: ebbef04296002afe3ecxcg): ").strip()
        if not tuya_device_id:
            print("❌ Device ID obrigatório!")
            return
        
        config = {
            "device_id": tuya_device_id,
            "metrics": ["energy", "voltage", "current", "power"]
        }
        device_type = "tuya"
    
    elif choice == '2':
        # PZEM-004T RTU
        print("📋 PZEM-004T via MODBUS RTU (Serial)\n")
        
        port = input("Porta COM (ex: COM3, /dev/ttyUSB0) [COM3]: ").strip() or "COM3"
        slave_id = input("Slave ID [1]: ").strip() or "1"
        baudrate = input("Baudrate [9600]: ").strip() or "9600"
        timeout = input("Timeout (s) [0.5]: ").strip() or "0.5"
        
        config = {
            "port": port,
            "slave_id": int(slave_id),
            "baudrate": int(baudrate),
            "timeout": float(timeout),
            "driver": "pzem004t",
            "base": 0
        }
        device_type = "modbus"
    
    elif choice == '3':
        # PZEM-004T TCP
        print("📋 PZEM-004T via MODBUS TCP (Conversor WiFi/4G)\n")
        
        host = input("IP do conversor (ex: 192.168.1.100): ").strip()
        if not host:
            print("❌ IP obrigatório!")
            return
        
        port = input("Porta [502]: ").strip() or "502"
        slave_id = input("Slave ID [1]: ").strip() or "1"
        timeout = input("Timeout (s) [3.0]: ").strip() or "3.0"
        
        config = {
            "host": host,
            "port": int(port),
            "slave_id": int(slave_id),
            "timeout": float(timeout),
            "driver": "pzem004t",
            "base": 0
        }
        device_type = "modbus_tcp"
    
    elif choice == '4':
        # SDM630 RTU
        print("📋 EASTRON SDM630 via MODBUS RTU (Serial)\n")
        
        port = input("Porta COM (ex: COM4, /dev/ttyUSB1) [COM4]: ").strip() or "COM4"
        slave_id = input("Slave ID [2]: ").strip() or "2"
        baudrate = input("Baudrate [9600]: ").strip() or "9600"
        timeout = input("Timeout (s) [1.0]: ").strip() or "1.0"
        
        config = {
            "port": port,
            "slave_id": int(slave_id),
            "baudrate": int(baudrate),
            "timeout": float(timeout),
            "driver": "sdm630",
            "base": 0
        }
        device_type = "modbus"
    
    elif choice == '5':
        # SDM630 TCP
        print("📋 EASTRON SDM630 via MODBUS TCP (Conversor WiFi/4G)\n")
        
        host = input("IP do conversor (ex: 192.168.1.101): ").strip()
        if not host:
            print("❌ IP obrigatório!")
            return
        
        port = input("Porta [502]: ").strip() or "502"
        slave_id = input("Slave ID [2]: ").strip() or "2"
        timeout = input("Timeout (s) [3.0]: ").strip() or "3.0"
        
        config = {
            "host": host,
            "port": int(port),
            "slave_id": int(slave_id),
            "timeout": float(timeout),
            "driver": "sdm630",
            "base": 0
        }
        device_type = "modbus_tcp"
    
    elif choice == '6':
        # Genérico
        print("📋 DISPOSITIVO MODBUS GENÉRICO\n")
        print("Escolha o tipo de conexão:\n")
        print("1. Modbus RTU (Serial)")
        print("2. Modbus TCP (Ethernet/WiFi)")
        print()
        
        conn_type = input("Digite 1 ou 2: ").strip()
        
        if conn_type == '1':
            port = input("Porta COM [COM5]: ").strip() or "COM5"
            slave_id = input("Slave ID [1]: ").strip() or "1"
            baudrate = input("Baudrate [9600]: ").strip() or "9600"
            
            config = {
                "port": port,
                "slave_id": int(slave_id),
                "baudrate": int(baudrate),
                "timeout": 1.0,
                "base": 0,
                "count": 4,
                "metrics": ["voltage", "current", "power", "energy_wh"]
            }
            device_type = "modbus"
        
        elif conn_type == '2':
            host = input("IP do dispositivo: ").strip()
            if not host:
                print("❌ IP obrigatório!")
                return
            
            config = {
                "host": host,
                "port": 502,
                "slave_id": 1,
                "timeout": 3.0,
                "base": 0,
                "count": 4,
                "metrics": ["voltage", "current", "power", "energy_wh"]
            }
            device_type = "modbus_tcp"
        else:
            print("❌ Opção inválida!")
            return
    
    # Confirmar cadastro
    print()
    print_header("📝 REVISÃO DO CADASTRO")
    
    print(f"Nome do dispositivo: {device_name}")
    print(f"Tipo: {device_type}")
    print(f"Configuração:")
    print(json.dumps(config, indent=2))
    print()
    
    confirm = input("Confirmar cadastro? (s/n): ").strip().lower()
    if confirm != 's':
        print("❌ Cadastro cancelado!")
        return
    
    print()
    device_id = create_device(client_id, device_name, device_type, config)
    
    if device_id:
        print()
        print_header("✅ DISPOSITIVO CADASTRADO COM SUCESSO!")
        
        print("🎯 Próximos passos:\n")
        print("   1. O poller vai coletar dados a cada 30 segundos")
        print("   2. Atualize o dashboard: http://localhost:8000/api/dashboard")
        print("   3. Verifique os logs: type data\\audit.log")
        print()
        
        print("📊 Para ver todos os dispositivos:")
        print("   python show_engines_status.py")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado pelo usuário!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

