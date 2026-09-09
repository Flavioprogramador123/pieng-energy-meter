# 📋 Guia de Auditoria de Dados - Tuya vs Sistema

**Data**: 18/10/2025  
**Objetivo**: Verificar integridade entre dados Tuya Platform e API local

---

## 🌐 Interfaces Abertas

1. **Tuya Platform**: https://us.platform.tuya.com/cloud/device/list
   - Projeto: PIENG Energy Monitor
   - Região: Western America Data Center
   
2. **Dashboard Local**: http://localhost:8000/api/dashboard
   - Backend: FastAPI
   - Banco: SQLite (vazio aguardando coleta)
   
3. **API Docs**: http://localhost:8000/docs
   - Swagger interativo
   - Testes de endpoints

---

## 📊 Dispositivos a Auditar

### 1. **Wifi Plug** (Medidor de Energia)

**Tuya Platform**:
```
Device ID: ebbef04296002afe3ecxcg
Nome: Wifi Plug
Categoria: cz (medidor)
```

**Dados Coletados pela API** (arquivo: `meter_ebbef04296002afe3ecxcg_FORCED_READ.json`):
```json
{
  "switch_1": true,           // Ligado
  "add_ele": 182,             // 182 kWh
  "cur_current": 0,           // 0 A
  "cur_power": 0,             // 0 W
  "cur_voltage": 1610,        // 161.0 V (1610 mV)
  "voltage_coe": 642,
  "electric_coe": 29558,
  "power_coe": 17318,
  "electricity_coe": 2410,
  "fault": 0,
  "relay_status": "last"
}
```

**Checklist de Auditoria**:
- [ ] Energia acumulada na plataforma = 182 kWh?
- [ ] Tensão atual mostrada na plataforma ≈ 161V?
- [ ] Corrente atual = 0A (sem carga)?
- [ ] Potência atual = 0W (sem carga)?
- [ ] Status do switch = LIGADO?

---

### 2. **Dvr** (Interruptor)

**Tuya Platform**:
```
Device ID: 73634132ec94cb8039a6
Nome: Dvr
Categoria: cz
```

**Dados Coletados pela API** (arquivo: `meter_73634132ec94cb8039a6_FORCED_READ.json`):
```json
{
  "switch_1": true,           // Ligado
  "countdown_1": 0,           // Sem temporizador
  "relay_status": "power_on"  // Relé ativado
}
```

**Checklist de Auditoria**:
- [ ] Status na plataforma = LIGADO (ON)?
- [ ] Sem temporizador ativo?
- [ ] Relé em estado "power_on"?

---

### 3. **WIFI dual meter** (OFFLINE)

**Tuya Platform**:
```
Device ID: eb12907d3f923984f1wntb
Nome: WIFI dual meter
Categoria: cz (medidor duplo)
Status: OFFLINE
```

**Dados Coletados pela API**:
```
⚠️  Resposta vazia (dispositivo realmente offline)
```

**Checklist de Auditoria**:
- [ ] Confirmar status OFFLINE na plataforma?
- [ ] Ver quando foi a última comunicação?
- [ ] Verificar histórico de dados (se disponível)?

---

## 🔍 Procedimento de Auditoria

### Passo 1: Verificar Status Online/Offline

Na **Tuya Platform**:
1. Acessar lista de dispositivos
2. Verificar ícone de status (🟢 Online / 🔴 Offline)
3. Comparar com dados coletados pela API

**Resultado Esperado**: 
- Wifi Plug e Dvr podem aparecer como OFFLINE na API mas ter dados
- Isso é normal (delay de sincronização)

---

### Passo 2: Comparar Valores de Energia (Wifi Plug)

Na **Tuya Platform** (detalhes do Wifi Plug):
1. Clicar no dispositivo "Wifi Plug"
2. Ir em "Device Logs" ou "Data Points"
3. Procurar campo "add_ele" ou "Energia"
4. Verificar se valor = **182 kWh** (ou próximo)

**Tolerância**: ±1 kWh (devido ao horário da leitura)

---

### Passo 3: Verificar Tensão e Corrente

Na **Tuya Platform**:
1. Procurar campos:
   - `cur_voltage` → Deve mostrar ≈161V
   - `cur_current` → Deve mostrar ≈0A
   - `cur_power` → Deve mostrar ≈0W

**Observação**: Se houver carga conectada, valores mudam!

---

