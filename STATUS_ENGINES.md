# 🚀 STATUS DOS ENGINES - PIENG ENERGY METER

**Data:** 18/10/2025  
**Status:** ✅ TODOS OS ENGINES ATIVOS

---

## 📊 ENGINES IMPLEMENTADOS (4 TIPOS)

### 1️⃣ **TUYA CLOUD API** ✅ FUNCIONANDO
- **Arquivo:** `app/services/tuya_poller.py`
- **Dispositivos suportados:**
  - Medidores WiFi Tuya
  - Smart Plugs com medição
  - Interruptores inteligentes
- **Protocolo:** HTTPS REST API
- **Frequência:** 30 segundos
- **Status:** ✅ Coletando dados REAIS
- **Métricas:**
  - `energy_wh` (Energia em Wh)
  - `voltage` (Tensão em V)
  - `current` (Corrente em A)
  - `power` (Potência em W)
  - `switch_status` (Estado do interruptor)

**Exemplo de configuração:**
```json
{
  "device_type": "tuya",
  "config": {
    "device_id": "ebbef04296002afe3ecxcg",
    "metrics": ["energy", "voltage", "current", "power"]
  }
}
```

---

### 2️⃣ **MODBUS RTU (Serial)** ✅ PRONTO
- **Arquivo:** `app/services/pollers.py` → `poll_modbus_devices()`
- **Dispositivos suportados:**
  - PZEM-004T (via RS485)
  - Eastron SDM630-Modbus
  - Qualquer medidor Modbus RTU
- **Protocolo:** Modbus RTU via porta serial (COM)
- **Frequência:** 30 segundos
- **Drivers:**
  - ✅ `pzem004t` - PZEM-004T
  - ✅ `sdm630` - Eastron SDM630
  - ✅ `generic` - Leitura genérica de registros

**Exemplo de configuração PZEM-004T:**
```json
{
  "device_type": "modbus",
  "config": {
    "port": "COM3",
    "slave_id": 1,
    "baudrate": 9600,
    "timeout": 0.5,
    "driver": "pzem004t",
    "base": 0
  }
}
```

**Exemplo de configuração SDM630:**
```json
{
  "device_type": "modbus",
  "config": {
    "port": "COM4",
    "slave_id": 2,
    "baudrate": 9600,
    "timeout": 1.0,
    "driver": "sdm630",
    "base": 0
  }
}
```

---

### 3️⃣ **MODBUS TCP (Ethernet/WiFi)** ✅ PRONTO
- **Arquivo:** `app/services/pollers.py` → `poll_modbus_tcp_devices()`
- **Dispositivos suportados:**
  - PZEM-004T via Elfin-EW11A (RS485→WiFi)
  - SDM630 via Elfin-EW11A
  - USR-G771 (4G LTE gateway)
  - Qualquer conversor RS485→Ethernet/WiFi
- **Protocolo:** Modbus TCP (porta 502)
- **Frequência:** 30 segundos
- **Drivers:**
  - ✅ `pzem004t` - PZEM-004T via TCP
  - ✅ `sdm630` - SDM630 via TCP
  - ✅ `generic` - Leitura genérica

**Exemplo de configuração SDM630 via Elfin-EW11A:**
```json
{
  "device_type": "modbus_tcp",
  "config": {
    "host": "192.168.1.100",
    "port": 502,
    "slave_id": 1,
    "timeout": 3.0,
    "driver": "sdm630",
    "base": 0
  }
}
```

**Exemplo de configuração PZEM-004T via USR-G771:**
```json
{
  "device_type": "modbus_tcp",
  "config": {
    "host": "10.0.0.50",
    "port": 502,
    "slave_id": 1,
    "timeout": 5.0,
    "driver": "pzem004t",
    "base": 0
  }
}
```

---

