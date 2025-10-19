# 🔌 Integração de Dispositivos IoT - PIENG Energy

> **Data**: 18/10/2025  
> **Objetivo**: Integrar todos os dispositivos do laboratório com a plataforma  
> **Status**: 🔧 Guia de configuração

---

## 📦 Inventário de Equipamentos

### ✅ **Dispositivos Operacionais**

| Dispositivo | Tipo | Protocolo | Status | Uso |
|-------------|------|-----------|--------|-----|
| **Eastron SDM630-MCT** | Medidor trifásico | Modbus TCP | ✅ Operando | Entrada principal |
| **Elfin EW11** | Gateway RS485→WiFi | Modbus TCP | ✅ Operando | Bridge para SDM630 |
| **2x Tuya Smart Meter** | Medidor WiFi | Tuya Cloud API | ✅ Operando | Cargas individuais |
| **2x PZEM-004T** | Medidor monofásico | Modbus RTU (USB) | ✅ Teste | Desenvolvimento |
| **USR-G771 LTE CAT1-DTU** | Gateway LTE 4G | TCP/UDP/MQTT | 🆕 Chegou | Acesso remoto |

---

## 🌐 Arquitetura de Rede Recomendada

### **Opção 1: Acesso Direto (Mais Simples, Menos Seguro)**

```
Internet ←→ Roteador (Port Forwarding) ←→ Dispositivos
                ↓
         Portas Abertas:
         - 8899: Elfin EW11 (Modbus TCP)
         - 8000: Backend Python (FastAPI)
         - 3000: Backend Node.js
         - 5432: PostgreSQL (NÃO recomendado!)
```

⚠️ **ATENÇÃO**: Abrir portas diretamente para internet é **arriscado**!

---

### **Opção 2: VPN + Túnel (RECOMENDADO)**

```
Internet
   ↓
Fidelco (Servidor VPN WireGuard)
   ↓
Túnel VPN Seguro
   ↓
Roteador Local → Dispositivos
```

✅ **Vantagens**:
- Segurança máxima
- Sem portas abertas para internet
- Acesso como se estivesse na rede local

---

### **Opção 3: USR-G771 LTE + Cloud (IDEAL para Clientes)**

```
Dispositivos → USR-G771 (LTE 4G) → Internet → Seu Servidor
```

✅ **Vantagens**:
- Não depende do roteador do cliente
- Funciona mesmo sem WiFi
- Instalação em qualquer lugar com sinal 4G

---

## 🔐 Configuração de Port Forwarding (Opção 1)

### **Passo 1: Descobrir IP Local dos Dispositivos**

```bash
# No Windows (PowerShell)
arp -a

# Procurar por:
# - Elfin EW11: normalmente 192.168.x.x
# - Fidelco: IP local do servidor
```

**Anotar IPs**:
```
Elfin EW11: 192.168.1.109 (exemplo)
Fidelco: 192.168.1.100
PC Dev: 192.168.1.50
```

---

### **Passo 2: Configurar IP Estático (Recomendado)**

**No roteador, reservar IPs por MAC address**:

```
1. Acessar roteador (geralmente 192.168.0.1 ou 192.168.1.1)
2. Usuário/senha (geralmente admin/admin ou no adesivo)
3. Procurar: "DHCP" → "Reserva de IP" ou "Static DHCP"
4. Adicionar:
   - Elfin EW11 (MAC: XX:XX:XX:XX:XX:XX) → 192.168.1.109
   - Fidelco (MAC: XX:XX:XX:XX:XX:XX) → 192.168.1.100
```

---

### **Passo 3: Configurar Port Forwarding**

**No roteador, procurar**: "Port Forwarding", "Virtual Server" ou "NAT"

**Adicionar regras**:

| Nome | Porta Externa | IP Interno | Porta Interna | Protocolo |
|------|---------------|------------|---------------|-----------|
| Elfin_Modbus | 8899 | 192.168.1.109 | 8899 | TCP |
| Backend_Python | 8000 | 192.168.1.100 | 8000 | TCP |
| Backend_Node | 3000 | 192.168.1.100 | 3000 | TCP |

⚠️ **NÃO abrir porta 5432 (PostgreSQL) diretamente!**

---

### **Passo 4: Obter IP Público**

