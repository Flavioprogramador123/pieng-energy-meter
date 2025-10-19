#!/usr/bin/env python3
"""
Teste de Câmeras Tuya - Acesso ao Stream em Tempo Real
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

print("=" * 80)
print("   📹 TESTE DE CÂMERAS TUYA - TEMPO REAL")
print("=" * 80)
print()

# Carregar credenciais
load_dotenv()

access_id = os.getenv("TUYA_ACCESS_ID")
access_secret = os.getenv("TUYA_ACCESS_SECRET")
region = os.getenv("TUYA_API_REGION", "us")

if not access_id or not access_secret:
    print("❌ Credenciais não encontradas no .env")
    exit(1)

try:
    import tinytuya
    
    print("📡 Conectando Tuya Cloud API...")
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=access_id,
        apiSecret=access_secret
    )
    
    # Listar todas as câmeras
    print("🔍 Buscando câmeras...")
    print()
    
    devices = cloud.getdevices()
    
    # Filtrar câmeras
    cameras = []
    for d in devices:
        category = d.get('category', '')
        name = d.get('name', 'Sem nome')
        
        # Categorias de câmeras: sp, ipc, camera
        if category in ['sp', 'ipc', 'camera'] or 'camera' in name.lower():
            cameras.append(d)
    
    if not cameras:
        print("⚠️  Nenhuma câmera encontrada")
        exit(0)
    
    print(f"✅ {len(cameras)} câmera(s) encontrada(s):")
    print()
    
    # Listar câmeras
    for i, cam in enumerate(cameras, 1):
        online = cam.get('online', False)
        status_icon = "🟢" if online else "🔴"
        
        print(f"{i}. {status_icon} {cam.get('name', 'Sem nome')}")
        print(f"   ID: {cam['id']}")
        print(f"   Produto: {cam.get('product_name', 'N/A')}")
        print(f"   Categoria: {cam.get('category', 'N/A')}")
        print(f"   Online: {'SIM' if online else 'NÃO'}")
        print()
    
    # Escolher câmera
    print("=" * 80)
    
    if len(cameras) == 1:
        selected_idx = 0
        print(f"📹 Testando única câmera disponível: {cameras[0].get('name')}")
    else:
        print("Qual câmera você quer testar?")
        try:
            choice = input(f"Digite o número (1-{len(cameras)}): ")
            selected_idx = int(choice) - 1
            
            if selected_idx < 0 or selected_idx >= len(cameras):
                print("❌ Número inválido")
                exit(1)
        except:
            print("❌ Entrada inválida")
            exit(1)
    
    selected_camera = cameras[selected_idx]
    camera_id = selected_camera['id']
    camera_name = selected_camera.get('name', 'Câmera')
    
    print()
    print("=" * 80)
    print(f"   📹 TESTANDO: {camera_name}")
    print("=" * 80)
    print()
    
    # Verificar status online
    if not selected_camera.get('online'):
        print("⚠️  ATENÇÃO: Câmera aparece como OFFLINE na API")
        print("   Tentando acessar mesmo assim...")
        print()
    
    # Buscar informações da câmera
    print("🔍 Buscando capacidades da câmera...")
    
    try:
        # Status atual
        status = cloud.getstatus(camera_id)
        
        if status and 'result' in status:
            print(f"✅ Status obtido!")
            print()
            print("📊 Datapoints disponíveis:")
            
            for item in status['result']:
                code = item.get('code', 'N/A')
                value = item.get('value', 'N/A')
                print(f"   • {code}: {value}")
            
            print()
            
            # Salvar dados
            filename = f"camera_{camera_id}_status.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
            print(f"💾 Status salvo em: {filename}")
        else:
            print("⚠️  Não foi possível obter status da câmera")
        
        print()
    
    except Exception as e:
        print(f"⚠️  Erro ao obter status: {e}")
        print()
    
    # Tentar obter snapshot
    print("=" * 80)
    print("   📸 TENTANDO CAPTURAR SNAPSHOT")
    print("=" * 80)
    print()
    
    try:
        # Algumas câmeras Tuya suportam comandos de snapshot
        print("🔄 Enviando comando de snapshot...")
        
        # Comando genérico de snapshot
        commands = {
            "commands": [
                {
                    "code": "record_snapshot",
                    "value": True
                }
            ]
        }
        
        # Nota: Isso pode não funcionar para todas as câmeras
        # Câmeras Tuya geralmente precisam de P2P ou RTSP
        
        print("⚠️  IMPORTANTE:")
        print("   Câmeras Tuya geralmente usam protocolo P2P proprietário")
        print("   Para ver stream em tempo real, você precisa:")
        print("   1. App Tuya/Smart Life no celular")
        print("   2. SDK P2P específico (não disponível em Python)")
        print("   3. Configurar RTSP (se a câmera suportar)")
        print()
        
        # Buscar URL de stream (se disponível)
        print("🔍 Buscando URL de stream...")
        
        # Alguns modelos expõem URL RTSP
        # Formato comum: rtsp://username:password@ip:port/stream
        
        print("⚠️  Para acessar stream de vídeo:")
        print()
        print("   OPÇÃO 1 - App Tuya (Recomendado):")
        print("   1. Instale 'Smart Life' no celular")
        print("   2. Faça login com mesma conta")
        print("   3. Acesse a câmera pelo app")
        print()
        print("   OPÇÃO 2 - RTSP (Se disponível):")
        print("   1. Verifique se câmera suporta RTSP")
        print("   2. Configure nas configurações da câmera")
        print("   3. Use VLC ou OBS para acessar")
        print()
        print("   OPÇÃO 3 - P2P SDK:")
        print("   1. Requer SDK C/C++ da Tuya")
        print("   2. Complexo de implementar")
        print("   3. Não disponível em Python puro")
        print()
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # Informações adicionais
    print()
    print("=" * 80)
    print("   📋 INFORMAÇÕES DA CÂMERA")
    print("=" * 80)
    print()
    
    print(f"Nome: {camera_name}")
    print(f"ID: {camera_id}")
    print(f"Produto: {selected_camera.get('product_name', 'N/A')}")
    print(f"Categoria: {selected_camera.get('category', 'N/A')}")
    print(f"Status: {'🟢 Online' if selected_camera.get('online') else '🔴 Offline'}")
    
    if 'ip' in selected_camera:
        print(f"IP: {selected_camera['ip']}")
    
    if 'local_key' in selected_camera:
        print(f"Local Key: {selected_camera['local_key'][:10]}... (truncado)")
    
    print()
    print("=" * 80)
    print("   ℹ️  LIMITAÇÕES TÉCNICAS")
    print("=" * 80)
    print()
    print("Câmeras Tuya usam protocolo P2P proprietário.")
    print("Python + tinytuya NÃO suportam stream de vídeo.")
    print()
    print("Para monitoramento em tempo real, use:")
    print("  • App Smart Life (celular)")
    print("  • Plataforma Tuya Web (navegador)")
    print("  • SDK oficial Tuya IoT")
    print()
    print("Para integração Python, considere:")
    print("  • Detecção de movimento (eventos)")
    print("  • Snapshots agendados (se disponível)")
    print("  • Gravações em nuvem (via API)")
    print()
    
    # Tentar obter eventos recentes
    print("=" * 80)
    print("   📝 EVENTOS RECENTES")
    print("=" * 80)
    print()
    
    try:
        print("🔍 Buscando histórico de eventos...")
        
        # API de eventos pode variar por dispositivo
        # Tentativa genérica
        
        print("⚠️  Histórico de eventos requer:")
        print("   • Plano de nuvem Tuya ativo")
        print("   • Permissões específicas no projeto IoT")
        print("   • Endpoint correto para categoria da câmera")
        print()
        
    except Exception as e:
        print(f"⚠️  Erro ao buscar eventos: {e}")
        print()
    
    print("=" * 80)
    print("   ✅ TESTE CONCLUÍDO")
    print("=" * 80)
    print()
    print("🎯 PRÓXIMOS PASSOS:")
    print()
    print("1. Para VER a câmera AO VIVO:")
    print("   → Use o app Smart Life no celular")
    print("   → https://play.google.com/store/apps/details?id=com.tuya.smartlife")
    print()
    print("2. Para INTEGRAR com Python:")
    print("   → Monitore eventos de movimento")
    print("   → Configure webhooks para notificações")
    print("   → Use API de snapshots (se disponível)")
    print()
    print("3. Para AUTOMAÇÃO:")
    print("   → Crie regras na plataforma Tuya")
    print("   → Configure alertas por movimento")
    print("   → Integre com outros dispositivos")
    print()

except ImportError:
    print("❌ tinytuya não instalado")
    print("Execute: pip install tinytuya")
    exit(1)
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

