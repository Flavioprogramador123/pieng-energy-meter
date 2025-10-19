#!/usr/bin/env python3
"""
Visualizador de Dados Tuya - Terminal
Interpreta e mostra dados REAIS dos dispositivos
"""

import json
from datetime import datetime
from pathlib import Path

print("=" * 80)
print("   📊 DADOS TUYA REAIS - VISUALIZAÇÃO COMPLETA")
print("=" * 80)
print()

# Função para interpretar dados
def interpret_value(code, value):
    """Interpreta e formata valores Tuya"""
    
    if code == "switch_1":
        return "🟢 LIGADO" if value else "🔴 DESLIGADO"
    
    elif code == "add_ele":
        return f"{value} kWh (Energia acumulada)"
    
    elif code == "cur_current":
        return f"{value / 1000:.3f} A (Corrente atual em Amperes)"
    
    elif code == "cur_power":
        return f"{value / 10:.1f} W (Potência atual em Watts)"
    
    elif code == "cur_voltage":
        return f"{value / 10:.1f} V (Tensão atual em Volts)"
    
    elif code == "countdown_1":
        return f"{value} segundos (Temporizador)"
    
    elif code == "relay_status":
        status_map = {
            "last": "Mantém último estado",
            "power_on": "Liga ao energizar",
            "power_off": "Desliga ao energizar"
        }
        return status_map.get(value, value)
    
    elif code == "fault":
        return "✅ Sem falhas" if value == 0 else f"⚠️ Código de falha: {value}"
    
    elif "_coe" in code:
        return f"{value} (Coeficiente de calibração)"
    
    else:
        return str(value)

# Arquivos JSON
files = [
    {
        "file": "meter_ebbef04296002afe3ecxcg_FORCED_READ.json",
        "name": "Wifi Plug - Medidor de Energia",
        "icon": "🔌",
        "type": "Medidor"
    },
    {
        "file": "meter_73634132ec94cb8039a6_FORCED_READ.json",
        "name": "Dvr - Interruptor",
        "icon": "💡",
        "type": "Interruptor"
    }
]

for device in files:
    file_path = Path(device["file"])
    
    if not file_path.exists():
        print(f"⚠️  Arquivo não encontrado: {device['file']}")
        print()
        continue
    
    print("=" * 80)
    print(f"   {device['icon']} {device['name']}")
    print("=" * 80)
    print()
    
    # Ler JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Mostrar metadados
    print("📝 Metadados da Resposta:")
    print(f"   Status: {'✅ Sucesso' if data.get('success') else '❌ Falha'}")
    
    # Converter timestamp (milissegundos para datetime)
    if 't' in data:
        timestamp_ms = data['t']
        timestamp_s = timestamp_ms / 1000
        dt = datetime.fromtimestamp(timestamp_s)
        print(f"   Timestamp: {dt.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"   Transaction ID: {data.get('tid', 'N/A')[:20]}...")
    
    print()
    print("📊 Dados do Dispositivo:")
    print()
    
    # Mostrar dados
    if 'result' in data:
        result = data['result']
        
        # Separar em categorias
        main_data = []
        config_data = []
        
        for item in result:
            code = item.get('code', 'N/A')
            value = item.get('value', 'N/A')
            
            if '_coe' in code or 'time' in code:
                config_data.append((code, value))
            else:
                main_data.append((code, value))
        
        # Mostrar dados principais
        print("   🔹 Medições Principais:")
        for code, value in main_data:
            interpreted = interpret_value(code, value)
            print(f"      • {code:20s}: {interpreted}")
        
        # Mostrar configurações/coeficientes
        if config_data:
            print()
            print("   ⚙️  Configurações & Coeficientes:")
            for code, value in config_data:
                interpreted = interpret_value(code, value)
                print(f"      • {code:20s}: {interpreted}")
    
    print()
    print("-" * 80)
    print()

# Resumo geral
print("=" * 80)
print("   📈 RESUMO DA AUDITORIA")
print("=" * 80)
print()

# Calcular métricas
try:
    with open("meter_ebbef04296002afe3ecxcg_FORCED_READ.json", 'r') as f:
        wifi_plug = json.load(f)
    
    result = wifi_plug['result']
    data_dict = {item['code']: item['value'] for item in result}
    
    energia = data_dict.get('add_ele', 0)
    tensao = data_dict.get('cur_voltage', 0) / 10
    corrente = data_dict.get('cur_current', 0) / 1000
    potencia = data_dict.get('cur_power', 0) / 10
    
    print("🔌 Wifi Plug (Medidor):")
    print(f"   ⚡ Energia Total: {energia} kWh")
    print(f"   📊 Tensão: {tensao:.1f} V")
    print(f"   📈 Corrente: {corrente:.3f} A")
    print(f"   🔋 Potência: {potencia:.1f} W")
    print()
    
    # Validações
    print("✅ Validações:")
    
    if 200 <= tensao <= 240:
        print(f"   ✅ Tensão OK (dentro de 200-240V)")
    else:
        print(f"   ⚠️  Tensão fora do normal!")
    
    if potencia == 0:
        print(f"   ℹ️  Sem carga conectada (0W)")
    else:
        print(f"   ✅ Carga ativa: {potencia:.1f}W")
    
    # Custo estimado
    tarifa = 0.65  # R$/kWh (média)
    custo = energia * tarifa
    print()
    print(f"💰 Custo Estimado (R$ {tarifa}/kWh): R$ {custo:.2f}")
    print()

except Exception as e:
    print(f"⚠️  Erro ao processar resumo: {e}")
    print()

print("=" * 80)
print("   ✅ VISUALIZAÇÃO CONCLUÍDA")
print("=" * 80)
print()
print("🔍 Para comparar com a plataforma Tuya:")
print("   https://us.platform.tuya.com/cloud/device/list")
print()