```bash
# No PC ou Fidelco
curl ifconfig.me
# ou
curl ipinfo.io/ip
```

**Anotar**: Seu IP público (ex: 200.100.50.25)

⚠️ **Se IP mudar** (IP dinâmico), usar serviço DDNS:
- No-IP (gratuito)
- DuckDNS (gratuito)
- DynDNS

---

### **Passo 5: Testar Acesso Externo**

```bash
# De outro lugar (celular com 4G, trabalho, etc)
# NÃO testar da mesma rede local!

# Testar Elfin EW11 (Modbus)
telnet SEU_IP_PUBLICO 8899

# Testar Backend
curl http://SEU_IP_PUBLICO:8000/
```

---

## 🔒 Segurança para Portas Abertas

### **1. Firewall no Fidelco/Servidor**

```bash
# Permitir apenas IPs específicos (exemplo)
sudo ufw allow from 200.100.0.0/16 to any port 8000 proto tcp
sudo ufw allow from 200.100.0.0/16 to any port 3000 proto tcp

# Bloquear resto
sudo ufw deny 8000/tcp
sudo ufw deny 3000/tcp
```

### **2. Autenticação nas APIs**

```python
# No FastAPI, adicionar API Key
from fastapi import Header, HTTPException

API_KEY = "sua-chave-super-secreta-aqui"

async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="API Key inválida")
    return x_api_key

# Usar em rotas
@app.get("/api/metrics", dependencies=[Depends(verify_api_key)])
def get_metrics():
    # ...
```

### **3. Rate Limiting**

```python
# Limitar requisições por IP
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/metrics")
@limiter.limit("10/minute")  # Máximo 10 req/min por IP
def get_metrics():
    # ...
```

---

## 📱 Integração Tuya Smart Meters

### **Obter Tokens e Configurar API**

#### **Passo 1: Criar Conta Tuya Developer**

1. Acessar: https://iot.tuya.com/
2. Registrar conta (gratuita)
3. Login

---

#### **Passo 2: Criar Cloud Project**

```
1. No dashboard, clicar "Cloud" → "Development"
2. Criar novo projeto:
   - Name: PIENG Energy Monitor
   - Industry: Smart Home ou Energy
   - Data Center: escolher mais próximo (Americas ou Europe)
   - Development Method: Custom
3. Criar projeto
```

---

#### **Passo 3: Obter API Credentials**

```
1. No projeto criado, clicar em "Overview"
2. Copiar:
   - Access ID/Client ID (exemplo: aabbccddee1234567890)
   - Access Secret/Client Secret (exemplo: 1234567890abcdef...)
3. Guardar em local seguro!
```

---

#### **Passo 4: Linkar Dispositivos Tuya**

**Opção A: Via Tuya Smart App (Mais Fácil)**

```
1. Baixar app "Tuya Smart" ou "Smart Life"
2. Login com MESMA conta do Tuya Developer
3. Seus dispositivos já devem aparecer
4. Anotar Device IDs:
   - Abrir dispositivo no app
   - Configurações → Info do dispositivo
   - Copiar "Device ID" (exemplo: bf1234567890abcdef)
```

**Opção B: Via Tuya IoT Platform (Manual)**

```
1. No projeto Tuya, ir em "Devices" → "Link Tuya App Account"
2. Escanear QR Code com o app Tuya Smart
3. Autorizar acesso
4. Dispositivos aparecerão na plataforma
```

---

#### **Passo 5: Habilitar APIs Necessárias**

```
1. No projeto Tuya, ir em "Service API"
2. Ativar:
   - IoT Core (básico, já ativo)
   - Authorization (para tokens)
   - Device Status Notification (para tempo real)
   - Industry Basic Service (recomendado)
3. Salvar
```

---

#### **Passo 6: Testar API Tuya (Python)**

```python
# Instalar biblioteca
pip install tinytuya

# Script de teste
import tinytuya

# Suas credenciais
ACCESS_ID = "aabbccddee1234567890"
ACCESS_SECRET = "1234567890abcdef..."
DEVICE_ID = "bf1234567890abcdef"

# Configurar cloud
cloud = tinytuya.Cloud(
    apiRegion="us",  # ou "eu", "cn", "in"
    apiKey=ACCESS_ID,
    apiSecret=ACCESS_SECRET
)

# Listar dispositivos
devices = cloud.getdevices()
print("Dispositivos encontrados:")
for device in devices:
    print(f"  - {device['name']}: {device['id']}")

# Buscar status de um dispositivo
status = cloud.getstatus(DEVICE_ID)
print(f"\nStatus do dispositivo {DEVICE_ID}:")
for dp in status:
    print(f"  - {dp['code']}: {dp['value']}")
```

