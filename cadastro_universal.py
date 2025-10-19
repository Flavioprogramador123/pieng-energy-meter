#!/usr/bin/env python3
"""
Sistema Universal de Cadastro de Dispositivos
PIENG Energy Meter - Suporta QUALQUER marca, modelo e protocolo
"""

import requests
import json
import os
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"{' ' * ((80 - len(title)) // 2)}{title}")
    print("=" * 80 + "\n")

def print_section(title: str):
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80 + "\n")

# ============================================================================
# TEMPLATES DE DISPOSITIVOS POPULARES
# ============================================================================

DEVICE_TEMPLATES = {
    # TUYA
    "tuya_meter": {
        "name": "Medidor Tuya (WiFi)",
        "device_type": "tuya",
        "protocol": "Cloud API",
        "config": {
            "device_id": "<ID_DO_DISPOSITIVO>",
            "metrics": ["energy", "voltage", "current", "power"]
        },
        "fields": ["device_id"]
    },
    
    # PZEM-004T
    "pzem_serial": {
        "name": "PZEM-004T (Serial RS485)",
        "device_type": "modbus",
        "protocol": "Modbus RTU",
        "config": {
            "port": "COM3",
            "slave_id": 1,
            "baudrate": 9600,
            "timeout": 0.5,
            "driver": "pzem004t",
            "base": 0
        },
        "fields": ["port", "slave_id", "baudrate"]
    },
    
    "pzem_tcp": {
        "name": "PZEM-004T (WiFi/Ethernet)",
        "device_type": "modbus_tcp",
        "protocol": "Modbus TCP",
        "config": {
            "host": "192.168.1.100",
            "port": 502,
            "slave_id": 1,
            "timeout": 3.0,
            "driver": "pzem004t",
            "base": 0
        },
        "fields": ["host", "port", "slave_id"]
    },
    
    # EASTRON SDM630
    "sdm630_serial": {
        "name": "Eastron SDM630 (Serial RS485)",
        "device_type": "modbus",
        "protocol": "Modbus RTU",
        "config": {
            "port": "COM4",
            "slave_id": 2,
            "baudrate": 9600,
            "timeout": 1.0,
            "driver": "sdm630",
            "base": 0
        },
        "fields": ["port", "slave_id", "baudrate"]
    },
    
    "sdm630_tcp": {
        "name": "Eastron SDM630 (WiFi/Ethernet)",
        "device_type": "modbus_tcp",
        "protocol": "Modbus TCP",
        "config": {
            "host": "192.168.1.101",
            "port": 502,
            "slave_id": 2,
            "timeout": 3.0,
            "driver": "sdm630",
            "base": 0
        },
        "fields": ["host", "port", "slave_id"]
    },
    
    # GENÉRICOS
    "modbus_rtu_generic": {
        "name": "Qualquer Modbus RTU (Serial)",
        "device_type": "modbus",
        "protocol": "Modbus RTU",
        "config": {
            "port": "COM5",
            "slave_id": 1,
            "baudrate": 9600,
            "timeout": 1.0,
            "base": 0,
            "count": 10,
            "metrics": ["voltage", "current", "power", "energy_wh"]
        },
        "fields": ["port", "slave_id", "baudrate", "base", "count"]
    },
    
    "modbus_tcp_generic": {
        "name": "Qualquer Modbus TCP (Ethernet/WiFi)",
        "device_type": "modbus_tcp",
        "protocol": "Modbus TCP",
        "config": {
            "host": "192.168.1.200",
            "port": 502,
            "slave_id": 1,
            "timeout": 3.0,
            "base": 0,
            "count": 10,
            "metrics": ["voltage", "current", "power", "energy_wh"]
        },
        "fields": ["host", "port", "slave_id", "base", "count"]
    },
    
    # OUTROS PROTOCOLOS (PREPARADO PARA EXPANSÃO)
    "custom": {
        "name": "Dispositivo Customizado",
        "device_type": "custom",
        "protocol": "Custom",
        "config": {},
        "fields": []
    }
}

# ============================================================================
# FUNÇÕES DE API
# ============================================================================

def list_clients():
    """Lista clientes existentes"""
    try:
        response = requests.get(f"{BASE_URL}/api/clients")
        response.raise_for_status()
        return response.json()
    except:
        return []

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
            print(f"   Resposta: {e.response.text}")
        return None

# ============================================================================
# MODO 1: CADASTRO ASSISTIDO POR TEMPLATE
# ============================================================================

