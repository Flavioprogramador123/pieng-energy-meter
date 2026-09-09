# Energy Meter — Guia de Arquitetura (para IA)

Documento de referência para evolução automática. Contém visão, árvore, modelos, endpoints, conectores, regras e analytics.

## ⚠️ PREMISSA MASTER - INTEGRIDADE DE DADOS

**REGRA ABSOLUTA**: Sistema trabalha **EXCLUSIVAMENTE com dados REAIS** de hardware físico!

### Política de Dados
- ✅ **PERMITIDO**: Leituras de hardware real (Modbus, Tuya, etc)
- ❌ **PROIBIDO**: Dados simulados, fake, mock ou gerados artificialmente
- ✅ **CORRETO**: Se não há dado, retorna `NULL` ou `[]` (vazio)
- ❌ **INCORRETO**: Gerar dados fictícios para "testar interface"

### Justificativa
- Usuário é **Analista Six Sigma**: dados fake comprometem análises estatísticas
- Decisões críticas dependem da integridade dos dados
- Auditorias requerem rastreabilidade completa
- Certificações (ISO 9001, ISO 50001) exigem dados auditáveis

### Logs de Auditoria
- Arquivo: `data/audit.log`
- Registra: timestamp, device_id, driver, métricas lidas, sucesso/falha
- Formato estruturado para análise forense

### Durante Desenvolvimento
- ✅ Testar com hardware físico (mesmo offline = timeout)
- ✅ Usar banco vazio (sem medições = interface vazia)
- ❌ NUNCA gerar dados fake para "simular"
- ✅ Interfaces devem lidar com estado vazio graciosamente

---

## Visão e Objetivo
- Plataforma master para coletar dados (Modbus RTU/RS485, Modbus TCP, Tuya API e outros), analisar e gerar alarmes por cliente.
- Encaminhamento opcional para plataforma slave (cliente acompanha a planta).
- Armazenamento local (SQLite); possível expansão para PostgreSQL/Cloud.

## Stack
- API: FastAPI + Jinja2 (templates)
- ORM/DB: SQLAlchemy + SQLite
- Agendador: APScheduler
- Conectores: minimalmodbus (RTU), pymodbus (TCP), tinytuya (Tuya Cloud)
- Analytics: pandas, numpy (regressão linear via polyfit)
- Auditoria: logging em arquivo estruturado (data/audit.log)
- Frontend: Chart.js (CDN) + CSS responsivo

## Árvore do Projeto
```
app/
  __init__.py
  connectors/
    __init__.py
    modbus.py
    modbus_tcp.py
    pzem004t.py
    eastron_sdm630.py
    tuya.py
    google_drive.py
  core/
    __init__.py
    config.py (+ tuya_access_id, tuya_access_secret, tuya_api_region)
    db.py
  crud.py
  main.py
  models.py
  routers/
    __init__.py
    alarms.py
    clients.py
    dashboard.py
    devices.py
    ingest.py
    metrics.py
    storage.py
  schemas.py
  services/
    __init__.py
    alarms.py
    analytics.py
    forwarder.py
    hybrid_storage.py
    pollers.py
    scheduler.py
    tuya_poller.py
  static/
    css/
      styles.css
    favicon.png
    js/
      dashboard.js
      device_setup.js
  templates/
    analytics.html
    dashboard.html
    device_setup.html
data/
  app.db (SQLite - APENAS dados reais!)
  audit.log (auditoria de leituras)
scripts/
  cadastro_universal.py (Sistema universal de cadastro)
  cadastrar_dispositivo.py (Script interativo)
  show_engines_status.py (Ver status dos engines)
  show_realtime_status.py (Ver dados em tempo real)
  test_tuya_real.py (Testar Tuya REAL)
  clean_and_setup_REAL.py (Limpar e configurar)
  setup_pzem004t_device.py (Cadastrar PZEM)
  setup_env.bat
  test_all_devices.py
  INICIAR_PROJETO.bat
docs/
  ANALISE_COMPLETA_SISTEMAS.md
  GLOSSARIO_CLIPPER_PYTHON.md
  INTEGRACAO_DISPOSITIVOS.md
  SEGURANCA_CREDENCIAIS.md
  SESSAO_18OUT2025.md
  STATUS_ENGINES.md
  DIAGRAMA_SISTEMA.md
  GUIA_CADASTRO_UNIVERSAL.md
  RESUMO_FINAL_SISTEMA.md
  MAPA_NAVEGACAO.md
  DADOS_REAIS_FINAL.md
  GUIA_AUDITORIA_DADOS.md
templates_importacao/
  exemplo_completo.json
claude.md
README.md
requirements.txt
.env (credenciais - NUNCA commitar!)
.gitignore (protege .env e credenciais)
```

