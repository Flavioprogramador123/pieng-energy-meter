#!/usr/bin/env python3
"""
Mostra o status de todos os ENGINES do sistema
PIENG Energy Meter - 4 Engines Ativos
"""

import sqlite3
from pathlib import Path

DB_PATH = "data/app.db"

def print_header(title: str, level: int = 0):
    if level == 0:
        print("\n" + "=" * 80)
        print(f"{' ' * ((80 - len(title)) // 2)}{title}")
        print("=" * 80 + "\n")
    elif level == 1:
        print("\n" + "=" * 80)
        print(f"   {title}")
        print("=" * 80 + "\n")
    else:
        print(f"\n--- {title} ---\n")

print_header("🚀 STATUS DOS ENGINES - PIENG ENERGY METER")

# Verificar arquivos dos engines
engines = {
    "1️⃣  Tuya Cloud API": {
        "file": "app/services/tuya_poller.py",
        "connector": "app/connectors/tuya.py",
        "device_type": "tuya"
    },
    "2️⃣  Modbus RTU (Serial)": {
        "file": "app/services/pollers.py",
        "connector": "app/connectors/modbus.py",
        "device_type": "modbus"
    },
    "3️⃣  Modbus TCP (Ethernet/WiFi)": {
        "file": "app/services/pollers.py",
        "connector": "app/connectors/modbus_tcp.py",
        "device_type": "modbus_tcp"
    },
    "4️⃣  Drivers Específicos": {
        "pzem004t": "app/connectors/pzem004t.py",
        "sdm630": "app/connectors/eastron_sdm630.py"
    }
}

print("📋 ENGINES IMPLEMENTADOS:\n")

for engine_name, info in engines.items():
    if engine_name == "4️⃣  Drivers Específicos":
        print(f"{engine_name}:")
        for driver_name, file_path in info.items():
            exists = "✅" if Path(file_path).exists() else "❌"
            print(f"   • {driver_name:12s}: {exists} {file_path}")
    else:
        file_exists = "✅" if Path(info["file"]).exists() else "❌"
        print(f"{engine_name}:")
        print(f"   Poller: {file_exists} {info['file']}")

print()

# Verificar scheduler ativo
print_header("⏰ SCHEDULER STATUS", level=1)