**Exemplo de output**:
```
Dispositivos encontrados:
  - Smart Meter Sala: bf1234567890abcdef
  - Smart Meter Cozinha: bf9876543210fedcba

Status do dispositivo bf1234567890abcdef:
  - voltage: 220
  - current: 1500
  - power: 330
  - energy: 12500
```

---

#### **Passo 7: Integrar com Energy Meter**

```python
# app/connectors/tuya.py (já existe, mas vamos melhorar)

import tinytuya
from typing import Dict, Any
from app.core.config import settings

class TuyaConnector:
    def __init__(self):
        self.cloud = tinytuya.Cloud(
            apiRegion=settings.tuya_api_region,
            apiKey=settings.tuya_access_id,
            apiSecret=settings.tuya_access_secret
        )
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Buscar status atual do dispositivo"""
        try:
            status = self.cloud.getstatus(device_id)
            
            # Converter para formato padrão
            metrics = {}
            for dp in status:
                code = dp['code']
                value = dp['value']
                
                # Mapear códigos Tuya para métricas padrão
                if code == 'voltage':
                    metrics['voltage'] = float(value) / 10  # Tuya retorna em décimos
                elif code == 'current':
                    metrics['current'] = float(value) / 1000  # mA para A
                elif code == 'power':
                    metrics['power'] = float(value) / 10  # décimos de W
                elif code in ['total_forward_energy', 'forward_energy_total']:
                    metrics['energy_kwh'] = float(value) / 100  # centésimos de kWh
            
            return metrics
        except Exception as e:
            print(f"Erro ao buscar status Tuya: {e}")
            return {}
    
    def list_devices(self) -> list:
        """Listar todos os dispositivos"""
        return self.cloud.getdevices()
```

**Adicionar em .env**:
```env
# Tuya API
TUYA_API_REGION=us
TUYA_ACCESS_ID=sua_access_id_aqui
TUYA_ACCESS_SECRET=seu_access_secret_aqui
```

**Criar poller para Tuya**:
```python
# app/services/pollers.py (adicionar)

from ..connectors.tuya import TuyaConnector

def poll_tuya_devices():
    """Poller para dispositivos Tuya"""
    db: Session = SessionLocal()
    tuya = TuyaConnector()
    
    try:
        devices = crud.list_devices(db)
        for d in devices:
            if d.device_type != "tuya" or not d.active:
                continue
            
            cfg = d.config or {}
            device_id = cfg.get("device_id")
            
            if not device_id:
                continue
            
            try:
                metrics = tuya.get_device_status(device_id)
                
                # Salvar métricas
                for metric_name, value in metrics.items():
                    crud.create_measurement(
                        db,
                        schemas.MeasurementCreate(
                            device_id=d.id,
                            metric=metric_name,
                            value=float(value)
                        )
                    )
                
                logger.info(f"Tuya poll OK: device_id={d.id}, metrics={len(metrics)}")
            except Exception as e:
                logger.error(f"Tuya poll ERROR: device_id={d.id}, error={str(e)}")
        
        db.commit()
    finally:
        db.close()

# Adicionar ao scheduler (app/main.py)
scheduler.add_job(lambda: poll_tuya_devices(), seconds=60, id="poll_tuya")
```

---

## 📡 Integração USR-G771 LTE (Gateway 4G)

### **Características do USR-G771**
- **LTE CAT1**: 10Mbps down / 5Mbps up
- **Protocolos**: TCP Client/Server, UDP, MQTT
- **Serial**: RS232 + RS485
- **GPIO**: 4 entradas digitais
- **Alimentação**: 12V DC

### **Casos de Uso**
1. **Backup de Internet**: Se WiFi cair, usar 4G
2. **Locais remotos**: Instalações sem WiFi
3. **Monitoramento móvel**: Equipamentos em movimento

---

### **Configuração USR-G771**

#### **Passo 1: Configuração Inicial (via USB)**

