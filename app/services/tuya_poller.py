"""
Tuya Poller - Coleta automática de dados dos dispositivos Tuya
APENAS DADOS REAIS!
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.core.db import get_db
from app.models import Device, Measurement
from app.core.config import settings
from app.services import firebase_sync

# Carregar .env
load_dotenv()


def get_tuya_client(api_device_id: Optional[str] = None):
    """Retorna cliente Tuya Cloud configurado"""
    try:
        import tinytuya
        
        access_id = settings.tuya_access_id
        access_secret = settings.tuya_access_secret
        region = settings.tuya_api_region or "us"
        
        if not access_id or not access_secret:
            print("[WARN] Credenciais Tuya nao configuradas")
            return None
        
        kwargs = {
            "apiRegion": region,
            "apiKey": access_id,
            "apiSecret": access_secret,
        }
        if api_device_id:
            kwargs["apiDeviceID"] = api_device_id
        
        cloud = tinytuya.Cloud(**kwargs)
        return cloud
    
    except ImportError:
        print("[ERR] tinytuya nao instalado")
        return None
    except Exception as e:
        print(f"[ERR] Erro ao conectar Tuya: {e}")
        return None


def fetch_tuya_status(cloud, tuya_device_id: str) -> Tuple[Optional[List], Optional[str]]:
    """
    Busca status do device.

    Usa primeiro o "device shadow" (v2.0/cloud/thing/{id}/shadow/properties), que
    retorna TODOS os data points do dispositivo. O endpoint legado v1.0 (getstatus)
    fica restrito à lista declarada em /specification, que para algumas categorias
    (ex.: disjuntores trifásicos "tdq") não inclui os DPs de medição elétrica
    (voltage_a, current_a, active_power_a, ...) mesmo estando o device reportando-os.
    """
    try:
        shadow = cloud._tuyaplatform(f"cloud/thing/{tuya_device_id}/shadow/properties", ver="v2.0")
        if isinstance(shadow, dict) and shadow.get("success"):
            props = shadow.get("result", {}).get("properties")
            if isinstance(props, list) and props:
                return props, None
    except Exception:
        pass  # cai para o fallback abaixo

    status = cloud.getstatus(tuya_device_id)
    if isinstance(status, dict) and status.get("success") and isinstance(status.get("result"), list):
        return status["result"], None

    # Fallback: endpoint clássico (mesmo data center da região)
    try:
        alt = cloud._tuyaplatform(f"devices/{tuya_device_id}/status")
        if isinstance(alt, dict) and alt.get("success") and isinstance(alt.get("result"), list):
            return alt["result"], None
        status = alt if isinstance(alt, dict) else status
    except Exception as e:
        return None, f"fallback_status_err={e}"

    if not isinstance(status, dict):
        return None, "resposta invalida da API"

    if status.get("Error") or status.get("Err"):
        return None, f"{status.get('Err')}: {status.get('Error') or status.get('Payload')}"

    code = status.get("code")
    msg = status.get("msg") or status.get("message") or "sem detalhe"
    if code or status.get("success") is False:
        return None, f"code={code} msg={msg}"

    if "result" not in status:
        return None, f"sem result: {status}"

    result = status.get("result")
    if not result:
        return None, "result vazio"

    return result, None


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

    # Medidor/disjuntor trifásico (categoria Tuya "tdq"): voltage_a/b/c, current_a/b/c,
    # active_power_a/b/c, power_factor_a/b/c, forward_energy_total, etc.
    # Reaproveita os mesmos nomes de métrica usados pelo driver SDM630 (voltage_l1,
    # power_total, energy_kwh...) para que a Análise Temporal funcione sem alterações.
    phase_map = {'a': 'l1', 'b': 'l2', 'c': 'l3'}
    voltages, currents, power_factors = [], [], []

    for src, dst in phase_map.items():
        if f'voltage_{src}' in data_dict:
            v = float(data_dict[f'voltage_{src}']) / 10.0
            metrics[f'voltage_{dst}'] = v
            voltages.append(v)

        if f'current_{src}' in data_dict:
            c = float(data_dict[f'current_{src}']) / 1000.0
            metrics[f'current_{dst}'] = c
            currents.append(c)

        if f'active_power_{src}' in data_dict:
            metrics[f'power_{dst}'] = float(data_dict[f'active_power_{src}'])

        if f'power_factor_{src}' in data_dict:
            pf = float(data_dict[f'power_factor_{src}']) / 100.0
            metrics[f'power_factor_{dst}'] = pf
            power_factors.append(pf)

    if voltages:
        metrics['voltage_avg'] = sum(voltages) / len(voltages)

    if 'current_total' in data_dict:
        metrics['current_total'] = float(data_dict['current_total']) / 1000.0
    elif currents:
        metrics['current_total'] = sum(currents)

    if 'active_power_total' in data_dict:
        metrics['power_total'] = float(data_dict['active_power_total'])
    elif 'power_l1' in metrics or 'power_l2' in metrics or 'power_l3' in metrics:
        metrics['power_total'] = sum(metrics.get(f'power_{p}', 0.0) for p in ('l1', 'l2', 'l3'))

    if power_factors and 'power_factor' not in metrics:
        metrics['power_factor'] = sum(power_factors) / len(power_factors)

    if 'forward_energy_total' in data_dict:
        energy_kwh = float(data_dict['forward_energy_total']) / 100.0
        metrics['energy_kwh'] = energy_kwh
        metrics.setdefault('energy_wh', energy_kwh * 1000)

    if 'frequency' in data_dict:
        metrics['frequency'] = float(data_dict['frequency'])

    return metrics


def poll_tuya_devices():
    """
    Coleta dados de todos os dispositivos Tuya ativos
    Salva medições no banco de dados
    
    APENAS DADOS REAIS!
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando polling Tuya...")
    
    # Obter cliente Tuya
    cloud = get_tuya_client()
    
    if not cloud:
        print("   [WARN] Cliente Tuya nao disponivel")
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
            print("   [INFO] Nenhum dispositivo Tuya ativo")
            return
        
        print(f"   [INFO] {len(tuya_devices)} dispositivo(s) Tuya para coletar")
        
        measurements_count = 0
        
        for device in tuya_devices:
            try:
                # Parsear config
                config = json.loads(device.config) if isinstance(device.config, str) else device.config
                
                tuya_device_id = config.get('device_id')
                
                if not tuya_device_id:
                    print(f"   [WARN] {device.name}: Sem device_id configurado")
                    continue
                
                result, err = fetch_tuya_status(cloud, tuya_device_id)
                if err:
                    print(f"   [WARN] {device.name}: API Tuya -> {err}")
                    continue
                
                # Converter dados
                metrics = parse_tuya_data(tuya_device_id, result)
                
                if not metrics:
                    print(f"   [WARN] {device.name}: Nenhuma metrica extraida")
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

                if firebase_sync.push_reading(device.id, device.name, "tuya", metrics, timestamp):
                    print(f"   [OK] {device.name}: leitura sincronizada com Firebase")

                print(f"   [OK] {device.name}: {len(metrics)} metrica(s) coletadas")
                
                # Log das métricas
                if 'energy_wh' in metrics:
                    print(f"      Energia: {metrics['energy_wh']/1000:.2f} kWh")
                if 'voltage' in metrics:
                    print(f"      Tensao: {metrics['voltage']:.1f} V")
                if 'current' in metrics:
                    print(f"      Corrente: {metrics['current']:.3f} A")
                if 'power' in metrics:
                    print(f"      Potencia: {metrics['power']:.1f} W")
            
            except Exception as e:
                print(f"   [ERR] {device.name}: Erro - {e}")
                continue
        
        # Commit das medições
        if measurements_count > 0:
            db.commit()
            print(f"   [OK] {measurements_count} medicao(oes) salva(s) no banco")
        else:
            print(f"   [INFO] Nenhuma medicao para salvar")
    
    except Exception as e:
        print(f"   [ERR] Erro no polling: {e}")
        db.rollback()
    
    finally:
        db.close()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling Tuya concluido\n")


if __name__ == "__main__":
    # Teste manual
    print("=" * 80)
    print("   TESTE MANUAL - TUYA POLLER")
    print("=" * 80)
    print()
    
    poll_tuya_devices()
    
    print()
    print("[OK] Teste concluido!")
    print("   Verifique o banco de dados para ver as medicoes")
    print()
