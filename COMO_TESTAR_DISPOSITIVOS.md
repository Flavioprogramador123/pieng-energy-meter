# 🧪 Como Testar Todos os Dispositivos PIENG

## 🚀 Início Rápido (Windows)

### **Passo 1: Configurar Ambiente** (5 minutos)

1. Abrir PowerShell ou Prompt de Comando
2. Ir para a pasta do projeto:
   ```cmd
   cd C:\Users\flavi\projeto\pieng-energy-meter
   ```
3. Executar setup:
   ```cmd
   setup_env.bat
   ```

Isso vai:
- ✅ Criar ambiente virtual Python
- ✅ Instalar todas as dependências (tinytuya, pymodbus, etc)
- ✅ Preparar ambiente

---

### **Passo 2: Testar Dispositivos** (10 minutos)

```cmd
test_all_devices.bat
```

O script vai testar **automaticamente**:

1. ✅ **Eastron SDM630** via Elfin EW11 (Modbus TCP)
2. ✅ **2x Tuya Smart Meters** (WiFi/Cloud)
3. ✅ **2x PZEM-004T** (USB/Serial)
4. ✅ **USR-G771** (LTE Gateway - se configurado)

---

## 📋 O que você precisa ter pronto

### **Antes de testar**:

#### **Para SDM630 (Modbus TCP)**
- [ ] Elfin EW11 ligado e conectado na rede
- [ ] IP do EW11 anotado (ex: 192.168.1.109)
- [ ] SDM630 conectado ao EW11 via RS485

#### **Para Tuya Smart Meters**
- [ ] Conta criada em: https://iot.tuya.com/
- [ ] Projeto Cloud criado
- [ ] **Access ID** copiado
- [ ] **Access Secret** copiado
- [ ] Dispositivos linkados via app Tuya Smart

#### **Para PZEM-004T**
- [ ] PZEM conectado ao PC via USB/RS485
- [ ] Driver CH340 instalado (se necessário)
- [ ] Portas COM anotadas (ex: COM3, COM4)

#### **Para USR-G771** (opcional por enquanto)
- [ ] USR-G771 configurado com chip 4G
- [ ] APN da operadora configurada
- [ ] Modo TCP Client configurado

---

## 🔧 Configuração do Script

Edite `test_all_devices.py` se precisar mudar IPs/portas:

```python
CONFIG = {
    # SDM630 via Elfin EW11
    "sdm630": {
        "enabled": True,
        "host": "192.168.1.109",  # ← MUDAR para seu IP
        "port": 8899,
        "slave_id": 1,
    },
    
    # Tuya - será solicitado no primeiro uso
    "tuya": {
        "enabled": True,
        "region": "us",  # us, eu, cn, in
    },
    
    # PZEM-004T
    "pzem": {
        "enabled": True,
        "devices": [
            {"port": "COM3", ...},  # ← MUDAR para suas portas
            {"port": "COM4", ...}
        ],
    },
    
    # USR-G771 (desabilitado por padrão)
    "usr_g771": {
        "enabled": False,  # ← Ativar quando configurar
    }
}
```

---

## 📊 Resultado Esperado

