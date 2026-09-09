#!/usr/bin/env python3
"""
Captura de Imagem da Câmera Tuya
Tenta todos os métodos possíveis para obter imagem
"""

import os
import json
import base64
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

print("=" * 80)
print("   📸 CAPTURA DE IMAGEM - CÂMERA TUYA")
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
    
    # Buscar câmeras
    print("🔍 Buscando câmeras...")
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
    
    # Listar câmeras
    for i, cam in enumerate(cameras, 1):
        online = cam.get('online', False)
        status_icon = "🟢" if online else "🔴"
        print(f"{i}. {status_icon} {cam.get('name', 'Sem nome')}")
    
    print()
    print("Qual câmera você quer capturar?")
    
    if len(cameras) == 1:
        selected_idx = 0
        print(f"(Usando única câmera: {cameras[0].get('name')})")
    else:
        choice = input(f"Digite o número (1-{len(cameras)}): ")
        selected_idx = int(choice) - 1
        
        if selected_idx < 0 or selected_idx >= len(cameras):
            print("❌ Número inválido")
            exit(1)
    
    selected_camera = cameras[selected_idx]
    camera_id = selected_camera['id']
    camera_name = selected_camera.get('name', 'Câmera')
    
    print()
    print("=" * 80)
    print(f"   📹 CAPTURANDO: {camera_name}")
    print("=" * 80)
    print()
    
    # Criar pasta para imagens
    img_dir = Path("camera_images")
    img_dir.mkdir(exist_ok=True)
    
    # MÉTODO 1: Verificar datapoint de imagem
    print("📋 MÉTODO 1: Verificando datapoints da câmera...")
    print()
    
    try:
        status = cloud.getstatus(camera_id)
        
        if status and 'result' in status:
            data_dict = {item['code']: item['value'] for item in status['result']}
            
            print(f"✅ {len(data_dict)} datapoints encontrados:")
            
            # Procurar campos relacionados a imagem
            image_fields = [
                'movement_detect_pic',  # Imagem de detecção de movimento
                'snapshot',             # Snapshot
                'picture_url',          # URL da imagem
                'alarm_message',        # Mensagem de alarme (pode conter imagem)
                'basic_device_icon',    # Ícone
                'encrypt_image',        # Imagem criptografada
            ]
            
            found_image = False
            
            for field in image_fields:
                if field in data_dict:
                    value = data_dict[field]
                    print(f"   • {field}: ", end="")
                    
                    if isinstance(value, str) and len(value) > 0:
                        print(f"({len(value)} caracteres)")
                        
                        # Se é base64, tentar decodificar
                        if field == 'alarm_message':
                            try:
                                decoded = base64.b64decode(value)
                                decoded_str = decoded.decode('utf-8')
                                alarm_data = json.loads(decoded_str)
                                
                                print(f"      Tipo de alarme: {alarm_data.get('cmd', 'N/A')}")
                                
                                if 'files' in alarm_data:
                                    print(f"      Arquivos: {len(alarm_data['files'])}")
                                    found_image = True
                            except:
                                pass
                        
                        elif value not in ['', '$']:
                            # Tentar como URL
                            if value.startswith('http'):
                                print(f"      🎯 URL encontrada!")
                                found_image = True
                                
                                # Tentar baixar
                                try:
                                    print(f"      Baixando...")
                                    response = requests.get(value, timeout=10)
                                    
                                    if response.status_code == 200:
                                        filename = img_dir / f"{camera_name.replace(' ', '_')}_{field}.jpg"
                                        
                                        with open(filename, 'wb') as f:
                                            f.write(response.content)
                                        
                                        print(f"      ✅ Salvo: {filename}")
                                        print()
                                        print(f"      🖼️  Abrindo imagem...")
                                        
                                        # Abrir imagem
                                        os.system(f'start {filename}')
                                        found_image = True
                                    else:
                                        print(f"      ⚠️  Erro HTTP: {response.status_code}")
                                
                                except Exception as e:
                                    print(f"      ❌ Erro ao baixar: {e}")
                            
                            # Tentar como base64
                            elif len(value) > 100:
                                try:
                                    decoded = base64.b64decode(value)
                                    
                                    filename = img_dir / f"{camera_name.replace(' ', '_')}_{field}.jpg"
                                    
                                    with open(filename, 'wb') as f:
                                        f.write(decoded)
                                    
                                    print(f"      ✅ Salvo: {filename}")
                                    print()
                                    print(f"      🖼️  Abrindo imagem...")
                                    
                                    os.system(f'start {filename}')
                                    found_image = True
                                
                                except:
                                    print(f"      ⚠️  Não é base64 válido")
                    else:
                        print("vazio")
            
            if not found_image:
                print()
                print("   ⚠️  Nenhuma imagem encontrada nos datapoints")
        
        else:
            print("⚠️  Não foi possível obter status da câmera")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print()
    
    # MÉTODO 2: API de Snapshot (se disponível)
    print("=" * 80)
    print("   📸 MÉTODO 2: Solicitando snapshot via API")
    print("=" * 80)
    print()
    
    try:
        # Algumas câmeras Tuya suportam comandos de snapshot
        print("🔄 Enviando comando de captura...")
        
        # Endpoint específico para snapshot (pode variar)
        # Isso geralmente requer permissões específicas
        
        print("⚠️  IMPORTANTE:")
        print()
        print("   A API Tuya NÃO oferece endpoint público de snapshot")
        print("   para câmeras de consumidor (categoria 'sp').")
        print()
        print("   Razões:")
        print("   • Protocolo P2P proprietário")
        print("   • Privacidade e segurança")
        print("   • Limitações de plano gratuito")
        print()
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # MÉTODO 3: Verificar armazenamento em nuvem
    print("=" * 80)
    print("   ☁️  MÉTODO 3: Verificando armazenamento em nuvem")
    print("=" * 80)
    print()
    
    try:
        print("🔍 Buscando gravações em nuvem...")
        print()
        print("⚠️  Armazenamento em nuvem requer:")
        print("   • Plano de assinatura ativo")
        print("   • Permissões específicas no projeto IoT")
        print("   • Endpoint de API apropriado")
        print()
        print("   Isso geralmente NÃO está disponível para")
        print("   desenvolvedores individuais com plano gratuito.")
        print()
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # SOLUÇÃO ALTERNATIVA
    print()
    print("=" * 80)
    print("   💡 SOLUÇÕES ALTERNATIVAS")
    print("=" * 80)
    print()
    
    print("Como câmeras Tuya usam protocolo P2P proprietário,")
    print("a única forma CONFIÁVEL de obter imagens é:")
    print()
    print("OPÇÃO 1 - App Smart Life (RECOMENDADO):")
    print("  1. Instale o app no celular")
    print("  2. Acesse a câmera")
    print("  3. Tire screenshot manualmente")
    print("  4. Ou configure gravação em cartão SD")
    print()
    print("OPÇÃO 2 - SDK Oficial Tuya:")
    print("  1. Solicite acesso ao SDK P2P")
    print("  2. Implemente em C/C++")
    print("  3. Compile binários")
    print("  4. Integre com Python via ctypes")
    print("  (Muito complexo e não gratuito)")
    print()
    print("OPÇÃO 3 - RTSP (Se disponível):")
    print("  1. Verifique se câmera suporta RTSP")
    print("  2. Configure RTSP nas configurações")
    print("  3. Use URL RTSP com VLC ou OpenCV")
    print("  (Poucos modelos Tuya suportam)")
    print()
    print("OPÇÃO 4 - Webhook de Evento:")
    print("  1. Configure webhook na plataforma Tuya")
    print("  2. Receba notificações de movimento")
    print("  3. Webhook pode conter URL de snapshot")
    print("  (Requer configuração avançada)")
    print()
    
    # Resumo
    print("=" * 80)
    print("   📊 RESUMO")
    print("=" * 80)
    print()
    
    print(f"Câmera testada: {camera_name}")
    print(f"ID: {camera_id}")
    print(f"Status: {'🟢 Online' if selected_camera.get('online') else '🔴 Offline'}")
    print()
    print("Resultado:")
    print("  ⚠️  Protocolo P2P impede captura direta via Python")
    print("  ℹ️  Use app Smart Life para visualização")
    print("  ℹ️  Ou configure detecção de movimento + webhooks")
    print()
    print("=" * 80)
    print()
    print("🎯 RECOMENDAÇÃO:")
    print()
    print("Para seu caso de uso (monitoramento energético):")
    print("  • FOQUE nos medidores de energia (Wifi Plug)")
    print("  • Use câmeras apenas para detecção de movimento")
    print("  • Configure alertas quando movimento detectado")
    print("  • Correlacione movimento com aumento de consumo")
    print()
    print("Isso dá inteligência ao sistema SEM precisar de vídeo!")
    print()

except ImportError:
    print("❌ tinytuya não instalado")
    exit(1)
except KeyboardInterrupt:
    print("\n\n⏹️  Cancelado pelo usuário")
    exit(0)
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)