def cadastro_por_template():
    """Cadastro usando templates predefinidos"""
    print_header("📋 CADASTRO ASSISTIDO - TEMPLATES")
    
    print("🔧 DISPOSITIVOS DISPONÍVEIS:\n")
    
    templates_list = list(DEVICE_TEMPLATES.items())
    
    for i, (key, template) in enumerate(templates_list):
        print(f"{i+1:2d}. {template['name']:40s} [{template['protocol']}]")
    
    print()
    choice = input(f"Escolha um dispositivo (1-{len(templates_list)}): ").strip()
    
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(templates_list):
            print("❌ Opção inválida!")
            return
    except ValueError:
        print("❌ Opção inválida!")
        return
    
    template_key, template = templates_list[idx]
    
    print_section(f"Cadastrando: {template['name']}")
    
    # Selecionar cliente
    clients = list_clients()
    
    if clients:
        print("📋 Clientes existentes:\n")
        for i, client in enumerate(clients):
            print(f"{i+1}. {client['name']} (ID {client['id']})")
        print(f"{len(clients)+1}. Criar novo cliente")
        print()
        
        client_choice = input(f"Selecione (1-{len(clients)+1}): ").strip()
        
        try:
            idx = int(client_choice) - 1
            if 0 <= idx < len(clients):
                client_id = clients[idx]['id']
            else:
                client_name = input("\nNome do novo cliente: ").strip()
                client_id = create_client(client_name or "Cliente Padrão")
                if not client_id:
                    return
        except ValueError:
            print("❌ Opção inválida!")
            return
    else:
        client_name = input("Nome do cliente: ").strip()
        client_id = create_client(client_name or "Cliente Padrão")
        if not client_id:
            return
    
    print()
    device_name = input(f"Nome do dispositivo [{template['name']}]: ").strip()
    device_name = device_name or template['name']
    
    # Configurar campos
    print_section("Configuração do Dispositivo")
    
    config = template['config'].copy()
    
    print(f"📝 Configure os parâmetros (Enter = usar padrão)\n")
    
    for field in template.get('fields', []):
        default_value = config.get(field, "")
        user_input = input(f"   {field:20s} [{default_value}]: ").strip()
        
        if user_input:
            # Tentar converter para o tipo correto
            if field in ['slave_id', 'baudrate', 'port', 'count', 'base'] and user_input.isdigit():
                config[field] = int(user_input)
            elif field == 'timeout':
                try:
                    config[field] = float(user_input)
                except:
                    config[field] = user_input
            else:
                config[field] = user_input
    
    # Adicionar campos customizados
    print()
    add_custom = input("Adicionar campos customizados? (s/n): ").strip().lower()
    
    if add_custom == 's':
        print("\n📝 Adicionar campos (digite 'fim' para terminar):\n")
        while True:
            field_name = input("   Nome do campo (ou 'fim'): ").strip()
            if field_name.lower() == 'fim':
                break
            
            field_value = input(f"   Valor de '{field_name}': ").strip()
            
            # Tentar detectar tipo
            if field_value.isdigit():
                config[field_name] = int(field_value)
            elif field_value.replace('.', '', 1).isdigit():
                config[field_name] = float(field_value)
            elif field_value.lower() in ['true', 'false']:
                config[field_name] = field_value.lower() == 'true'
            else:
                config[field_name] = field_value
    
    # Confirmar
    print_section("Revisão do Cadastro")
    
    print(f"Cliente ID: {client_id}")
    print(f"Nome: {device_name}")
    print(f"Tipo: {template['device_type']}")
    print(f"Protocolo: {template['protocol']}")
    print(f"\nConfiguração:")
    print(json.dumps(config, indent=2))
    print()
    
    confirm = input("Confirmar cadastro? (s/n): ").strip().lower()
    
    if confirm == 's':
        print()
        device_id = create_device(client_id, device_name, template['device_type'], config)
        
        if device_id:
            print_section("✅ SUCESSO!")
            print(f"Dispositivo cadastrado: ID {device_id}")
            print(f"\n🔄 O poller vai começar a coletar dados em até 30 segundos!")
            print(f"🌐 Dashboard: http://localhost:8000/api/dashboard")
    else:
        print("❌ Cadastro cancelado!")

# ============================================================================
# MODO 2: CADASTRO MANUAL COMPLETO
# ============================================================================