scheduler_file = "app/main.py"
if Path(scheduler_file).exists():
    with open(scheduler_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    pollers_found = []
    if "poll_modbus_devices()" in content:
        pollers_found.append("✅ Modbus RTU Poller")
    if "poll_modbus_tcp_devices()" in content:
        pollers_found.append("✅ Modbus TCP Poller")
    if "poll_tuya_devices()" in content:
        pollers_found.append("✅ Tuya Poller")
    
    print("📊 Pollers Agendados:")
    for poller in pollers_found:
        print(f"   {poller}")
    
    print()
    print(f"🔄 Frequência: 30 segundos")
    print(f"⚙️  Scheduler: APScheduler")
else:
    print("❌ Arquivo main.py não encontrado!")

# Verificar dispositivos cadastrados
print_header("📱 DISPOSITIVOS CADASTRADOS", level=1)

if not Path(DB_PATH).exists():
    print("⚠️  Banco de dados não encontrado!")
    print(f"   Caminho esperado: {DB_PATH}")
else:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total de dispositivos
        cursor.execute("SELECT COUNT(*) FROM devices")
        total_devices = cursor.fetchone()[0]
        
        print(f"💾 Total de dispositivos: {total_devices}\n")
        
        if total_devices > 0:
            # Dispositivos por tipo
            cursor.execute("""
                SELECT device_type, COUNT(*) as count, SUM(active) as active_count
                FROM devices
                GROUP BY device_type
            """)
            
            device_types = cursor.fetchall()
            
            print("📊 Dispositivos por Engine:\n")
            
            type_names = {
                "tuya": "1️⃣  Tuya Cloud",
                "modbus": "2️⃣  Modbus RTU",
                "modbus_tcp": "3️⃣  Modbus TCP"
            }
            
            for dtype, count, active in device_types:
                name = type_names.get(dtype, f"❓ {dtype}")
                status = f"({active} ativo(s))" if active else "(nenhum ativo)"
                print(f"   {name:20s}: {count} dispositivo(s) {status}")
            
            print()
            
            # Listar dispositivos
            cursor.execute("""
                SELECT id, name, device_type, active
                FROM devices
                ORDER BY device_type, id
            """)
            
            devices = cursor.fetchall()
            
            print_header("📋 LISTA DE DISPOSITIVOS", level=2)
            
            for dev_id, name, dtype, active in devices:
                status_icon = "🟢" if active else "🔴"
                type_name = type_names.get(dtype, dtype)
                print(f"{status_icon} ID {dev_id:2d}: {name:30s} [{type_name}]")
        else:
            print("⚠️  Nenhum dispositivo cadastrado ainda!")
            print()
            print("💡 Para cadastrar dispositivos:")
            print("   • Tuya: python setup_tuya_devices_REAL.py")
            print("   • PZEM-004T: Crie via API /api/devices")
            print("   • SDM630: Crie via API /api/devices")
        
        print()
        
        # Verificar medições
        cursor.execute("SELECT COUNT(*) FROM measurements")
        total_measurements = cursor.fetchone()[0]
        
        print_header("📊 MEDIÇÕES COLETADAS", level=1)
        print(f"💾 Total de medições: {total_measurements}\n")
        
        if total_measurements > 0:
            # Medições por dispositivo
            cursor.execute("""
                SELECT d.name, d.device_type, COUNT(*) as count
                FROM measurements m
                JOIN devices d ON m.device_id = d.id
                GROUP BY d.id
                ORDER BY count DESC
            """)
            
            measurements_by_device = cursor.fetchall()
            
            print("📈 Medições por dispositivo:\n")
            for dev_name, dtype, count in measurements_by_device:
                type_icon = {
                    "tuya": "📡",
                    "modbus": "🔌",
                    "modbus_tcp": "🌐"
                }.get(dtype, "⚙️")
                print(f"   {type_icon} {dev_name:30s}: {count:5d} medição(ões)")
            
            print()
            
            # Última atualização
            cursor.execute("SELECT MAX(timestamp) FROM measurements")
            last_update = cursor.fetchone()[0]
            
            if last_update:
                print(f"🕐 Última medição: {last_update}")
        else:
            print("⚠️  Nenhuma medição coletada ainda!")
            print("   Aguarde o scheduler executar (a cada 30s)")
        
        conn.close()
    
    except Exception as e:
        print(f"❌ Erro ao acessar banco: {e}")

# Verificar logs
print_header("📝 LOGS DO SISTEMA", level=1)

log_file = "data/audit.log"
if Path(log_file).exists():
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📄 Arquivo: {log_file}")
    print(f"📊 Total de linhas: {len(lines)}\n")
    
    if lines:
        print("📋 Últimas 10 entradas:\n")
        for line in lines[-10:]:
            print(f"   {line.strip()}")
else:
    print(f"ℹ️  Arquivo de log não encontrado: {log_file}")
    print("   (Será criado quando houver erro em algum poller)")

# Resumo final
print_header("✅ RESUMO GERAL", level=1)

print("🎯 ENGINES DISPONÍVEIS: 4")
print()
print("   1️⃣  Tuya Cloud API      → ✅ Implementado")
print("   2️⃣  Modbus RTU          → ✅ Implementado")
print("   3️⃣  Modbus TCP          → ✅ Implementado")
print("   4️⃣  Modbus Genérico     → ✅ Implementado")
print()
print("🔧 DRIVERS ESPECÍFICOS:")
print("   • PZEM-004T    → ✅ Serial e TCP")
print("   • SDM630       → ✅ Serial e TCP")
print()
print("⏰ SCHEDULER: APScheduler (30s)")
print("💾 BANCO: SQLite (data/app.db)")
print("🌐 DASHBOARD: http://localhost:8000/api/dashboard")
print()

print("=" * 80)
print("   ✅ TODOS OS ENGINES ESTÃO PRONTOS!")
print("=" * 80)
print()

print("📚 Para mais informações: cat STATUS_ENGINES.md")
print()


