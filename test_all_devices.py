#!/usr/bin/env python3
"""
Script para testar TODOS os dispositivos do laboratório PIENG
- Eastron SDM630 via Elfin EW11 (Modbus TCP)
- 2x Tuya Smart Meters (WiFi/Cloud)
- 2x PZEM-004T (USB/Serial)
- USR-G771 LTE Gateway

Autor: PIENG Energy
Data: 18/10/2025
"""

import sys
import json
from datetime import datetime
from typing import Dict, Any, List

# ===== CONFIGURAÇÃO =====
CONFIG = {
    # SDM630 via Elfin EW11
    "sdm630": {
        "enabled": True,
        "host": "192.168.1.109",  # IP do Elfin EW11
        "port": 8899,
        "slave_id": 1,
        "timeout": 3.0
    },
    
    # Tuya Smart Meters (credenciais vêm do .env)
    "tuya": {
        "enabled": True,
        "region": "us",  # us, eu, cn, in
    },
    
    # PZEM-004T (USB/Serial)
    "pzem": {
        "enabled": True,
        "devices": [
            {"port": "COM3", "slave_id": 1, "name": "PZEM-004T #1"},
            {"port": "COM4", "slave_id": 1, "name": "PZEM-004T #2"}
        ],
        "baudrate": 9600,
        "timeout": 0.5
    },
    
    # USR-G771 LTE Gateway
    "usr_g771": {
        "enabled": False,  # Ativar quando configurado
        "host": "192.168.1.200",
        "port": 8899
    }
}

# ===== FUNÇÕES DE TESTE =====

def print_header(title: str):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 70)
    print(f"   {title}")
    print("=" * 70)

def print_device(name: str, status: str, details: Dict[str, Any] = None):
    """Imprime informações do dispositivo"""
    status_icon = "✅" if status == "OK" else "❌" if status == "ERRO" else "⚠️"
    print(f"\n{status_icon} {name}")
    print("-" * 70)
    if details:
        for key, value in details.items():
            print(f"  {key}: {value}")

def test_sdm630() -> Dict[str, Any]:
    """Testa Eastron SDM630 via Elfin EW11 (Modbus TCP)"""
    print_header("Testando SDM630 via Elfin EW11 (Modbus TCP)")
    
    if not CONFIG["sdm630"]["enabled"]:
        print("⚠️  SDM630 desabilitado na configuração")
        return {"status": "SKIP"}
    
    try:
        from pymodbus.client import ModbusTcpClient
        
        cfg = CONFIG["sdm630"]
        print(f"Conectando em {cfg['host']}:{cfg['port']} (slave_id={cfg['slave_id']})...")
        
        client = ModbusTcpClient(
            host=cfg['host'],
            port=cfg['port'],
            timeout=cfg['timeout']
        )
        
        if not client.connect():
            return {"status": "ERRO", "message": "Não foi possível conectar"}
        
        # Ler tensões (3 fases)
        result = client.read_input_registers(address=0x0000, count=6, slave=cfg['slave_id'])
        
        if result.isError():
            client.close()
            return {"status": "ERRO", "message": str(result)}
        
        # Converter para float32
        import struct
        def regs_to_float(reg_high: int, reg_low: int) -> float:
            combined = (reg_high << 16) | reg_low
            return struct.unpack('>f', struct.pack('>I', combined))[0]
        
        regs = result.registers
        v1 = regs_to_float(regs[0], regs[1])
        v2 = regs_to_float(regs[2], regs[3])
        v3 = regs_to_float(regs[4], regs[5])
        
        # Ler correntes
        result = client.read_input_registers(address=0x0006, count=6, slave=cfg['slave_id'])
        regs = result.registers
        i1 = regs_to_float(regs[0], regs[1])
        i2 = regs_to_float(regs[2], regs[3])
        i3 = regs_to_float(regs[4], regs[5])
        
        # Ler potência total
        result = client.read_input_registers(address=0x0034, count=2, slave=cfg['slave_id'])
        regs = result.registers
        power_total = regs_to_float(regs[0], regs[1])
        
        # Ler energia
        result = client.read_input_registers(address=0x0048, count=2, slave=cfg['slave_id'])
        regs = result.registers
        energy_kwh = regs_to_float(regs[0], regs[1])
        
        client.close()
        
        metrics = {
            "Tensão L1": f"{v1:.2f} V",
            "Tensão L2": f"{v2:.2f} V",
            "Tensão L3": f"{v3:.2f} V",
            "Corrente L1": f"{i1:.3f} A",
            "Corrente L2": f"{i2:.3f} A",
            "Corrente L3": f"{i3:.3f} A",
            "Potência Total": f"{power_total:.2f} W",
            "Energia": f"{energy_kwh:.2f} kWh"
        }
        
        print_device("Eastron SDM630-MCT", "OK", metrics)
        
        return {
            "status": "OK",
            "device_type": "modbus_tcp",
            "driver": "sdm630",
            "metrics": metrics,
            "raw_values": {
                "voltage_l1": v1,
                "voltage_l2": v2,
                "voltage_l3": v3,
                "current_l1": i1,
                "current_l2": i2,
                "current_l3": i3,
                "power_total": power_total,
                "energy_kwh": energy_kwh
            }
        }
        
    except ImportError:
        return {"status": "ERRO", "message": "pymodbus não instalado: pip install pymodbus"}
    except Exception as e:
        return {"status": "ERRO", "message": str(e)}