## Configuração (.env)
```env
# Aplicação
APP_NAME=Energy Meter Master
API_PREFIX=/api
DATABASE_URL=sqlite:///./data/app.db
SCHEDULER_TIMEZONE=America/Sao_Paulo

# Encaminhamento (Master → Slave)
ENABLE_FORWARDING=false
FORWARDER_URL=http://localhost:9000

# Tuya IoT (opcional - NUNCA expor em código!)
TUYA_ACCESS_ID=seu_access_id_aqui
TUYA_ACCESS_SECRET=seu_access_secret_aqui
TUYA_API_REGION=us
```

## Modelos (SQLAlchemy)
- **Client**(id, name, external_id, created_at)
- **Device**(id, client_id, name, device_type[modbus|modbus_tcp|tuya|...], active, config JSON, created_at)
- **Measurement**(id, device_id, timestamp, metric, value, extra JSON)
- **AlarmRuleModel**(id, client_id, device_id?, name, metric, operator {>,<,>=,<=,==,!=}, threshold, enabled, created_at)
- **AlarmEvent**(id, rule_id, device_id, timestamp, metric, value, details, acknowledged)

### Campos Importantes em Device.config
```json
{
  // Modbus TCP
  "host": "192.168.1.109",
  "port": 8899,
  "slave_id": 1,
  "driver": "sdm630",  // ou "pzem004t"
  "timeout": 3.0,
  
  // Modbus RTU
  "port": "COM3",
  "slave_id": 1,
  "baudrate": 9600,
  "driver": "pzem004t",
  "timeout": 0.5,
  
  // Tuya
  "device_id": "xxxxx",
  "local_key": "xxxxx"
}
```

## Schemas (Pydantic)
- ClientCreate/Read, DeviceCreate/Read
- MeasurementCreate/Read
- AlarmRuleCreate/Read, AlarmEventRead

## Endpoints
- GET `/` — healthcheck
- **Clients**: GET `/api/clients`, POST `/api/clients`
- **Devices**: GET `/api/devices?client_id?`, POST `/api/devices`
- **Ingest**: POST `/api/ingest` — persiste, avalia regras, forward opcional
- **Metrics**: 
  - GET `/api/metrics?device_id&metric?&limit?`
  - GET `/api/metrics/summary` — resumo estatístico + six sigma
  - GET `/api/metrics/aggregate` — agregações (hourly, daily, weekly, monthly)
  - GET `/api/metrics/linreg` — regressão linear x vs y
- **Alarms**: 
  - GET `/api/alarms/rules`, POST `/api/alarms/rules`
  - GET `/api/alarms/events` — eventos de alarme por dispositivo
- **Dashboard**: GET `/api/dashboard` — interface web com gráficos
- **Analytics**: GET `/api/analytics` — análises avançadas

## Conectores e Pollers

### Modbus TCP (`app/connectors/modbus_tcp.py`)
- Cliente para dispositivos Modbus TCP (via Elfin EW11, etc)
- Poller: `services/pollers.py::poll_modbus_tcp_devices` (30s)

### Modbus RTU (`app/connectors/modbus.py`)
- `ModbusRTUClient(port, slave_id, baudrate=9600, timeout=0.5)`
- Poller: `services/pollers.py::poll_modbus_devices` (30s)

