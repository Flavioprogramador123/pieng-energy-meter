#!/usr/bin/env python3
"""
Força leitura de medidores - Tenta ler mesmo se offline
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

print("=" * 70)
print("   FORÇA LEITURA - MEDIDORES DE ENERGIA")
print("=" * 70)
print()

load_dotenv()

access_id = os.getenv("TUYA_ACCESS_ID")
access_secret = os.getenv("TUYA_ACCESS_SECRET")
region = os.getenv("TUYA_API_REGION", "us")

if not access_id or not access_secret:
    print("❌ Credenciais não encontradas")
    exit(1)

try:
    import tinytuya
    
    # Medidores identificados
    meters = [
        {"id": "eb12907d3f923984f1wntb", "name": "WIFI dual meter"},
        {"id": "ebbef04296002afe3ecxcg", "name": "Wifi Plug"},
        {"id": "73634132ec94cb8039a6", "name": "Dvr"}
    ]
    
    print("📊 Forçando leitura de 3 medidores...")
    print()
    
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=access_id,
        apiSecret=access_secret
    )
    
    results = []
    
    for meter in meters:
        print(f"📱 {meter['name']} ({meter['id'][:10]}...)")
        
        try:
            # Forçar leitura
            status = cloud.getstatus(meter['id'])
            
            if status and 'result' in status:
                data = status['result']
                
                if len(data) > 0:
                    print(f"   ✅ {len(data)} DADOS REAIS obtidos!")
                    
                    for item in data:
                        code = item.get('code', 'N/A')
                        value = item.get('value', 'N/A')
                        print(f"      • {code}: {value}")
                    
                    # Salvar
                    filename = f"meter_{meter['id']}_FORCED_READ.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(status, f, indent=2, ensure_ascii=False)
                    print(f"      💾 {filename}")
                    
                    results.append({
                        "device_id": meter['id'],
                        "device_name": meter['name'],
                        "success": True,
                        "data_points": len(data),
                        "data": data
                    })
                
                else:
                    print(f"   ⚠️  Resposta vazia (dispositivo realmente offline)")
                    results.append({
                        "device_id": meter['id'],
                        "device_name": meter['name'],
                        "success": False,
                        "reason": "No data"
                    })
            
            else:
                print(f"   ⚠️  API retornou erro: {status}")
                results.append({
                    "device_id": meter['id'],
                    "device_name": meter['name'],
                    "success": False,
                    "reason": "API error",
                    "response": status
                })
        
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            results.append({
                "device_id": meter['id'],
                "device_name": meter['name'],
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # Resumo
    print("=" * 70)
    print("   📊 RESUMO DA LEITURA FORÇADA")
    print("=" * 70)
    print()
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    print(f"✅ Sucesso: {len(successful)}/{len(meters)}")
    print(f"❌ Falhou: {len(failed)}/{len(meters)}")
    print()
    
    if successful:
        print("🎉 Medidores com DADOS REAIS:")
        for r in successful:
            print(f"   • {r['device_name']}: {r['data_points']} dados")
        print()
        print("🎯 ESTES PODEM SER CADASTRADOS NO SISTEMA!")
    
    if failed:
        print("⚠️  Medidores sem dados:")
        for r in failed:
            reason = r.get('reason', r.get('error', 'Unknown'))
            print(f"   • {r['device_name']}: {reason}")
        print()
        print("💡 Ação: Ligar fisicamente e aguardar 5-10 minutos")
    
    # Salvar resumo
    summary_file = f"forced_read_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"💾 Resumo salvo: {summary_file}")
    print()

except ImportError:
    print("❌ tinytuya não instalado")
    exit(1)
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