def test_tuya() -> Dict[str, Any]:
    """Testa Tuya Smart Meters"""
    print_header("Testando Tuya Smart Meters (Cloud API)")
    
    if not CONFIG["tuya"]["enabled"]:
        print("⚠️  Tuya desabilitado na configuração")
        return {"status": "SKIP"}
    
    try:
        import tinytuya
        import os
        from dotenv import load_dotenv
        
        # Carregar variáveis do .env
        load_dotenv()
        
        # Buscar credenciais do .env (NUNCA solicitar via input!)
        access_id = os.getenv("TUYA_ACCESS_ID")
        access_secret = os.getenv("TUYA_ACCESS_SECRET")
        region = os.getenv("TUYA_API_REGION", CONFIG["tuya"]["region"])
        
        if not access_id or not access_secret:
            print("⚠️  Credenciais Tuya não encontradas!")
            print("\n📝 Configure no arquivo .env:")
            print("   TUYA_ACCESS_ID=sua_access_id_aqui")
            print("   TUYA_ACCESS_SECRET=seu_access_secret_aqui")
            print("   TUYA_API_REGION=us")
            print("\n⚠️  NUNCA exponha essas chaves em código ou commits Git!")
            return {"status": "SKIP", "message": "Credenciais não configuradas no .env"}
        
        print(f"Conectando ao Tuya Cloud (região: {region})...")
        
        cloud = tinytuya.Cloud(
            apiRegion=region,
            apiKey=access_id,
            apiSecret=access_secret
        )
        
        # Listar dispositivos
        devices = cloud.getdevices()
        
        if not devices:
            return {"status": "ERRO", "message": "Nenhum dispositivo encontrado. Verifique: 1) Credenciais, 2) Dispositivos linkados na plataforma"}
        
        results = []
        for device in devices:
            device_name = device.get('name', 'Sem nome')
            device_id = device['id']
            
            try:
                # Buscar status
                status = cloud.getstatus(device_id)
                
                metrics = {}
                for dp in status:
                    code = dp.get('code', 'unknown')
                    value = dp.get('value')
                    
                    # Converter para formato padrão
                    if code in ['cur_voltage', 'voltage']:
                        metrics['Tensão'] = f"{float(value)/10:.2f} V"
                        metrics['voltage'] = float(value)/10
                    elif code in ['cur_current', 'current']:
                        metrics['Corrente'] = f"{float(value)/1000:.3f} A"
                        metrics['current'] = float(value)/1000
                    elif code in ['cur_power', 'power']:
                        metrics['Potência'] = f"{float(value)/10:.2f} W"
                        metrics['power'] = float(value)/10
                    elif code in ['total_forward_energy', 'forward_energy_total']:
                        metrics['Energia'] = f"{float(value)/100:.2f} kWh"
                        metrics['energy_kwh'] = float(value)/100
                
                print_device(device_name, "OK", {k: v for k, v in metrics.items() if isinstance(v, str)})
                
                results.append({
                    "name": device_name,
                    "device_id": device_id,
                    "status": "OK",
                    "metrics": metrics
                })
                
            except Exception as e:
                print_device(device_name, "ERRO", {"Erro": str(e)})
                results.append({
                    "name": device_name,
                    "device_id": device_id,
                    "status": "ERRO",
                    "error": str(e)
                })
        
        return {
            "status": "OK",
            "device_type": "tuya",
            "total_devices": len(devices),
            "devices": results
        }
        
    except ImportError:
        return {"status": "ERRO", "message": "tinytuya não instalado: pip install tinytuya"}
    except Exception as e:
        return {"status": "ERRO", "message": str(e)}