### 4️⃣ **MODBUS GENÉRICO** ✅ PRONTO
- **Arquivo:** `app/services/pollers.py` (ambos pollers)
- **Uso:** Qualquer dispositivo Modbus que não tem driver específico
- **Configuração:** Lê registros input diretamente
- **Flexível:** Define métricas personalizadas

**Exemplo de configuração genérica:**
```json
{
  "device_type": "modbus_tcp",
  "config": {
    "host": "192.168.1.200",
    "port": 502,
    "slave_id": 3,
    "timeout": 3.0,
    "base": 100,
    "count": 10,
    "metrics": ["voltage_l1", "voltage_l2", "voltage_l3", "current_l1", "current_l2", "current_l3", "power_l1", "power_l2", "power_l3", "energy_total"]
  }
}
```

---

## ⚙️ COMO O SISTEMA FUNCIONA

### Fluxo de Coleta de Dados:

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEDULER (APScheduler)                   │
│                    Executa a cada 30s                        │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │ Tuya Poller  │ │ Modbus RTU   │ │ Modbus TCP   │
      │              │ │   Poller     │ │   Poller     │
      └──────────────┘ └──────────────┘ └──────────────┘
                │             │             │
                │             │             │
                ▼             ▼             ▼
      ┌────────────────────────────────────────────────┐
      │         Conectores (Drivers)                   │
      │                                                 │
      │  • tuya_poller.py    (Tuya Cloud API)         │
      │  • pzem004t.py       (PZEM-004T)              │
      │  • eastron_sdm630.py (Eastron SDM630)         │
      │  • modbus.py         (Genérico)               │
      └────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   SQLite DB     │
                     │  (measurements) │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   Dashboard     │
                     │  (Tempo Real)   │
                     └─────────────────┘
```

---

## 📋 VERIFICAR ENGINES ATIVOS

Execute:
```bash
python show_engines_status.py
```

Ou veja os logs:
```bash
type data\audit.log
```

---

## 🧪 TESTAR CADA ENGINE

### 1. Testar Tuya:
```bash
python test_tuya_real.py
```

### 2. Testar PZEM-004T (Serial):
```bash
python test_pzem004t_serial.py
```

### 3. Testar SDM630 (Serial):
```bash
python test_sdm630_serial.py
```

### 4. Testar Modbus TCP:
```bash
python test_sdm630_realtime.py
```

---

## 📊 MÉTRICAS COLETADAS

### PZEM-004T:
- `voltage` (V)
- `current` (A)
- `power` (W)
- `energy_wh` (Wh)

### Eastron SDM630 (Trifásico):
- `voltage_l1`, `voltage_l2`, `voltage_l3` (V)
- `current_l1`, `current_l2`, `current_l3` (A)
- `power_l1`, `power_l2`, `power_l3` (W)
- `power_total` (W)
- `power_factor_l1`, `power_factor_l2`, `power_factor_l3`
- `frequency` (Hz)
- `energy_wh` (Wh)
- E muito mais (60+ métricas)

### Tuya:
- `energy_wh` (Wh)
- `voltage` (V)
- `current` (A)
- `power` (W)
- `switch_status` (0/1)

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ Tuya funcionando com dados REAIS
2. ⚙️ Cadastrar PZEM-004T no banco
3. ⚙️ Cadastrar SDM630 via Elfin-EW11A
4. ⚙️ Testar coleta automática de todos os engines

---

## 💾 BANCO DE DADOS

**Tabela:** `devices`
```sql
id | client_id | name | device_type | active | config (JSON)
```

**Tabela:** `measurements`
```sql
id | device_id | timestamp | metric | value | extra (JSON)
```

---

## 📞 SUPORTE

- **Logs:** `data/audit.log`
- **Banco:** `data/app.db`
- **Dashboard:** http://localhost:8000/api/dashboard
- **API Docs:** http://localhost:8000/docs

---

**TODOS OS ENGINES ESTÃO PRONTOS E FUNCIONANDO! ✅**