```
1. Conectar USR-G771 ao PC via USB
2. Instalar driver CH340 (se necessário)
3. Abrir Putty ou terminal serial:
   - Porta: COM# (verificar no Device Manager)
   - Baud Rate: 115200
   - Data: 8, Parity: None, Stop: 1

4. Comandos AT:
   AT+NETMODE=0  (auto)
   AT+CGDCONT=1,"IP","sua_apn"  (APN da operadora)
   AT+CFUN=1  (ativar rádio)
```

**APNs das operadoras brasileiras**:
```
Vivo: zap.vivo.com.br ou internet.vivo.com.br
Claro: claro.com.br
TIM: tim.br
Oi: gprs.oi.com.br
```

---

#### **Passo 2: Configurar Modo TCP Client**

**Via software USR-G771 Config Tool** (mais fácil):

```
1. Baixar: http://www.usr.cn → Suporte → USR-G771
2. Instalar e abrir
3. Configurar:
   - Work Mode: TCP Client
   - Remote Host: SEU_IP_PUBLICO ou seu-dominio.com
   - Remote Port: 8000 (porta do seu backend)
   - Local Port: 8899 (para Modbus)
   - Heart Beat: Ativado (60s)
4. Salvar e reiniciar
```

---

#### **Passo 3: Conectar Dispositivo Modbus ao USR-G771**

**Exemplo: PZEM-004T → USR-G771 → 4G → Seu Servidor**

```
Conexão física:
PZEM-004T (RS485) → USR-G771 (485-A, 485-B)

Configuração PZEM:
- A+ (Amarelo) → 485-A no USR-G771
- B- (Azul) → 485-B no USR-G771
- GND (Preto) → GND no USR-G771
```

**No backend, receber dados**:
```python
# app/routers/ingest.py (adicionar endpoint para USR-G771)

@router.post("/ingest/usr-g771")
async def ingest_usr_g771(data: dict):
    """Receber dados do USR-G771 via 4G"""
    # USR-G771 envia dados no formato configurado
    # Exemplo: JSON com medições
    
    device_id = data.get("device_id")
    metrics = data.get("metrics", {})
    
    # Salvar no banco
    for metric_name, value in metrics.items():
        crud.create_measurement(
            db,
            schemas.MeasurementCreate(
                device_id=device_id,
                metric=metric_name,
                value=float(value)
            )
        )
    
    return {"status": "ok", "metrics_saved": len(metrics)}
```

---

#### **Passo 4: Monitorar Conexão LTE**

```python
# Script de monitoramento
import requests
import time

USR_G771_IP = "192.168.1.200"  # IP local do USR-G771
API_ENDPOINT = "http://SEU_IP:8000/api/ingest/usr-g771"

while True:
    try:
        # Buscar status do USR-G771
        # (depende da API/interface do dispositivo)
        
        # Exemplo: ler dados da serial conectada
        # e enviar para seu servidor
        
        data = {
            "device_id": 1,
            "metrics": {
                "voltage": 220.5,
                "current": 3.2,
                "power": 705.6
            }
        }
        
        response = requests.post(API_ENDPOINT, json=data)
        print(f"Enviado: {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")
    
    time.sleep(30)  # A cada 30s
```

---

## 🔧 Integração PZEM-004T (USB/Serial)

### **Configuração no PC de Desenvolvimento**

```python
# Testar comunicação
import minimalmodbus

# Verificar porta COM
# Windows: COM3, COM4, etc (ver Device Manager)
# Linux: /dev/ttyUSB0

instrument = minimalmodbus.Instrument('COM3', 1)  # porta, slave_id
instrument.serial.baudrate = 9600
instrument.serial.timeout = 0.5

# Ler tensão (registro 0x0000)
voltage = instrument.read_register(0x0000, 1, 4)  # reg, decimals, function
print(f"Tensão: {voltage} V")

# Ler corrente (0x0001)
current = instrument.read_register(0x0001, 3, 4)
print(f"Corrente: {current} A")

# Ler potência (0x0003)
power = instrument.read_register(0x0003, 1, 4)
print(f"Potência: {power} W")

# Ler energia (0x0005)
energy = instrument.read_long(0x0005, 4)  # 2 registradores
print(f"Energia: {energy} Wh")
```

---

## 📊 Dashboard de Monitoramento

### **Visualizar Todos os Dispositivos**