def test_pzem() -> Dict[str, Any]:
    """Testa PZEM-004T (USB/Serial)"""
    print_header("Testando PZEM-004T (USB/Serial)")
    
    if not CONFIG["pzem"]["enabled"]:
        print("⚠️  PZEM desabilitado na configuração")
        return {"status": "SKIP"}
    
    try:
        import minimalmodbus
        import serial.tools.list_ports
        
        # Listar portas disponíveis
        print("\nPortas COM disponíveis:")
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            print(f"  - {port.device}: {port.description}")
        
        if not ports:
            return {"status": "ERRO", "message": "Nenhuma porta COM encontrada"}
        
        cfg = CONFIG["pzem"]
        results = []
        
        for pzem_cfg in cfg["devices"]:
            port = pzem_cfg["port"]
            slave_id = pzem_cfg["slave_id"]
            name = pzem_cfg["name"]
            
            print(f"\nTestando {name} em {port}...")
            
            try:
                instrument = minimalmodbus.Instrument(port, slave_id)
                instrument.serial.baudrate = cfg["baudrate"]
                instrument.serial.timeout = cfg["timeout"]
                
                # Ler métricas PZEM-004T
                voltage = instrument.read_register(0x0000, 1, 4)
                current = instrument.read_register(0x0001, 3, 4)
                power = instrument.read_register(0x0003, 1, 4)
                energy = instrument.read_long(0x0005, 4)
                
                metrics = {
                    "Tensão": f"{voltage:.2f} V",
                    "Corrente": f"{current:.3f} A",
                    "Potência": f"{power:.2f} W",
                    "Energia": f"{energy/1000:.2f} kWh"
                }
                
                print_device(name, "OK", metrics)
                
                results.append({
                    "name": name,
                    "port": port,
                    "status": "OK",
                    "metrics": metrics,
                    "raw_values": {
                        "voltage": voltage,
                        "current": current,
                        "power": power,
                        "energy_kwh": energy/1000
                    }
                })
                
            except Exception as e:
                print_device(name, "ERRO", {"Erro": str(e)})
                results.append({
                    "name": name,
                    "port": port,
                    "status": "ERRO",
                    "error": str(e)
                })
        
        return {
            "status": "OK",
            "device_type": "modbus_rtu",
            "driver": "pzem004t",
            "total_devices": len(cfg["devices"]),
            "devices": results
        }
        
    except ImportError:
        return {"status": "ERRO", "message": "minimalmodbus não instalado: pip install minimalmodbus pyserial"}
    except Exception as e:
        return {"status": "ERRO", "message": str(e)}