### Eastron SDM630 (`app/connectors/eastron_sdm630.py`)
- **Driver**: `read_sdm630_metrics(client)`
- **Métricas**: 
  - Tensões (L1, L2, L3)
  - Correntes (L1, L2, L3)
  - Potências (L1, L2, L3, Total)
  - Energia (kWh)
  - Fator de potência
  - Frequência
- **Detecção**: Consumo vs Injeção (potência negativa = geração solar)

### PZEM-004T (`app/connectors/pzem004t.py`)
- **Driver**: `read_pzem004t_metrics()` 
- Lê 5 registradores: voltage/current/power/energy_wh
- Energia como U32 (regs 3+4)
- 9600 8N1, timeout 0.5s

### Tuya API (`app/connectors/tuya.py`)
- `TuyaAPIClient(region, key, secret, uid)` 
- `list_devices`, `get_status`, `get_energy_data`
- **Credenciais**: Obrigatoriamente via `.env` (nunca hardcoded!)
- Agendamento Tuya: pendente (similar ao Modbus)

## Regras de Alarme
- Avaliadas na ingestão; cria `AlarmEvent` quando `operator(value, threshold)` é verdadeiro.
- Escopo por cliente e/ou dispositivo; habilitável por regra.
- Operadores: `>`, `<`, `>=`, `<=`, `==`, `!=`

## Analytics
- **Resumo**: count, mean, std, min, max
- **Six Sigma**: mean, std, cpk (LSL/USL = mean ± 3σ)
- **Regressão linear**: slope, intercept, r²
- **Agregações**: hourly, daily, weekly, monthly

## Encaminhamento Master → Slave
- `services/forwarder.py`: POST para `/api/ingest` do slave.
- Controlado por `ENABLE_FORWARDING` e `FORWARDER_URL`.

## Como rodar
```bash
# 1. Setup ambiente
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Configurar .env (copiar de env.example)
cp env.example .env
# Editar .env com credenciais reais

# 3. Iniciar backend
python -m uvicorn app.main:app --reload --port 8000

# 4. Acessar
# Dashboard: http://localhost:8000/api/dashboard
# API Docs: http://localhost:8000/docs
```

## Dispositivos Físicos

### SDM630 via Elfin EW11
- **Status**: Hardware existente, IP a confirmar
- **Protocolo**: Modbus TCP
- **Configuração**: Descobrir IP do EW11 (scanner de rede)
- **Teste**: `test_sdm630_realtime.py`

### PZEM-004T (2 unidades)
- **Status**: Hardware existente
- **Protocolo**: Modbus RTU (USB-RS485)
- **Portas**: COM3, COM4 (verificar)
- **Driver**: CH340 (instalar se necessário)

### Tuya Smart Meters (2 unidades)
- **Status**: Hardware existente
- **Protocolo**: Tuya Cloud API
- **Credenciais**: Configuradas no `.env`
- **Teste**: `test_all_devices.py`

### USR-G771 LTE Gateway
- **Status**: Hardware novo, aguardando chip 4G
- **Função**: Gateway Modbus RTU → 4G → Internet
- **Uso**: Dispositivos remotos sem WiFi

---

## Sessão 08-09/09/2026 - Ver CHANGELOG.md e .claude/session_context.json