```python
# Endpoint para status de todos os dispositivos
@router.get("/api/devices/status")
def get_all_devices_status(db: Session = Depends(get_db)):
    devices = crud.list_devices(db)
    
    status = []
    for device in devices:
        # Buscar última medição
        last_measurement = db.query(Measurement)\
            .filter(Measurement.device_id == device.id)\
            .order_by(Measurement.timestamp.desc())\
            .first()
        
        status.append({
            "device_id": device.id,
            "name": device.name,
            "type": device.device_type,
            "active": device.active,
            "last_seen": last_measurement.timestamp if last_measurement else None,
            "status": "online" if last_measurement and 
                      (datetime.utcnow() - last_measurement.timestamp).seconds < 120 
                      else "offline"
        })
    
    return status
```

**Output esperado**:
```json
[
  {
    "device_id": 1,
    "name": "SDM630 - Entrada Principal",
    "type": "modbus_tcp",
    "active": true,
    "last_seen": "2025-10-18T14:30:00Z",
    "status": "online"
  },
  {
    "device_id": 2,
    "name": "Tuya Smart Meter - Sala",
    "type": "tuya",
    "active": true,
    "last_seen": "2025-10-18T14:29:45Z",
    "status": "online"
  },
  {
    "device_id": 3,
    "name": "PZEM-004T - Teste Lab",
    "type": "modbus",
    "active": true,
    "last_seen": "2025-10-18T14:15:00Z",
    "status": "offline"
  }
]
```

---

## 🚀 Próximos Passos

### **Hoje (2 horas)**
1. ✅ Obter credenciais Tuya (Access ID + Secret)
2. ✅ Testar script Python com Tuya
3. ✅ Validar medições dos Smart Meters

### **Amanhã (3 horas)**
1. ✅ Configurar port forwarding no roteador
2. ✅ Testar acesso externo ao Elfin EW11
3. ✅ Validar SDM630 respondendo

### **Esta Semana (5 horas)**
1. ✅ Configurar USR-G771 com chip 4G
2. ✅ Testar PZEM-004T via USB
3. ✅ Integrar todos os dispositivos no banco PostgreSQL
4. ✅ Dashboard mostrando todos os equipamentos

---

## 📋 Checklist de Validação

### **Conectividade**
- [ ] Elfin EW11 responde na rede local
- [ ] Tuya Smart Meters aparecem na API
- [ ] PZEM-004T comunica via USB
- [ ] USR-G771 conecta via 4G
- [ ] Port forwarding funcionando

### **Integração**
- [ ] SDM630 envia dados para banco
- [ ] Tuya envia dados para banco
- [ ] PZEM envia dados para banco
- [ ] Todos os pollers rodando

### **Dashboard**
- [ ] Mostra status de todos os dispositivos
- [ ] Gráficos de consumo em tempo real
- [ ] Alarmes disparando corretamente

---

## 🆘 Troubleshooting

### **Tuya API não retorna dispositivos**
```python
# Verificar região da API
# Testar com diferentes regiões: us, eu, cn, in

# Verificar se dispositivos estão linkados
# No Tuya IoT Platform, ver se aparecem em "Devices"

# Logs de debug
import logging
logging.basicConfig(level=logging.DEBUG)
```

### **USR-G771 não conecta**
```
- Verificar sinal 4G (LEDs do dispositivo)
- Testar APN da operadora
- Verificar se chip tem dados habilitados
- Firewall do servidor pode estar bloqueando
```

### **Port forwarding não funciona**
```
- Testar de FORA da rede (4G do celular)
- Verificar se IP público está correto
- Alguns ISPs bloqueiam portas (CGN/CGNAT)
- Usar DDNS se IP dinâmico
```

---

## 📞 Recursos Adicionais

**Tuya**:
- Documentação oficial: https://developer.tuya.com/
- GitHub tinytuya: https://github.com/jasonacox/tinytuya

**USR-G771**:
- Manual: http://www.usr.cn/Download/663.html
- Support: support@usr.cn

**PZEM-004T**:
- Datasheet Modbus: Registro 0x0000-0x000A
- GitHub: https://github.com/mandulaj/PZEM-004T-v30

---

**Criado em**: 18/10/2025  
**Status**: 📋 Pronto para implementação  
**Próximo**: Obter credenciais Tuya e testar integração

