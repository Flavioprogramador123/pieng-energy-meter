# 📊 DIAGRAMA DO SISTEMA - PIENG ENERGY METER

---

## 🎯 SITUAÇÃO ATUAL

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🚀 4 ENGINES IMPLEMENTADOS                            │
│                         (CÓDIGO PRONTO)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │   1. Tuya Cloud   │  │  2. Modbus RTU    │  │  3. Modbus TCP    │
    │   ✅ FUNCIONANDO  │  │  ✅ PRONTO        │  │  ✅ PRONTO        │
    └───────────────────┘  └───────────────────┘  └───────────────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │  4. Genérico      │
                          │  ✅ PRONTO        │
                          └───────────────────┘

════════════════════════════════════════════════════════════════════════════

                        📱 DISPOSITIVOS CADASTRADOS
                            (NO BANCO DE DADOS)

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │   Wifi Plug       │  │   Dvr             │  │   PZEM-004T       │
    │   ✅ CADASTRADO   │  │   ✅ CADASTRADO   │  │   ❌ FALTANDO     │
    │   (Tuya)          │  │   (Tuya)          │  │   (Modbus)        │
    └───────────────────┘  └───────────────────┘  └───────────────────┘

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │   SDM630          │  │   USR-G771        │  │   Outros...       │
    │   ❌ FALTANDO     │  │   ❌ FALTANDO     │  │   ❌ FALTANDO     │
    │   (Modbus)        │  │   (Gateway)       │  │                   │
    └───────────────────┘  └───────────────────┘  └───────────────────┘

════════════════════════════════════════════════════════════════════════════

                          🌐 DASHBOARD (Frontend)
                      
    ┌─────────────────────────────────────────────────────────────────┐
    │  Dispositivo:  [Dropdown]                                       │
    │                                                                  │
    │  📋 SOMENTE MOSTRA OS DISPOSITIVOS CADASTRADOS:                 │
    │                                                                  │
    │  ┌────────────────────────────────────────────┐                │
    │  │ ▼ Selecione um dispositivo                 │                │
    │  ├────────────────────────────────────────────┤                │
    │  │   Wifi Plug - Medidor Real (tuya)          │ ← ✅ Aparece  │
    │  │   Dvr - Interruptor Real (tuya)            │ ← ✅ Aparece  │
    │  └────────────────────────────────────────────┘                │
    │                                                                  │
    │  ⚠️  PZEM-004T não aparece → Não está cadastrado               │
    │  ⚠️  SDM630 não aparece → Não está cadastrado                  │
    │                                                                  │
    └─────────────────────────────────────────────────────────────────┘

```

---

## 🔄 FLUXO DO SISTEMA

```
    HARDWARE FÍSICO              BANCO DE DADOS           DASHBOARD
    ===============              ==============           =========

┌──────────────────┐                                  
│  Wifi Plug       │──┐                               
│  (Tuya Cloud)    │  │                               
└──────────────────┘  │                               
                      │                               
┌──────────────────┐  │         ┌─────────────┐      ┌──────────────┐
│  Dvr             │──┼────────→│  CADASTRADO │─────→│   APARECE    │
│  (Tuya Cloud)    │  │         │  no banco   │      │ no dropdown  │
└──────────────────┘  │         └─────────────┘      └──────────────┘
                      │                               
┌──────────────────┐  │                               
│  PZEM-004T       │──┘                               
│  (Modbus RTU)    │                                  
└──────────────────┘                                  
         ↓                                            
    ❌ NÃO cadastrado  →  ❌ NÃO aparece              

┌──────────────────┐                                  
│  SDM630          │                                  
│  (Modbus TCP)    │                                  
└──────────────────┘                                  
         ↓                                            
    ❌ NÃO cadastrado  →  ❌ NÃO aparece              
```

---

## 🎯 PARA FAZER APARECER MAIS DISPOSITIVOS

### **PASSO 1: Conecte o hardware**
- ✅ Wifi Plug → Já conectado na rede WiFi
- ✅ Dvr → Já conectado na rede WiFi
- ⚠️  PZEM-004T → Conecte via RS485 ou conversor WiFi
- ⚠️  SDM630 → Conecte via RS485 ou Elfin-EW11A

### **PASSO 2: Execute o script de cadastro**

```bash
# Opção 1: Script interativo (RECOMENDADO)
python cadastrar_dispositivo.py

# Opção 2: Scripts específicos
python setup_pzem004t_device.py
python setup_sdm630_device.py
```

### **PASSO 3: Aguarde 30 segundos**
- O poller vai detectar o novo dispositivo
- Vai começar a coletar dados automaticamente

### **PASSO 4: Atualize o dashboard**
- Pressione F5
- O novo dispositivo vai aparecer no dropdown! ✅

---

## 📋 EXEMPLO DE CADASTRO VIA API

### Cadastrar PZEM-004T (Modbus TCP):

```bash
POST http://localhost:8000/api/devices

{
  "client_id": 1,
  "name": "PZEM-004T - Escritório",
  "device_type": "modbus_tcp",
  "active": true,
  "config": {
    "host": "192.168.1.100",
    "port": 502,
    "slave_id": 1,
    "timeout": 3.0,
    "driver": "pzem004t",
    "base": 0
  }
}
```

### Cadastrar SDM630 (Modbus TCP via Elfin-EW11A):

```bash
POST http://localhost:8000/api/devices

{
  "client_id": 1,
  "name": "SDM630 - Entrada Principal",
  "device_type": "modbus_tcp",
  "active": true,
  "config": {
    "host": "192.168.1.101",
    "port": 502,
    "slave_id": 2,
    "timeout": 3.0,
    "driver": "sdm630",
    "base": 0
  }
}
```

---

## ✅ RESUMO

| COMPONENTE | STATUS | QTD |
|------------|--------|-----|
| **Engines Implementados** | ✅ 4/4 | 100% |
| **Dispositivos Cadastrados** | ⚠️ 2/? | Depende de você |
| **Tuya funcionando** | ✅ Sim | 66 medições |
| **Modbus aguardando** | ⏳ Sim | Cadastro pendente |

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ Engines → Todos implementados
2. ⚠️  **Você precisa:** Cadastrar seus dispositivos físicos
3. ⏳ Sistema vai coletar dados automaticamente
4. ✅ Dashboard vai mostrar todos os dispositivos

---

**CÓDIGO ESTÁ PRONTO! FALTA CADASTRAR OS EQUIPAMENTOS QUE VOCÊ TEM! 🚀**


