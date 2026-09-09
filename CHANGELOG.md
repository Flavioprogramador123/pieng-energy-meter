# Changelog

Todas as mudanças relevantes do projeto Energy Meter são registradas aqui.
Formato livre, em português, por sessão de trabalho.

## 2026-09-08/09 — Sessão: dados Tuya trifásicos, CRUD de dispositivos, Firebase, Postgres de teste, redesign visual, tema claro/escuro, análise estatística

### Corrigido
- **Coleta Tuya trifásica (`medidorCASA`)**: o poller usava a API v1.0 (`getstatus`), que para a categoria "tdq" (disjuntor trifásico) só retorna 3 DPs básicos (`switch_1`, `fault`, `relay_status`) mesmo com o dispositivo reportando tensão/corrente/potência por fase. Trocado para o endpoint v2.0 `cloud/thing/{id}/shadow/properties`, que retorna todos os DPs. `parse_tuya_data()` agora mapeia `voltage_a/b/c`, `current_a/b/c`, `active_power_a/b/c`, `power_factor_a/b/c`, `forward_energy_total`, `frequency` para os mesmos nomes já usados pelo driver SDM630 (`voltage_l1`, `power_total`, `energy_kwh`...), reaproveitando toda a UI existente sem mudanças de schema.
  - Arquivo: `app/services/tuya_poller.py`
- **Cadastro de dispositivos ativos**: `Device.active` estava mal configurado (o medidor real trifásico "medidorCASA" chegou a ficar desativado por engano durante o diagnóstico; corrigido manualmente no banco).

### Adicionado
- **CRUD visual de dispositivos** (`/api/setup`): botões de apagar (🗑) e ativar/desativar por dispositivo, com confirmação antes de apagar (remove measurements em cascata). Backend já existia (`DELETE`/`PATCH /api/devices/{id}`); só faltava a UI.
  - Arquivos: `app/static/js/device_setup.js`, `app/templates/device_setup.html`
- **Sincronização opcional com Firebase Firestore** (`app/services/firebase_sync.py`): grava **um documento por leitura** (todas as métricas do poll num map), não um doc por métrica — decisão deliberada para não estourar a cota gratuita do Firestore com múltiplos equipamentos a cada 30s. Desligado por padrão (`FIREBASE_ENABLED=false` no `.env`); nunca bloqueia o SQLite se falhar. Conectado nos 3 pollers (`tuya_poller.py`, `pollers.py` RTU e TCP).
- **Postgres local para teste** via `docker-compose.yml` (novo, na raiz) — container isolado, dados em `data/postgres_data/` (gitignored). Script `migrate_sqlite_to_postgres.py` migra os dados reais do SQLite preservando IDs, ajustando sequences, e pulando registros corrompidos sem abortar (ver "Notas" abaixo). App continua rodando em SQLite; a troca de `DATABASE_URL` é manual (linha alternativa comentada no `.env`).
- **`/api/metrics/available`**: lista métricas com dados reais para um device/período (usado pelo seletor dinâmico da Análise Temporal).
- **`/api/metrics/period_summary`**: estatísticas do período atual vs período anterior equivalente (mesmo device/métrica), incluindo consumo (kWh) quando a métrica é cumulativa (`energy_wh`/`energy_kwh`) e variação percentual.
- **Cpk real com limites de especificação** (`app/services/analytics.py::SPEC_LIMITS`): tensão (209-231V, PRODIST Módulo 8), frequência (58.8-61.2Hz), fator de potência (≥0.92). Sem limite conhecido, cai num índice auto-referenciado (média±3σ) claramente sinalizado como não sendo um Cpk real (`cpk_real: false`) — antes o cálculo usava sempre média±3σ e dava ~1.0 pra qualquer métrica, inclusive as com limite de norma conhecido.
- **Card "Qualidade — Six Sigma"** e **"Comparação com Período Anterior"** na Análise Temporal, consumindo os dois endpoints acima.
- **Tooltips ricos em todos os gráficos**: `interaction: {mode:'index', intersect:false}` (mostra todas as séries ao passar o mouse num ponto do eixo X) + formatação de valor com separador brasileiro, aplicado em `dashboard.js` e `analytics.html`.
- **Redesign visual completo** — tema "painel de instrumentação": fundo grafite, leituras em fonte monoespaçada (JetBrains Mono) estilo mostrador digital, cores de fase R-S-T reais (L1 vermelho / L2 âmbar / L3 azul) usadas de forma consistente em números ao vivo e gráficos. Layout unificado via `app/templates/base.html` (nav compartilhada entre Dashboard/Análise Temporal/Dispositivos). Emojis decorativos removidos de títulos/botões.
- **Tema claro/escuro**: dois botões no topo (`Claro`/`Escuro`), paleta clara com cores recalibradas para contraste (não é só clarear o fundo), persistida em `localStorage`, sem flash ao carregar (`app/static/js/theme.js`). Gráficos Chart.js reconstroem as cores ao trocar de tema (canvas não lê variável CSS ao vivo).

### Notas / dívidas conhecidas
- Cliente `id=2` no SQLite tem um nome corrompido (conteúdo inteiro de um script PowerShell, ~2400 caracteres) — lixo de teste antigo, sem dispositivos associados. O script de migração pula automaticamente por estourar `VARCHAR(200)` no Postgres; não foi limpo do SQLite.
- 5 measurements órfãs (device_id apontando pra um device já apagado) — sobraram de uma corrida entre o scheduler (poll a cada 30s) e uma exclusão via UI; SQLite não valida foreign key por padrão. Também puladas na migração. Não é um bug novo desta sessão, é pré-existente à falta de `PRAGMA foreign_keys=ON`.
- Havia dois processos uvicorn duplicados rodando o app (um pela venv do projeto, travado sem bindar a porta; outro pelo Python global, de fato servindo). O travado foi encerrado; o que está servindo (Python global, `--reload`) foi mantido rodando de propósito — é o coletor de dados reais ao vivo.
- `firebase-admin` e `psycopg2-binary` foram adicionados ao `requirements.txt` mas o Postgres/Firebase são **opcionais** — SQLite continua sendo o banco em produção até decisão explícita de migrar.

### Contexto de infraestrutura (fora deste repo)
- Servidor físico "Fidelco" (mini PC + HD) para o Postgres definitivo ainda não está disponível. Plano combinado: teste local agora → HD na máquina de escritório (liga 24h) amanhã → mini PC em casa no futuro. Ver `pieng_postgres/SETUP_FIDELCO.md` (projeto irmão) — script de provisionamento assume specs de servidor (8 cores/16GB/SSD) que **não batem** com o hardware real planejado (mini PC + HD mecânico); precisa ajuste de tuning (`random_page_cost`, `shared_buffers` etc.) antes de rodar lá.
