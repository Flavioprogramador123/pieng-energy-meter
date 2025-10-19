#!/usr/bin/env python3
"""
Script para testar e extrair informações dos dispositivos Tuya
Autor: PIENG Energy
Data: 18/10/2025
"""

import tinytuya
import json
from datetime import datetime

print("=" * 60)
print("   PIENG - Teste de Dispositivos Tuya")
print("=" * 60)
print()

# ===== CONFIGURAÇÃO =====
# Substitua com suas credenciais do Tuya IoT Platform
ACCESS_ID = input("Digite seu Tuya Access ID: ").strip()
ACCESS_SECRET = input("Digite seu Tuya Access Secret: ").strip()

# Região da API (us, eu, cn, in)
print("\nRegiões disponíveis:")
print("  us - Americas")
print("  eu - Europa")
print("  cn - China")
print("  in - Índia")
API_REGION = input("Digite a região (padrão: us): ").strip() or "us"

print("\n" + "=" * 60)
print("Conectando ao Tuya Cloud...")
print("=" * 60)

try:
    # Conectar ao Tuya Cloud
    cloud = tinytuya.Cloud(
        apiRegion=API_REGION,
        apiKey=ACCESS_ID,
        apiSecret=ACCESS_SECRET
    )
    
    # Listar dispositivos
    print("\n📱 Buscando dispositivos...")
    devices = cloud.getdevices()
    
    if not devices:
        print("\n⚠️  Nenhum dispositivo encontrado!")
        print("\nVerifique:")
        print("  1. Credenciais corretas")
        print("  2. Dispositivos linkados na plataforma Tuya IoT")
        print("  3. Região da API correta")
        exit(1)
    
    print(f"\n✅ {len(devices)} dispositivo(s) encontrado(s)!\n")
    
    # Salvar em arquivo JSON
    output_file = f"tuya_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    devices_info = []
    
    for idx, device in enumerate(devices, 1):
        print("-" * 60)
        print(f"Dispositivo #{idx}: {device.get('name', 'Sem nome')}")
        print("-" * 60)
        print(f"  ID: {device['id']}")
        print(f"  Product: {device.get('product_name', 'N/A')}")
        print(f"  Category: {device.get('category', 'N/A')}")
        print(f"  Online: {'Sim' if device.get('online') else 'Não'}")
        print(f"  IP: {device.get('ip', 'N/A')}")
        print(f"  Local Key: {device.get('local_key', 'N/A')}")
        
        # Buscar status atual
        try:
            status = cloud.getstatus(device['id'])
            print(f"\n  Status atual:")
            
            metrics = {}
            for dp in status:
                code = dp.get('code', 'unknown')
                value = dp.get('value', 'N/A')
                print(f"    - {code}: {value}")
                metrics[code] = value
            
            device['current_status'] = metrics
            device['last_check'] = datetime.now().isoformat()
            
            # Converter para formato PIENG
            pieng_metrics = {}
            if 'cur_voltage' in metrics or 'voltage' in metrics:
                voltage_key = 'cur_voltage' if 'cur_voltage' in metrics else 'voltage'
                pieng_metrics['voltage'] = float(metrics[voltage_key]) / 10
            
            if 'cur_current' in metrics or 'current' in metrics:
                current_key = 'cur_current' if 'cur_current' in metrics else 'current'
                pieng_metrics['current'] = float(metrics[current_key]) / 1000
            
            if 'cur_power' in metrics or 'power' in metrics:
                power_key = 'cur_power' if 'cur_power' in metrics else 'power'
                pieng_metrics['power'] = float(metrics[power_key]) / 10
            
            if 'total_forward_energy' in metrics or 'forward_energy_total' in metrics:
                energy_key = 'total_forward_energy' if 'total_forward_energy' in metrics else 'forward_energy_total'
                pieng_metrics['energy_kwh'] = float(metrics[energy_key]) / 100
            
            if pieng_metrics:
                print(f"\n  Métricas PIENG (convertidas):")
                for key, value in pieng_metrics.items():
                    unit = {'voltage': 'V', 'current': 'A', 'power': 'W', 'energy_kwh': 'kWh'}.get(key, '')
                    print(f"    - {key}: {value:.2f} {unit}")
                
                device['pieng_metrics'] = pieng_metrics
            
        except Exception as e:
            print(f"\n  ⚠️  Erro ao buscar status: {e}")
        
        devices_info.append(device)
        print()
    
    # Salvar em arquivo
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'region': API_REGION,
            'total_devices': len(devices_info),
            'devices': devices_info
        }, f, indent=2, ensure_ascii=False)
    
    print("=" * 60)
    print(f"✅ Informações salvas em: {output_file}")
    print("=" * 60)
    
    # Gerar código para .env
    print("\n📝 Adicione no seu arquivo .env:")
    print("-" * 60)
    print(f"TUYA_API_REGION={API_REGION}")
    print(f"TUYA_ACCESS_ID={ACCESS_ID}")
    print(f"TUYA_ACCESS_SECRET={ACCESS_SECRET}")
    print()
    
    # Gerar código para cadastrar dispositivos
    print("📝 Código SQL para cadastrar dispositivos:")
    print("-" * 60)
    for idx, device in enumerate(devices_info, 1):
        device_name = device.get('name', f'Tuya Device {idx}')
        device_id = device['id']
        local_key = device.get('local_key', '')
        
        print(f"""
-- Dispositivo {idx}: {device_name}
INSERT INTO devices (client_id, name, device_type, active, config)
VALUES (
    1,  -- Altere para o ID do seu cliente
    '{device_name}',
    'tuya',
    true,
    '{{"device_id": "{device_id}", "local_key": "{local_key}"}}'::jsonb
);
""")
    
    print("\n✅ Teste concluído com sucesso!")
    print("\nPróximos passos:")
    print("  1. Copie as credenciais para o .env")
    print("  2. Execute os SQLs acima no PostgreSQL")
    print("  3. Configure o poller no app/services/pollers.py")
    print("  4. Reinicie o backend")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    print("\nVerifique:")
    print("  1. Biblioteca instalada: pip install tinytuya")
    print("  2. Credenciais corretas")
    print("  3. Conexão com internet")
    exit(1)

