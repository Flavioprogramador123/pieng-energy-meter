"""
Tuya Poller - Coleta automática de dados dos dispositivos Tuya
APENAS DADOS REAIS!
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.core.db import get_db
from app.models import Device, Measurement
from app.core.config import settings

# Carregar .env
load_dotenv()


def get_tuya_client():
    """Retorna cliente Tuya Cloud configurado"""
    try:
        import tinytuya
        
        access_id = settings.tuya_access_id
        access_secret = settings.tuya_access_secret
        region = settings.tuya_api_region
        
        if not access_id or not access_secret:
            print("⚠️  Credenciais Tuya não configuradas")
            return None
        
        cloud = tinytuya.Cloud(
            apiRegion=region,
            apiKey=access_id,
            apiSecret=access_secret
        )
        
        return cloud
    
    except ImportError:
        print("❌ tinytuya não instalado")
        return None
    except Exception as e:
        print(f"❌ Erro ao conectar Tuya: {e}")
        return None


def parse_tuya_data(device_id: str, status_result: List[Dict]) -> Dict[str, Any]:
    """
    Converte dados Tuya em métricas padronizadas
    
    Args:
        device_id: ID do dispositivo Tuya
        status_result: Lista de datapoints do status
    
    Returns:
        Dict com métricas padronizadas
    """
    metrics = {}
    
    # Converter lista em dict
    data_dict = {item['code']: item['value'] for item in status_result}
    
    # Mapear campos Tuya para métricas
    
    # Energia (Wh) - converter de kWh para Wh para compatibilidade com dashboard
    if 'add_ele' in data_dict:
        metrics['energy_wh'] = float(data_dict['add_ele']) * 1000  # kWh -> Wh
    
    # Tensão (V) - converter de mV para V
    if 'cur_voltage' in data_dict:
        metrics['voltage'] = float(data_dict['cur_voltage']) / 10.0
    
    # Corrente (A) - converter de mA para A
    if 'cur_current' in data_dict:
        metrics['current'] = float(data_dict['cur_current']) / 1000.0
    
    # Potência (W) - converter de dW para W
    if 'cur_power' in data_dict:
        metrics['power'] = float(data_dict['cur_power']) / 10.0
    
    # Status switch (on/off)
    if 'switch_1' in data_dict:
        metrics['switch_status'] = 1 if data_dict['switch_1'] else 0
    
    # Fator de potência (calcular se temos V, A e W)
    if 'voltage' in metrics and 'current' in metrics and 'power' in metrics:
        voltage = metrics['voltage']
        current = metrics['current']
        power = metrics['power']
        
        if voltage > 0 and current > 0:
            apparent_power = voltage * current
            if apparent_power > 0:
                metrics['power_factor'] = min(power / apparent_power, 1.0)
    
    return metrics


def poll_tuya_devices():
    """
    Coleta dados de todos os dispositivos Tuya ativos
    Salva medições no banco de dados
    
    APENAS DADOS REAIS!
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Iniciando polling Tuya...")
    
    # Obter cliente Tuya
    cloud = get_tuya_client()
    
    if not cloud:
        print("   ⚠️  Cliente Tuya não disponível")
        return
    
    # Obter sessão do banco
    db = next(get_db())
    
    try:
        # Buscar dispositivos Tuya ativos
        tuya_devices = db.query(Device).filter(
            Device.device_type == "tuya",
            Device.active == True
        ).all()
        
        if not tuya_devices:
            print("   ℹ️  Nenhum dispositivo Tuya ativo")
            return
        
        print(f"   📊 {len(tuya_devices)} dispositivo(s) Tuya para coletar")
        
        measurements_count = 0
        
        for device in tuya_devices:
            try:
                # Parsear config
                config = json.loads(device.config) if isinstance(device.config, str) else device.config
                
                tuya_device_id = config.get('device_id')
                
                if not tuya_device_id:
                    print(f"   ⚠️  {device.name}: Sem device_id configurado")
                    continue
                
                # Ler status do dispositivo
                status = cloud.getstatus(tuya_device_id)
                
                if not status or 'result' not in status:
                    print(f"   ⚠️  {device.name}: Sem resposta")
                    continue
                
                result = status['result']
                
                if not result:
                    print(f"   ℹ️  {device.name}: Sem dados")
                    continue
                
                # Converter dados
                metrics = parse_tuya_data(tuya_device_id, result)
                
                if not metrics:
                    print(f"   ⚠️  {device.name}: Nenhuma métrica extraída")
                    continue
                
                # Salvar cada métrica
                timestamp = datetime.now()
                
                for metric_name, metric_value in metrics.items():
                    measurement = Measurement(
                        device_id=device.id,
                        timestamp=timestamp,
                        metric=metric_name,
                        value=metric_value,
                        extra=json.dumps({
                            'source': 'tuya_cloud_api',
                            'tuya_device_id': tuya_device_id
                        })
                    )
                    
                    db.add(measurement)
                    measurements_count += 1
                
                print(f"   ✅ {device.name}: {len(metrics)} métrica(s) coletadas")
                
                # Log das métricas
                if 'energy_wh' in metrics:
                    print(f"      ⚡ Energia: {metrics['energy_wh']/1000:.2f} kWh")
                if 'voltage' in metrics:
                    print(f"      📊 Tensão: {metrics['voltage']:.1f} V")
                if 'current' in metrics:
                    print(f"      📈 Corrente: {metrics['current']:.3f} A")
                if 'power' in metrics:
                    print(f"      🔋 Potência: {metrics['power']:.1f} W")
            
            except Exception as e:
                print(f"   ❌ {device.name}: Erro - {e}")
                continue
        
        # Commit das medições
        if measurements_count > 0:
            db.commit()
            print(f"   💾 {measurements_count} medição(ões) salva(s) no banco")
        else:
            print(f"   ℹ️  Nenhuma medição para salvar")
    
    except Exception as e:
        print(f"   ❌ Erro no polling: {e}")
        db.rollback()
    
    finally:
        db.close()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Polling Tuya concluído\n")


if __name__ == "__main__":
    # Teste manual
    print("=" * 80)
    print("   🧪 TESTE MANUAL - TUYA POLLER")
    print("=" * 80)
    print()
    
    poll_tuya_devices()
    
    print()
    print("✅ Teste concluído!")
    print("   Verifique o banco de dados para ver as medições")
    print()

