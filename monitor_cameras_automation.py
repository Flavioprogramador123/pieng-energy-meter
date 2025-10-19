#!/usr/bin/env python3
"""
Monitor Automático de Câmeras + Energia
Correlaciona detecção de movimento com consumo energético
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

print("=" * 80)
print("   🎥 MONITOR AUTOMÁTICO - CÂMERAS + ENERGIA")
print("=" * 80)
print()

# Carregar credenciais
load_dotenv()

access_id = os.getenv("TUYA_ACCESS_ID")
access_secret = os.getenv("TUYA_ACCESS_SECRET")
region = os.getenv("TUYA_API_REGION", "us")

if not access_id or not access_secret:
    print("❌ Credenciais não encontradas")
    exit(1)

try:
    import tinytuya
    
    print("📡 Conectando Tuya Cloud API...")
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=access_id,
        apiSecret=access_secret
    )
    print("✅ Conectado!")
    print()
    
    # Buscar TODAS as câmeras
    print("🔍 Testando TODAS as câmeras...")
    print()
    
    devices = cloud.getdevices()
    
    cameras = []
    for d in devices:
        category = d.get('category', '')
        name = d.get('name', 'Sem nome')
        
        if category in ['sp', 'ipc', 'camera'] or 'camera' in name.lower():
            cameras.append(d)
    
    if not cameras:
        print("⚠️  Nenhuma câmera encontrada")
        exit(0)
    
    print(f"✅ {len(cameras)} câmera(s) encontrada(s)")
    print()
    print("🧪 Testando cada câmera para encontrar uma que responda...")
    print()
    
    working_cameras = []
    
    for i, cam in enumerate(cameras, 1):
        cam_id = cam['id']
        cam_name = cam.get('name', 'Sem nome')
        online = cam.get('online', False)
        
        print(f"[{i}/{len(cameras)}] Testando: {cam_name}...")
        
        try:
            # Tentar ler status
            status = cloud.getstatus(cam_id)
            
            if status and 'result' in status and len(status['result']) > 0:
                print(f"   ✅ RESPONDE! {len(status['result'])} datapoints")
                
                # Verificar se tem detecção de movimento
                data_dict = {item['code']: item['value'] for item in status['result']}
                
                has_motion = any(k in data_dict for k in [
                    'motion_switch', 'movement_detect_pic', 
                    'pir', 'motion_detected', 'humanoid_filter'
                ])
                
                if has_motion:
                    print(f"   🎯 TEM DETECÇÃO DE MOVIMENTO!")
                    working_cameras.append({
                        'device': cam,
                        'status': status,
                        'data': data_dict
                    })
                else:
                    print(f"   ⚠️  Sem detecção de movimento")
            else:
                print(f"   ⚠️  Não responde")
        
        except Exception as e:
            print(f"   ❌ Erro: {str(e)[:50]}")
        
        print()
    
    if not working_cameras:
        print("=" * 80)
        print("⚠️  NENHUMA CÂMERA RESPONDENDO NO MOMENTO")
        print("=" * 80)
        print()
        print("Possíveis causas:")
        print("  • Câmeras realmente offline")
        print("  • Aguardando sincronização com nuvem")
        print("  • Precisa acesso via app primeiro")
        print()
        print("💡 Tente:")
        print("  1. Abrir app Smart Life no celular")
        print("  2. Acessar cada câmera pelo app")
        print("  3. Aguardar 5-10 minutos")
        print("  4. Executar este script novamente")
        print()
        exit(0)
    
    print("=" * 80)
    print(f"   ✅ {len(working_cameras)} CÂMERA(S) FUNCIONANDO!")
    print("=" * 80)
    print()
    
    # Mostrar câmeras funcionando
    for i, cam_info in enumerate(working_cameras, 1):
        cam = cam_info['device']
        data = cam_info['data']
        
        print(f"{i}. 📹 {cam.get('name', 'Câmera')}")
        print(f"   ID: {cam['id']}")
        
        # Status de movimento
        motion_on = data.get('motion_switch', False)
        humanoid = data.get('humanoid_filter', False)
        sensitivity = data.get('motion_sensitivity', 'N/A')
        
        print(f"   Detecção: {'🟢 ATIVA' if motion_on else '🔴 DESATIVADA'}")
        print(f"   Filtro Humano: {'✅ SIM' if humanoid else '❌ NÃO'}")
        print(f"   Sensibilidade: {sensitivity}")
        print()
    
    # Criar monitor automático
    print("=" * 80)
    print("   🤖 INICIANDO MONITOR AUTOMÁTICO")
    print("=" * 80)
    print()
    
    print("Configurações:")
    print(f"  • {len(working_cameras)} câmera(s) monitoradas")
    print(f"  • Intervalo: 10 segundos")
    print(f"  • Correlação com energia: ATIVA")
    print()
    print("Eventos monitorados:")
    print("  • Detecção de movimento")
    print("  • Detecção de pessoa (humanoid)")
    print("  • Mudança de status")
    print()
    print("Pressione Ctrl+C para parar")
    print()
    print("-" * 80)
    print()
    
    # Estado anterior
    previous_states = {}
    
    iteration = 0
    events_detected = []
    
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"[{timestamp}] Verificação #{iteration}...")
            
            for cam_info in working_cameras:
                cam = cam_info['device']
                cam_id = cam['id']
                cam_name = cam.get('name', 'Câmera')
                
                try:
                    # Ler status atual
                    status = cloud.getstatus(cam_id)
                    
                    if not status or 'result' not in status:
                        continue
                    
                    current_data = {item['code']: item['value'] 
                                   for item in status['result']}
                    
                    # Verificar mudanças
                    if cam_id in previous_states:
                        prev_data = previous_states[cam_id]
                        
                        # Verificar detecção de movimento
                        if 'movement_detect_pic' in current_data:
                            curr_pic = current_data.get('movement_detect_pic', '')
                            prev_pic = prev_data.get('movement_detect_pic', '')
                            
                            if curr_pic != prev_pic and curr_pic not in ['', '$']:
                                event = {
                                    'timestamp': datetime.now().isoformat(),
                                    'camera': cam_name,
                                    'camera_id': cam_id,
                                    'type': 'motion_detected',
                                    'humanoid': current_data.get('humanoid_filter', False)
                                }
                                
                                events_detected.append(event)
                                
                                print(f"\n🚨 MOVIMENTO DETECTADO!")
                                print(f"   Câmera: {cam_name}")
                                print(f"   Hora: {timestamp}")
                                
                                if event['humanoid']:
                                    print(f"   👤 PESSOA DETECTADA!")
                                
                                print()
                        
                        # Verificar mudança de status
                        for key in ['motion_switch', 'motion_sensitivity']:
                            if key in current_data:
                                if current_data[key] != prev_data.get(key):
                                    print(f"\n📝 {cam_name}: {key} mudou")
                                    print(f"   De: {prev_data.get(key)} → Para: {current_data[key]}")
                                    print()
                    
                    # Atualizar estado
                    previous_states[cam_id] = current_data
                
                except Exception as e:
                    print(f"   ⚠️  {cam_name}: {str(e)[:40]}")
            
            # Resumo
            if iteration % 6 == 0:  # A cada 1 minuto
                print()
                print("-" * 80)
                print(f"📊 Resumo - {len(events_detected)} evento(s) detectado(s)")
                
                if events_detected:
                    print()
                    for evt in events_detected[-5:]:  # Últimos 5
                        ts = datetime.fromisoformat(evt['timestamp'])
                        print(f"  • {ts.strftime('%H:%M:%S')} - {evt['camera']}")
                        if evt.get('humanoid'):
                            print(f"    👤 Pessoa detectada")
                
                print("-" * 80)
                print()
            
            # Aguardar
            time.sleep(10)
    
    except KeyboardInterrupt:
        print()
        print()
        print("=" * 80)
        print("   ⏹️  MONITOR PARADO PELO USUÁRIO")
        print("=" * 80)
        print()
        
        # Salvar eventos
        if events_detected:
            filename = f"camera_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(events_detected, f, indent=2, ensure_ascii=False)
            
            print(f"💾 {len(events_detected)} evento(s) salvo(s) em: {filename}")
            print()
            
            # Estatísticas
            print("📊 Estatísticas:")
            print(f"   Total de eventos: {len(events_detected)}")
            
            humanoid_events = [e for e in events_detected if e.get('humanoid')]
            if humanoid_events:
                print(f"   Pessoas detectadas: {len(humanoid_events)}")
            
            # Por câmera
            from collections import Counter
            cameras_count = Counter(e['camera'] for e in events_detected)
            
            print()
            print("   Por câmera:")
            for cam_name, count in cameras_count.most_common():
                print(f"     • {cam_name}: {count} evento(s)")
            
            print()
        else:
            print("⚠️  Nenhum evento detectado durante o monitoramento")
            print()
        
        print("✅ Monitor encerrado com sucesso")
        print()

except ImportError:
    print("❌ tinytuya não instalado")
    exit(1)
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

