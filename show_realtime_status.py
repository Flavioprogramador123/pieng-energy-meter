#!/usr/bin/env python3
"""
Mostra status em tempo real do sistema
APENAS DADOS REAIS do banco de dados!
"""

import sqlite3
from datetime import datetime
from collections import defaultdict

DB_PATH = "data/app.db"

print("=" * 80)
print("   📊 STATUS EM TEMPO REAL - DADOS REAIS DO BANCO")
print("=" * 80)
print()

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total de medições
    cursor.execute("SELECT COUNT(*) FROM measurements")
    total_measurements = cursor.fetchone()[0]
    
    print(f"💾 Total de medições no banco: {total_measurements}")
    print()
    
    if total_measurements == 0:
        print("⚠️  Banco vazio! Aguarde o poller coletar dados...")
        print("   (A cada 30 segundos novas medições são salvas)")
        print()
        conn.close()
        exit(0)
    
    # Últimas medições por dispositivo
    cursor.execute("""
        SELECT 
            d.name,
            d.device_type,
            m.metric,
            m.value,
            m.timestamp
        FROM measurements m
        JOIN devices d ON m.device_id = d.id
        WHERE m.timestamp = (
            SELECT MAX(timestamp)
            FROM measurements m2
            WHERE m2.device_id = m.device_id
            AND m2.metric = m.metric
        )
        ORDER BY d.name, m.metric
    """)
    
    results = cursor.fetchall()
    
    # Agrupar por dispositivo
    devices_data = defaultdict(list)
    
    for row in results:
        device_name, device_type, metric, value, timestamp = row
        devices_data[device_name].append({
            'type': device_type,
            'metric': metric,
            'value': value,
            'timestamp': timestamp
        })
    
    # Mostrar cada dispositivo
    for device_name, metrics in devices_data.items():
        device_type = metrics[0]['type']
        timestamp = metrics[0]['timestamp']
        
        print("=" * 80)
        print(f"   📱 {device_name} ({device_type})")
        print("=" * 80)
        print(f"   🕐 Última atualização: {timestamp}")
        print()
        
        # Organizar métricas
        metrics_dict = {m['metric']: m['value'] for m in metrics}
        
        # Mostrar métricas formatadas
        if 'energy_wh' in metrics_dict:
            energy_kwh = metrics_dict['energy_wh'] / 1000
            print(f"   ⚡ Energia Total: {energy_kwh:.2f} kWh")
        
        if 'voltage' in metrics_dict:
            print(f"   📊 Tensão: {metrics_dict['voltage']:.1f} V")
        
        if 'current' in metrics_dict:
            print(f"   📈 Corrente: {metrics_dict['current']:.3f} A")
        
        if 'power' in metrics_dict:
            print(f"   🔋 Potência: {metrics_dict['power']:.1f} W")
        
        if 'power_factor' in metrics_dict:
            print(f"   📉 Fator de Potência: {metrics_dict['power_factor']:.3f}")
        
        if 'switch_status' in metrics_dict:
            status = "🟢 LIGADO" if metrics_dict['switch_status'] == 1 else "🔴 DESLIGADO"
            print(f"   💡 Status: {status}")
        
        # Custo estimado
        if 'energy_wh' in metrics_dict:
            energy_kwh = metrics_dict['energy_wh'] / 1000
            tariff = 0.65  # R$/kWh
            cost = energy_kwh * tariff
            print()
            print(f"   💰 Custo Estimado: R$ {cost:.2f} (@ R$ {tariff}/kWh)")
        
        print()
    
    # Estatísticas gerais
    print("=" * 80)
    print("   📊 ESTATÍSTICAS GERAIS")
    print("=" * 80)
    print()
    
    # Total por métrica
    cursor.execute("""
        SELECT metric, COUNT(*) as count
        FROM measurements
        GROUP BY metric
        ORDER BY count DESC
    """)
    
    metrics_count = cursor.fetchall()
    
    print("📈 Medições por tipo:")
    for metric, count in metrics_count:
        print(f"   • {metric:20s}: {count:4d} medição(ões)")
    
    print()
    
    # Primeira e última medição
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM measurements")
    first, last = cursor.fetchone()
    
    print(f"🕐 Primeira medição: {first}")
    print(f"🕐 Última medição: {last}")
    
    # Calcular tempo de monitoramento
    if first and last:
        first_dt = datetime.fromisoformat(first)
        last_dt = datetime.fromisoformat(last)
        duration = last_dt - first_dt
        
        print(f"⏱️  Tempo de monitoramento: {duration}")
    
    print()
    
    conn.close()
    
    print("=" * 80)
    print("   ✅ SISTEMA FUNCIONANDO COM DADOS REAIS!")
    print("=" * 80)
    print()
    print("🔄 Atualização automática a cada 30 segundos")
    print("🌐 Dashboard: http://localhost:8000/api/dashboard")
    print()

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