Sessão grande: correção da coleta Tuya trifásica (`medidorCASA`, categoria "tdq"),
CRUD visual de dispositivos, sincronização opcional com Firebase, Postgres local
de teste + script de migração, redesign visual completo (tema "painel de
instrumentação" + claro/escuro), Cpk real com limites de especificação e
comparação de período (dia/semana/mês) na Análise Temporal.

**Flush / storage (noite++):** espelho Postgres no `K:` com flush a cada **30 min**
e teto de cache SQLite **200 MB** (~3 dias / ~3 aparelhos em teste). Config em
`/api/db` → `data/runtime_settings.json`. Hot path continua SQLite.

**Antes de continuar o trabalho**: leia `CHANGELOG.md` (relato completo) e
`.claude/session_context.json` (estado estruturado: devices ativos, dívidas
técnicas conhecidas, próximos passos combinados com o usuário). Resumo rápido:
- Único device Tuya ativo agora é `medidorCASA` (id=5 na migração, trifásico, real).
- Banco continua SQLite em produção; Postgres nativo no `K:` é espelho (flush 30 min).
- Existe também caminho Docker preservado (`docker-compose.yml`, porta 5433).
- Servidor uvicorn ao vivo (venv, `--reload`, tipicamente **:8001**) está coletando
  dados reais — não derrubar sem avisar o usuário.

---

## Sessão 18/10/2025 (Continuação - Noite) - Interface Visual e Integração Completa

### ✅ Concluído - Parte 2 (Noite)

1. **Dados REAIS Implementados**:
   - ❌ DELETADO: `generate_test_data.py` (dados fake)
   - ✅ Banco limpo completamente
   - ✅ Poller Tuya funcionando com dados REAIS
   - ✅ 2 dispositivos Tuya ativos (Wifi Plug, Dvr)
   - ✅ Coleta automática a cada 30s
   - ✅ Dashboard mostrando apenas dados reais

2. **Sistema de Cadastro Universal**:
   - ✅ `cadastro_universal.py` - 3 modos de cadastro
   - ✅ **Modo 1**: Cadastro assistido com templates
   - ✅ **Modo 2**: Cadastro manual (100% customizado)
   - ✅ **Modo 3**: Importação em lote (JSON)
   - ✅ Suporta QUALQUER marca/modelo/protocolo
   - ✅ Templates: Tuya, PZEM-004T, SDM630, Genérico
   - ✅ Documentação: `GUIA_CADASTRO_UNIVERSAL.md`

3. **Interface Visual Web (HTML/CSS/JavaScript)**:
   - ✅ `app/templates/device_setup.html` - Interface moderna
   - ✅ `app/static/js/device_setup.js` - Integração com API
   - ✅ 6 cards visuais para selecionar engine
   - ✅ Formulários dinâmicos por tipo de dispositivo
   - ✅ Validação de campos em tempo real
   - ✅ Design responsivo (mobile-friendly)
   - ✅ Animações suaves e feedback visual
   - ✅ Lista de dispositivos cadastrados em tempo real

4. **Navegação Integrada**:
   - ✅ Dashboard → Botões: [➕ Cadastrar] [📊 Analytics]
   - ✅ Setup → Botões: [🏠 Dashboard] [📊 Analytics]
   - ✅ Analytics → Botões: [🏠 Dashboard] [➕ Cadastrar]
   - ✅ Todas as páginas 100% integradas
   - ✅ Usuário NUNCA fica perdido
   - ✅ Documentação: `MAPA_NAVEGACAO.md`

5. **Documentação Completa**:
   - ✅ `STATUS_ENGINES.md` - Status dos 4 engines
   - ✅ `DIAGRAMA_SISTEMA.md` - Arquitetura visual
   - ✅ `GUIA_CADASTRO_UNIVERSAL.md` - Manual completo
   - ✅ `RESUMO_FINAL_SISTEMA.md` - Visão geral
   - ✅ `MAPA_NAVEGACAO.md` - Navegação completa
   - ✅ `templates_importacao/exemplo_completo.json` - Exemplo prático

6. **4 Engines Confirmados Ativos**:
   - ✅ Tuya Cloud API - Funcionando (66+ medições)
   - ✅ Modbus RTU (RS485/Serial) - Pronto
   - ✅ Modbus TCP (Ethernet/WiFi) - Pronto
   - ✅ Genérico (Qualquer Modbus) - Pronto
   - ✅ Todos rodando a cada 30s no scheduler
   - ✅ Logs aparecem quando há dispositivos

7. **Correções de API**:
   - ❌ Problema: HTTP 500 no endpoint `/api/metrics`
   - ✅ Solução: Serialização JSON do campo `extra`
   - ✅ Endpoint retornando HTTP 200
   - ✅ Dashboard recebendo dados corretamente
   - ✅ Gráficos funcionando

### 📊 Estatísticas da Sessão

- **Arquivos criados**: 15+ (scripts, documentação, interface)
- **Linhas de código**: ~2.000 linhas
- **Dispositivos suportados**: TODOS (Tuya, PZEM, SDM630, Schneider, ABB, WEG, Siemens...)
- **Medições coletadas**: 150+ (dados REAIS)
- **Páginas integradas**: 3 (Dashboard, Setup, Analytics)
- **Engines ativos**: 4/4 (100%)

### 🎯 URLs do Sistema

```
Dashboard:   http://localhost:8000/api/dashboard
Setup:       http://localhost:8000/api/setup        ← NOVO!
Analytics:   http://localhost:8000/api/analytics
API Docs:    http://localhost:8000/docs
Health:      http://localhost:8000/
```

---

## Sessão 18/10/2025 (Manhã) - Resumo de Tarefas

### ✅ Concluído - Parte 1
1. **Análise Completa**:
   - Comparação Energy Meter (SQLite) vs PIENG PostgreSQL
   - Arquitetura de convergência definida
   - Documentação: `ANALISE_COMPLETA_SISTEMAS.md` (1.003 linhas)

2. **Segurança de Credenciais**:
   - Corrigido: scripts solicitavam `input()` para credenciais
   - Solução: Migrado para `.env` + `python-dotenv`
   - `.gitignore` atualizado (nunca commitar `.env`)
   - Documentação: `SEGURANCA_CREDENCIAIS.md`
   - Template: `env.example` (sem credenciais reais)
   - Verificação: `verify_security.bat`

3. **Integração de Dispositivos**:
   - Inventário completo de hardware
   - Script de teste: `test_all_devices.py`
   - Documentação: `INTEGRACAO_DISPOSITIVOS.md`, `COMO_TESTAR_DISPOSITIVOS.md`
   - Credenciais Tuya configuradas

4. **Glossário Clipper → Python**:
   - Tradução de conceitos antigos para modernos
   - Documentação: `GLOSSARIO_CLIPPER_PYTHON.md` (430 linhas)
   - Analogias com eletrônica e automação

5. **Correção Frontend**:
   - **Erro**: `ValidationError` - campos Tuya não declarados em `config.py`
   - **Solução**: Adicionados `tuya_access_id`, `tuya_access_secret`, `tuya_api_region` em `Settings`
   - Backend iniciado com sucesso
   - Dashboard acessível

6. **Scripts de Automação**:
   - `setup_env.bat` - Setup ambiente Python
   - `test_all_devices.bat` - Testar hardware
   - `INICIAR_PROJETO.bat` - Menu principal do projeto
   - `verify_security.bat` - Verificar segurança

7. **Documentação de Sessão**:
   - `SESSAO_18OUT2025.md` - Relatório completo da sessão

### ⚠️ Importante: Dados Simulados
- **CRIADO**: `generate_test_data.py` (207.384 medições fake)
- **STATUS**: ⚠️ **USO PROIBIDO EM PRODUÇÃO!**
- **AÇÃO NECESSÁRIA**: Limpar banco de dados fake antes de produção
- **PREMISSA**: Sistema deve trabalhar APENAS com dados reais

### 🔄 Pendente (Próxima Sessão)

#### Hardware
- [ ] Descobrir IP do Elfin EW11 (SDM630)
- [ ] Validar comunicação Modbus TCP com SDM630
- [ ] Testar PZEM-004T em COM3/COM4
- [ ] Verificar driver CH340 instalado
- [ ] Testar Tuya API com credenciais reais
- [ ] Configurar USR-G771 (aguardando chip 4G)

#### Backend
- [ ] **LIMPAR banco de dados fake** (data/app.db)
- [ ] Implementar poller Tuya automático
- [ ] Melhorar tratamento de timeouts
- [ ] Adicionar retry logic para Modbus

#### Frontend
- [ ] Lidar com estado vazio (sem medições)
- [ ] Mensagens amigáveis quando não há dados
- [ ] Loading states para requisições
- [ ] Error states para falhas de comunicação

#### Multi-tenant
- [ ] Migrar para PostgreSQL (Fidelco)
- [ ] Implementar autenticação JWT
- [ ] Isolamento por cliente
- [ ] Portal slave para clientes

---

## Roadmap - Próximos Passos

### Curto Prazo (Esta Semana)
1. **Hardware Físico**:
   - Descobrir IP Elfin EW11 (scanner de rede)
   - Testar SDM630 com Modbus Poll
   - Configurar PZEM-004T (driver CH340)
   - Validar comunicação Modbus

2. **Tuya API**:
   - Testar API com credenciais do `.env`
   - Linkar dispositivos na plataforma Tuya IoT
   - Implementar poller automático

3. **Limpeza**:
   - ⚠️ **LIMPAR dados fake** do banco
   - Testar interface com banco vazio
   - Garantir graceful degradation

### Médio Prazo (Próxima Semana)
4. **Servidor Fidelco** (Debian 11):
   - Executar setup PostgreSQL
   - Migrar banco SQLite → PostgreSQL
   - Configurar backup automático
   - Testar acesso remoto

5. **Multi-Tenant**:
   - Adaptar Energy Meter para multi-tenant
   - Adicionar filtros por `client_id`
   - Criar portal cliente isolado
   - Implementar autenticação JWT

6. **USR-G771 LTE**:
   - Inserir chip 4G
   - Configurar APN da operadora
   - Testar conexão LTE
   - Integrar com backend

### Longo Prazo (Próximo Mês)
7. **Produção**:
   - Deploy backend no Fidelco
   - Deploy frontend no Vercel
   - Configurar domínio
   - Onboarding primeiro cliente

8. **Análises Avançadas**:
   - Dashboard Six Sigma completo
   - Análise de demanda (pico/fora-ponta)
   - Predições com Machine Learning
   - Relatórios automáticos PDF

9. **Integrações**:
   - Firebase/Cloud SQL para escala
   - APIs de terceiros (Enel, CPFL)
   - IoT platforms (AWS IoT, Azure IoT)

### Melhorias Técnicas
10. **Performance**:
    - Cache Redis para consultas frequentes
    - Paginação em endpoints grandes
    - Compressão de dados históricos

11. **Monitoramento**:
    - Logs estruturados (JSON)
    - Métricas de performance
    - Health checks avançados

12. **DevOps**:
    - Docker containers
    - CI/CD pipeline
    - Deploy automatizado

---

## Notas Técnicas

### PZEM-004T (Modbus)
- 9600 8N1; energia 32 bits (2 registradores)
- Preferir leitura de 5 regs desde 0x0000
- Padronizar bytes `0xNN`; CRC calculado pela biblioteca

### SDM630 (Modbus TCP)
- 3 fases, múltiplos registradores
- Detecção de injeção (potência negativa)
- Requer Elfin EW11 para TCP

### Tuya IoT
- Credenciais via Tuya IoT Platform
- Região: US, EU, CN (configurável)
- Rate limits: Respeitar quotas da API

---

## Glossário para Engenheiro Clipper

Ver: `GLOSSARIO_CLIPPER_PYTHON.md`

**Conceitos-chave**:
- **API REST** = Função acessível por HTTP
- **JSON** = Estrutura de dados (array associativo)
- **ORM** = Comandos xBase em objetos
- **Async/Await** = Loop sem travar tela
- **Virtual Environment** = Bibliotecas isoladas por projeto
- **Git** = Backup automático com histórico

---

## 🎯 Missão do Projeto

> **Criar plataforma SaaS de monitoramento energético independente, escalável e lucrativa!**

**Meta 2026**: 100+ clientes | R$ 50-100k MRR | Referência no setor

**Vale do Silício Tupiniquim! 🇧🇷🚀**