def test_usr_g771() -> Dict[str, Any]:
    """Testa USR-G771 LTE Gateway"""
    print_header("Testando USR-G771 LTE Gateway")
    
    if not CONFIG["usr_g771"]["enabled"]:
        print("⚠️  USR-G771 não configurado ainda")
        print("\nPara configurar:")
        print("1. Conectar USR-G771 via USB")
        print("2. Configurar APN da operadora")
        print("3. Configurar modo TCP Client")
        print("4. Habilitar em CONFIG['usr_g771']['enabled'] = True")
        return {"status": "SKIP"}
    
    try:
        import socket
        
        cfg = CONFIG["usr_g771"]
        print(f"Testando conexão com {cfg['host']}:{cfg['port']}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        result = sock.connect_ex((cfg['host'], cfg['port']))
        sock.close()
        
        if result == 0:
            print_device("USR-G771 LTE Gateway", "OK", {
                "Host": cfg['host'],
                "Porta": cfg['port'],
                "Status": "Acessível"
            })
            return {"status": "OK", "device_type": "lte_gateway"}
        else:
            return {"status": "ERRO", "message": f"Não foi possível conectar (erro {result})"}
            
    except Exception as e:
        return {"status": "ERRO", "message": str(e)}

# ===== MAIN =====

def main():
    print("=" * 70)
    print("   PIENG Energy - Teste de Todos os Dispositivos")
    print("=" * 70)
    print(f"\nData: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    all_results = {}
    
    # Testar cada tipo de dispositivo
    all_results["sdm630"] = test_sdm630()
    all_results["tuya"] = test_tuya()
    all_results["pzem"] = test_pzem()
    all_results["usr_g771"] = test_usr_g771()
    
    # Resumo final
    print_header("Resumo dos Testes")
    
    total_ok = sum(1 for r in all_results.values() if r.get("status") == "OK")
    total_error = sum(1 for r in all_results.values() if r.get("status") == "ERRO")
    total_skip = sum(1 for r in all_results.values() if r.get("status") == "SKIP")
    
    print(f"\n✅ Sucesso: {total_ok}")
    print(f"❌ Erro: {total_error}")
    print(f"⚠️  Ignorado: {total_skip}")
    
    # Salvar resultados em JSON
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_ok': total_ok,
                'total_error': total_error,
                'total_skip': total_skip
            },
            'results': all_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Resultados salvos em: {output_file}")
    
    # SQL para cadastrar dispositivos
    if total_ok > 0:
        print_header("SQL para Cadastrar Dispositivos")
        
        client_id = input("\nDigite o ID do cliente (ou Enter para 1): ").strip() or "1"
        
        print("\n-- Copie e cole no PostgreSQL:")
        print("-" * 70)
        
        device_num = 1
        
        # SDM630
        if all_results["sdm630"].get("status") == "OK":
            print(f"""
-- Dispositivo {device_num}: Eastron SDM630 via Elfin EW11
INSERT INTO devices (client_id, name, device_type, active, config)
VALUES (
    {client_id},
    'SDM630 - Entrada Principal',
    'modbus_tcp',
    true,
    '{{"host": "{CONFIG["sdm630"]["host"]}", "port": {CONFIG["sdm630"]["port"]}, "slave_id": {CONFIG["sdm630"]["slave_id"]}, "driver": "sdm630"}}'::jsonb
);
""")
            device_num += 1
        
        # Tuya
        if all_results["tuya"].get("status") == "OK":
            for device in all_results["tuya"].get("devices", []):
                if device.get("status") == "OK":
                    print(f"""
-- Dispositivo {device_num}: {device['name']}
INSERT INTO devices (client_id, name, device_type, active, config)
VALUES (
    {client_id},
    '{device['name']}',
    'tuya',
    true,
    '{{"device_id": "{device['device_id']}"}}'::jsonb
);
""")
                    device_num += 1
        
        # PZEM
        if all_results["pzem"].get("status") == "OK":
            for device in all_results["pzem"].get("devices", []):
                if device.get("status") == "OK":
                    print(f"""
-- Dispositivo {device_num}: {device['name']}
INSERT INTO devices (client_id, name, device_type, active, config)
VALUES (
    {client_id},
    '{device['name']}',
    'modbus',
    true,
    '{{"port": "{device['port']}", "slave_id": 1, "baudrate": 9600, "driver": "pzem004t"}}'::jsonb
);
""")
                    device_num += 1
    
    print("\n" + "=" * 70)
    print("   ✅ Teste concluído!")
    print("=" * 70)
    print("\nPróximos passos:")
    print("  1. Copiar SQLs acima e executar no PostgreSQL")
    print("  2. Configurar pollers no backend")
    print("  3. Iniciar coleta automática")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()