### Passo 4: Verificar Timestamps

**Importante para auditoria Six Sigma**:

1. Anotar horário da leitura na plataforma Tuya
2. Comparar com timestamp dos arquivos JSON locais:
   - `meter_ebbef04296002afe3ecxcg_FORCED_READ.json`
   - `forced_read_summary_20251018_212825.json`
3. Verificar diferença de tempo

**Esperado**: Diferença < 10 minutos

---

### Passo 5: Teste de Controle (Dvr)

**Teste em tempo real**:

1. Na **Tuya Platform**:
   - Clicar em "Dvr"
   - Clicar em "Control" ou botão ON/OFF
   - Desligar o dispositivo

2. Aguardar 10 segundos

3. Executar script de leitura:
   ```bash
   python force_read_meters.py
   ```

4. Verificar se `switch_1` mudou para `false`

**Objetivo**: Confirmar que API reflete mudanças em tempo real

---

## 📊 Relatório de Auditoria

### Dispositivos Auditados

| Dispositivo | Tuya Platform | API Local | Status | Observações |
|-------------|---------------|-----------|--------|-------------|
| Wifi Plug | 🟢 / 🔴 | ✅ Dados OK | ⬜ | Energia: ___ kWh |
| Dvr | 🟢 / 🔴 | ✅ Dados OK | ⬜ | Switch: ___ |
| WIFI dual meter | 🔴 OFFLINE | ❌ Sem dados | ⬜ | Aguardando ligar |

**Legenda**:
- ✅ = Dados consistentes
- ⚠️ = Dados com diferença tolerável
- ❌ = Dados inconsistentes
- ⬜ = Não auditado

---

### Divergências Encontradas

**Se encontrar divergências, anotar aqui**:

1. Campo: ____________
   - Tuya Platform: ____________
   - API Local: ____________
   - Diferença: ____________%
   - Causa provável: ____________

2. (adicionar mais conforme necessário)

---

## 🎯 Critérios de Aprovação

### ✅ Auditoria APROVADA se:

1. **Energia acumulada**: Diferença < 2%
2. **Tensão**: Diferença < 5V
3. **Corrente**: Diferença < 0.5A
4. **Potência**: Diferença < 50W
5. **Status switch**: 100% consistente
6. **Timestamps**: Diferença < 10 minutos

### ❌ Auditoria REPROVADA se:

1. Energia com diferença > 5%
2. Status switch inconsistente
3. Valores impossíveis (ex: tensão = 0V com potência > 0W)
4. Timestamps com diferença > 30 minutos
5. Dados claramente incorretos

---

## 📝 Próximos Passos Após Auditoria

### Se APROVADA ✅:
1. [ ] Implementar poller Tuya automático
2. [ ] Configurar coleta a cada 30 segundos
3. [ ] Monitorar por 24 horas
4. [ ] Validar integridade contínua

### Se REPROVADA ❌:
1. [ ] Identificar causa da divergência
2. [ ] Verificar configuração de coeficientes
3. [ ] Testar com outro dispositivo
4. [ ] Contatar suporte Tuya se necessário

---

## 🔧 Ferramentas para Auditoria

### Scripts Disponíveis:

```bash
# Forçar leitura de medidores
python force_read_meters.py

# Testar dispositivo específico
python test_device_online.py

# Monitorar até ficar online
python monitor_tuya_online.py

# Testar múltiplos dispositivos
python test_multiple_online.py
```

### Arquivos JSON para Comparação:

- `meter_ebbef04296002afe3ecxcg_FORCED_READ.json`
- `meter_73634132ec94cb8039a6_FORCED_READ.json`
- `forced_read_summary_20251018_212825.json`
- `tuya_devices_REAL_20251018_212245.json`

---

## 📞 Referências

- **Tuya Platform**: https://us.platform.tuya.com/
- **Tuya API Docs**: https://developer.tuya.com/
- **Dashboard Local**: http://localhost:8000/api/dashboard
- **API Swagger**: http://localhost:8000/docs

---

## ✍️ Assinatura do Auditor

**Nome**: ____________________________  
**Data**: 18/10/2025  
**Hora**: _______  
**Resultado**: ⬜ APROVADO  ⬜ REPROVADO  ⬜ PENDENTE  

**Observações**:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

**Auditoria conforme ISO 9001 e Six Sigma**  
**Rastreabilidade completa garantida** ✅