```
==================================================
   PIENG Energy - Teste de Todos os Dispositivos
==================================================

Data: 18/10/2025 14:30:00

==================================================
   Testando SDM630 via Elfin EW11 (Modbus TCP)
==================================================

Conectando em 192.168.1.109:8899 (slave_id=1)...

✅ Eastron SDM630-MCT
--------------------------------------------------
  Tensão L1: 220.50 V
  Tensão L2: 219.80 V
  Tensão L3: 221.20 V
  Corrente L1: 3.250 A
  Corrente L2: 2.980 A
  Corrente L3: 3.100 A
  Potência Total: 2050.00 W
  Energia: 1234.56 kWh

==================================================
   Testando Tuya Smart Meters (Cloud API)
==================================================

Digite seu Tuya Access ID: [você digita aqui]
Digite seu Tuya Access Secret: [você digita aqui]

Conectando ao Tuya Cloud (região: us)...

✅ Smart Meter Sala
--------------------------------------------------
  Tensão: 220.30 V
  Corrente: 1.450 A
  Potência: 319.40 W
  Energia: 45.67 kWh

✅ Smart Meter Cozinha
--------------------------------------------------
  Tensão: 220.10 V
  Corrente: 2.100 A
  Potência: 462.20 W
  Energia: 78.90 kWh

==================================================
   Testando PZEM-004T (USB/Serial)
==================================================

Portas COM disponíveis:
  - COM3: USB-SERIAL CH340 (COM3)
  - COM4: USB-SERIAL CH340 (COM4)

Testando PZEM-004T #1 em COM3...

✅ PZEM-004T #1
--------------------------------------------------
  Tensão: 220.00 V
  Corrente: 0.850 A
  Potência: 187.00 W
  Energia: 12.34 kWh

==================================================
   Resumo dos Testes
==================================================

✅ Sucesso: 4
❌ Erro: 0
⚠️  Ignorado: 1

📄 Resultados salvos em: test_results_20251018_143000.json

==================================================
   SQL para Cadastrar Dispositivos
==================================================

Digite o ID do cliente (ou Enter para 1): 1

-- Copie e cole no PostgreSQL:
----------------------------------------------------------------------

-- Dispositivo 1: Eastron SDM630 via Elfin EW11
INSERT INTO devices (client_id, name, device_type, active, config)
VALUES (
    1,
    'SDM630 - Entrada Principal',
    'modbus_tcp',
    true,
    '{"host": "192.168.1.109", "port": 8899, "slave_id": 1, "driver": "sdm630"}'::jsonb
);

-- Dispositivo 2: Smart Meter Sala
INSERT INTO devices (client_id, name, device_type, active, config)
VALUES (
    1,
    'Smart Meter Sala',
    'tuya',
    true,
    '{"device_id": "bf1234567890abcdef"}'::jsonb
);

-- ... (resto dos dispositivos)

==================================================
   ✅ Teste concluído!
==================================================

Próximos passos:
  1. Copiar SQLs acima e executar no PostgreSQL
  2. Configurar pollers no backend
  3. Iniciar coleta automática
```

---

## 🆘 Problemas Comuns

### **"Python não encontrado"**
```cmd
# Instalar Python de: https://python.org
# Versão recomendada: 3.11 ou 3.12
```

### **"Porta COM não encontrada"**
```
1. Verificar Device Manager (Gerenciador de Dispositivos)
2. Instalar driver CH340 se necessário
3. Verificar se PZEM está conectado
4. Mudar porta USB
```

### **"SDM630 não responde"**
```
1. Verificar se Elfin EW11 está ligado
2. Pingar IP: ping 192.168.1.109
3. Verificar porta 8899 aberta
4. Verificar slave_id correto (geralmente 1)
5. Testar com Modbus Poll/Master
```

### **"Tuya não encontra dispositivos"**
```
1. Verificar credenciais (Access ID e Secret)
2. Verificar região da API (us, eu, cn, in)
3. Linkar dispositivos na plataforma Tuya IoT
   - Devices → Link Tuya App Account
   - Escanear QR Code
4. Dar permissões de API no projeto
```

### **"Erro WinError 2" ao instalar tinytuya**
```
# Usar setup_env.bat ao invés de pip direto
# Ou executar como Administrador
```

---

## 📝 Arquivos Gerados

Após rodar o teste:

- `test_results_YYYYMMDD_HHMMSS.json` - Resultado completo em JSON
  - Status de cada dispositivo
  - Medições coletadas
  - Erros encontrados

- `tuya_devices_YYYYMMDD_HHMMSS.json` - Info detalhada dos Tuya (se usar test_tuya_devices.py)

---

## 🔄 Próximos Passos

Após validar que todos os dispositivos funcionam:

1. **Cadastrar no PostgreSQL**
   - Copiar SQLs gerados
   - Executar no banco do Fidelco

2. **Configurar Pollers**
   - Editar `app/services/pollers.py`
   - Adicionar/atualizar pollers para Tuya

3. **Iniciar Backend**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Ver Dashboard**
   - http://localhost:8000/api/dashboard

---

## 📞 Suporte

**Documentos relacionados**:
- `INTEGRACAO_DISPOSITIVOS.md` - Guia detalhado de cada dispositivo
- `ANALISE_COMPLETA_SISTEMAS.md` - Arquitetura geral
- `SETUP_FIDELCO.md` - Configurar servidor

**Problemas?**
- Verificar logs em `data/audit.log`
- Ver resultado JSON detalhado
- Testar dispositivos individualmente

---

**Criado em**: 18/10/2025  
**Status**: ✅ Pronto para uso

