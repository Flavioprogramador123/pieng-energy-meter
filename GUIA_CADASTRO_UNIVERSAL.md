# 📚 GUIA: SISTEMA UNIVERSAL DE CADASTRO

**PIENG Energy Meter - Cadastre QUALQUER dispositivo!**

---

## 🎯 OBJETIVO

Sistema que permite cadastrar dispositivos **INDEPENDENTE** de:
- ✅ Marca (Tuya, PZEM, Eastron, Schneider, ABB, WEG, etc)
- ✅ Modelo (004T, SDM630, PM2230, etc)
- ✅ Protocolo (Tuya Cloud, Modbus RTU, Modbus TCP, etc)

---

## 🚀 COMO USAR

### **OPÇÃO 1: Cadastro Assistido (RECOMENDADO)**

```bash
python cadastro_universal.py
```

Selecione a opção **1** e escolha um template:

```
1. Medidor Tuya (WiFi)
2. PZEM-004T (Serial RS485)
3. PZEM-004T (WiFi/Ethernet)
4. Eastron SDM630 (Serial RS485)
5. Eastron SDM630 (WiFi/Ethernet)
6. Qualquer Modbus RTU (Serial)
7. Qualquer Modbus TCP (Ethernet/WiFi)
8. Dispositivo Customizado
```

O sistema vai guiar você passo a passo! ✅

---

### **OPÇÃO 2: Cadastro Manual**

Para dispositivos que não tem template:

```bash
python cadastro_universal.py
```

Selecione a opção **2** e configure tudo manualmente:
- Nome do dispositivo
- Tipo (tuya, modbus, modbus_tcp, custom)
- Configuração JSON customizada

**Exemplo:**

```json
{
  "host": "192.168.1.150",
  "port": 502,
  "slave_id": 5,
  "timeout": 3.0,
  "driver": "custom_meter",
  "registers": {
    "voltage": 100,
    "current": 102,
    "power": 104
  }
}
```

---

### **OPÇÃO 3: Importação em Lote**

Cadastre **VÁRIOS dispositivos de uma vez**!

#### **Passo 1: Criar arquivo JSON**

Crie um arquivo `meus_dispositivos.json`:

```json
[
  {
    "name": "Medidor 1",
    "device_type": "modbus_tcp",
    "client_id": 1,
    "config": {
      "host": "192.168.1.100",
      "port": 502,
      "slave_id": 1,
      "driver": "pzem004t"
    }
  },
  {
    "name": "Medidor 2",
    "device_type": "modbus_tcp",
    "client_id": 1,
    "config": {
      "host": "192.168.1.101",
      "port": 502,
      "slave_id": 2,
      "driver": "sdm630"
    }
  }
]
```

#### **Passo 2: Importar**

```bash
python cadastro_universal.py
```

Selecione a opção **3** e forneça o caminho do arquivo.

✅ Todos os dispositivos serão cadastrados automaticamente!

---

## 📋 TEMPLATES INCLUÍDOS

### **1. Tuya Cloud (WiFi)**

```json
{
  "device_type": "tuya",
  "config": {
    "device_id": "ebbef04296002afe3ecxcg",
    "metrics": ["energy", "voltage", "current", "power"]
  }
}
```

**Quando usar:**
- Medidores WiFi Tuya
- Smart Plugs com medição
- Qualquer dispositivo Tuya Cloud

---

### **2. PZEM-004T Serial**

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

**Quando usar:**
- PZEM-004T conectado via RS485 direto no PC
- Conexão serial RS232/RS485

---

### **3. PZEM-004T TCP**