def cadastro_manual():
    """Cadastro 100% manual para dispositivos não listados"""
    print_header("⚙️  CADASTRO MANUAL - DISPOSITIVO CUSTOMIZADO")
    
    print("📝 Este modo permite cadastrar QUALQUER dispositivo!")
    print("   Configure todos os parâmetros manualmente.\n")
    
    # Cliente
    clients = list_clients()
    
    if clients:
        print("📋 Clientes:\n")
        for i, client in enumerate(clients):
            print(f"{i+1}. {client['name']}")
        print(f"{len(clients)+1}. Novo cliente")
        print()
        
        choice = input(f"Selecione (1-{len(clients)+1}): ").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(clients):
                client_id = clients[idx]['id']
            else:
                client_name = input("\nNome do novo cliente: ").strip()
                client_id = create_client(client_name or "Cliente Padrão")
        except:
            print("❌ Opção inválida!")
            return
    else:
        client_name = input("Nome do cliente: ").strip()
        client_id = create_client(client_name or "Cliente Padrão")
    
    if not client_id:
        return
    
    print_section("Informações Básicas")
    
    device_name = input("Nome do dispositivo: ").strip()
    if not device_name:
        print("❌ Nome obrigatório!")
        return
    
    print("\n📋 Tipos de dispositivo disponíveis:")
    print("   1. tuya         - Dispositivos Tuya Cloud")
    print("   2. modbus       - Modbus RTU (Serial)")
    print("   3. modbus_tcp   - Modbus TCP (Ethernet/WiFi)")
    print("   4. custom       - Outro (customizado)")
    print()
    
    device_type_map = {
        '1': 'tuya',
        '2': 'modbus',
        '3': 'modbus_tcp',
        '4': 'custom'
    }
    
    type_choice = input("Tipo (1-4): ").strip()
    device_type = device_type_map.get(type_choice, 'custom')
    
    print_section("Configuração JSON")
    
    print("📝 Forneça a configuração em formato JSON")
    print("   Exemplo para Modbus TCP:")
    print('   {"host": "192.168.1.100", "port": 502, "slave_id": 1}')
    print()
    print("   Digite linha por linha, 'fim' para terminar:")
    print()
    
    config_lines = []
    while True:
        line = input("   ")
        if line.strip().lower() == 'fim':
            break
        config_lines.append(line)
    
    config_str = '\n'.join(config_lines)
    
    try:
        config = json.loads(config_str)
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON inválido: {e}")
        print("\n📝 Criando configuração vazia...")
        config = {}
    
    # Confirmar
    print_section("Revisão")
    
    print(f"Nome: {device_name}")
    print(f"Tipo: {device_type}")
    print(f"Configuração:")
    print(json.dumps(config, indent=2))
    print()
    
    confirm = input("Confirmar? (s/n): ").strip().lower()
    
    if confirm == 's':
        print()
        device_id = create_device(client_id, device_name, device_type, config)
        
        if device_id:
            print_section("✅ SUCESSO!")
            print(f"Dispositivo customizado cadastrado: ID {device_id}")

# ============================================================================
# MODO 3: IMPORTAÇÃO EM LOTE (JSON/CSV)
# ============================================================================

def importacao_lote():
    """Importa múltiplos dispositivos de um arquivo"""
    print_header("📦 IMPORTAÇÃO EM LOTE")
    
    print("📝 Formatos suportados:")
    print("   1. JSON - Lista de dispositivos")
    print("   2. CSV  - Planilha de dispositivos")
    print()
    
    file_path = input("Caminho do arquivo: ").strip()
    
    if not os.path.exists(file_path):
        print(f"❌ Arquivo não encontrado: {file_path}")
        return
    
    # Detectar formato
    if file_path.endswith('.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                devices_data = json.load(f)
            
            print(f"\n✅ {len(devices_data)} dispositivo(s) encontrado(s)")
            print()
            
            for i, dev_data in enumerate(devices_data):
                print(f"\n📱 Dispositivo {i+1}/{len(devices_data)}")
                print(f"   Nome: {dev_data.get('name', 'Sem nome')}")
                
                device_id = create_device(
                    client_id=dev_data.get('client_id', 1),
                    device_name=dev_data['name'],
                    device_type=dev_data['device_type'],
                    config=dev_data.get('config', {})
                )
                
                if not device_id:
                    print(f"   ⚠️  Falha ao cadastrar!")
            
            print_section("✅ IMPORTAÇÃO CONCLUÍDA")
        
        except Exception as e:
            print(f"❌ Erro ao importar: {e}")
    
    elif file_path.endswith('.csv'):
        print("📋 Importação CSV será implementada em breve!")
    
    else:
        print("❌ Formato não suportado! Use .json ou .csv")

# ============================================================================
# MENU PRINCIPAL
# ============================================================================

def main():
    print_header("🚀 SISTEMA UNIVERSAL DE CADASTRO DE DISPOSITIVOS")
    
    print("📋 MODOS DE CADASTRO:\n")
    print("1. 📝 Cadastro Assistido (Templates prontos)")
    print("2. ⚙️  Cadastro Manual (100% customizado)")
    print("3. 📦 Importação em Lote (JSON/CSV)")
    print("4. 📚 Ver Templates Disponíveis")
    print("5. ❌ Sair")
    print()
    
    choice = input("Escolha uma opção (1-5): ").strip()
    
    if choice == '1':
        cadastro_por_template()
    elif choice == '2':
        cadastro_manual()
    elif choice == '3':
        importacao_lote()
    elif choice == '4':
        print_header("📚 TEMPLATES DISPONÍVEIS")
        for key, template in DEVICE_TEMPLATES.items():
            print(f"\n🔧 {template['name']}")
            print(f"   Protocolo: {template['protocol']}")
            print(f"   Tipo: {template['device_type']}")
            print(f"   Configuração:")
            print(json.dumps(template['config'], indent=6))
    elif choice == '5':
        print("\n👋 Até logo!")
        return
    else:
        print("❌ Opção inválida!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado pelo usuário!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