```json
{
  "device_type": "modbus_tcp",
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

**Quando usar:**
- PZEM-004T via Elfin-EW11A (RS485→WiFi)
- PZEM-004T via USR-G771 (RS485→4G)
- Qualquer conversor RS485→Ethernet/WiFi

---

### **4. Eastron SDM630 Serial**

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

**Quando usar:**
- SDM630 conectado via RS485 direto
- Medidores trifásicos Eastron

---

### **5. Eastron SDM630 TCP**

```json
{
  "device_type": "modbus_tcp",
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

**Quando usar:**
- SDM630 via Elfin-EW11A
- SDM630 via USR-G771
- Qualquer conversor RS485→TCP

---

### **6. Modbus Genérico**

```json
{
  "device_type": "modbus_tcp",
  "config": {
    "host": "192.168.1.200",
    "port": 502,
    "slave_id": 1,
    "timeout": 3.0,
    "base": 0,
    "count": 10,
    "metrics": ["voltage", "current", "power", "energy_wh"]
  }
}
```

**Quando usar:**
- Qualquer medidor Modbus que não tem driver específico
- Dispositivos customizados
- Protocolos não-padrão

**Parâmetros:**
- `base`: Endereço inicial dos registros
- `count`: Quantidade de registros a ler
- `metrics`: Nome das métricas (na ordem dos registros)

---

## 🔧 ADICIONAR NOVOS TEMPLATES

Edite `cadastro_universal.py` e adicione ao dicionário `DEVICE_TEMPLATES`:

```python
"meu_dispositivo": {
    "name": "Meu Dispositivo Especial",
    "device_type": "modbus_tcp",
    "protocol": "Modbus TCP",
    "config": {
        "host": "192.168.1.123",
        "port": 502,
        "slave_id": 1,
        "timeout": 3.0,
        "custom_field": "valor_customizado"
    },
    "fields": ["host", "port", "slave_id", "custom_field"]
}
```

---

## 📊 EXEMPLOS PRÁTICOS

### **Exemplo 1: Fábrica com 10 PZEM-004T**

Crie `fabrica_pzems.json`:

```json
[
  {"name": "PZEM - Linha 1", "device_type": "modbus_tcp", "client_id": 1, 
   "config": {"host": "192.168.1.100", "port": 502, "slave_id": 1, "driver": "pzem004t"}},
  
  {"name": "PZEM - Linha 2", "device_type": "modbus_tcp", "client_id": 1, 
   "config": {"host": "192.168.1.101", "port": 502, "slave_id": 1, "driver": "pzem004t"}},
  
  {"name": "PZEM - Linha 3", "device_type": "modbus_tcp", "client_id": 1, 
   "config": {"host": "192.168.1.102", "port": 502, "slave_id": 1, "driver": "pzem004t"}}
]
```

Importe:
```bash
python cadastro_universal.py
# Opção 3 → fabrica_pzems.json
```

✅ 10 dispositivos cadastrados em segundos!

---

### **Exemplo 2: Prédio com Medidores Diversos**

```json
[
  {
    "name": "Entrada Principal - SDM630",
    "device_type": "modbus_tcp",
    "client_id": 1,
    "config": {
      "host": "192.168.1.10",
      "port": 502,
      "slave_id": 1,
      "driver": "sdm630"
    }
  },
  {
    "name": "Sala TI - PZEM",
    "device_type": "modbus_tcp",
    "client_id": 1,
    "config": {
      "host": "192.168.1.20",
      "port": 502,
      "slave_id": 1,
      "driver": "pzem004t"
    }
  },
  {
    "name": "Ar Condicionado - Tuya",
    "device_type": "tuya",
    "client_id": 1,
    "config": {
      "device_id": "abc123def456",
      "metrics": ["energy", "power"]
    }
  }
]
```

---

## 🎯 FLUXO COMPLETO

```
1. PREPARAÇÃO
   ├── Conectar dispositivo físico
   ├── Configurar IP (se TCP) ou porta COM (se serial)
   └── Anotar Slave ID

2. CADASTRO
   ├── Executar: python cadastro_universal.py
   ├── Escolher modo (assistido/manual/lote)
   └── Preencher configurações

3. VERIFICAÇÃO
   ├── Aguardar 30 segundos (poller automático)
   ├── Verificar logs: type data\audit.log
   └── Ver dashboard: http://localhost:8000/api/dashboard

4. VALIDAÇÃO
   ├── Dispositivo aparece no dropdown? ✅
   ├── Dados sendo coletados? ✅
   └── Gráficos funcionando? ✅
```

---

## ⚠️ TROUBLESHOOTING

### **Dispositivo não aparece no dashboard**

1. Verificar se foi cadastrado:
   ```bash
   python show_engines_status.py
   ```

2. Ver se há erros no log:
   ```bash
   type data\audit.log
   ```

3. Testar conexão:
   - TCP: `ping 192.168.1.100`
   - Serial: Verificar porta COM no Gerenciador de Dispositivos

---

### **Erro ao coletar dados**

1. Verificar configuração:
   - IP correto?
   - Slave ID correto?
   - Porta COM correta?
   - Baudrate correto?

2. Testar comunicação:
   - Para Modbus TCP: Usar Modbus Poll
   - Para Modbus RTU: Usar Serial Port Monitor

---

## 📚 DOCUMENTAÇÃO ADICIONAL

- **STATUS_ENGINES.md** - Detalhes técnicos dos engines
- **DIAGRAMA_SISTEMA.md** - Arquitetura visual
- **show_engines_status.py** - Ver status em tempo real

---

## 🎉 RESUMO

✅ **Templates prontos** para dispositivos populares  
✅ **Cadastro manual** para dispositivos customizados  
✅ **Importação em lote** para múltiplos dispositivos  
✅ **Flexível** - Aceita QUALQUER marca/modelo/protocolo  
✅ **Simples** - Interface interativa e guiada  

**NENHUMA LIMITAÇÃO DE MARCA OU MODELO!** 🚀

