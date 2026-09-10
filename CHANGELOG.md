# Changelog

Todas as mudanças relevantes do projeto Energy Meter são registradas aqui.
Formato livre, em português, por sessão de trabalho.

## 2026-09-09 (noite final) — Validação ao vivo no painel + encerramento

### Testado pelo usuário (logs :8001)
- Interruptor `eba5da7bcaca181936499z` tecla 3 → ligar → `success: True`
- Interruptor `ebdd111cd1fc767c0fbyta` tecla 2 → ligar → `success: True`
- Ar Consul: `T24`, `T23` e `PowerOff` pelo hub IR → `success: True`
- Poller Energy Meter: medidorCASA + Solar Dual Meter coletando normalmente

### Problema conhecido (Tuya Cloud, não do código)
- Device `eb5a1f91b343c565846oqi` (3 teclas): erro **`60001001`**
  *Your controllable device pool quota is insufficient.*
- Causa: cota/vínculo do projeto no console Tuya IoT (aparelho fora do pool
  controlável ou cota do plano). Correção no console Tuya, não no app.

### Operação ao encerrar
- Servidores locais derrubados; PC desligado a pedido do usuário.
- Branch publicada: `feature/home-module` (GitHub + PR #1).
- Amanhã em outra máquina: `git checkout feature/home-module` + `.env` Tuya +
  `uvicorn :8001` (ver checklist da sessão).

## 2026-09-09 (madrugada, HOME) — Repaginação do painel web + correções que faltavam

### Corrigido (backend)
- **Ar-condicionado sem estado**: o card lia `temp`/`T`/`temp_set`, mas o device
  virtual do hub IR guarda em **`temperature`** e **`switch_power`**. Agora o ar
  mostra temperatura real, ligado/desligado, além de **modo**, **vento** e
  **swing** (`mode`/`fan`/`swing`, traduzidos de enum para texto).
- **Tecla de power do IR**: era sempre `PowerOn`/`PowerOff`. Agora vem do
  catálogo (`remote.keys`). A **TV Samsung usa `Power` (toggle)** e o ar usa
  `PowerOn`/`PowerOff`. Novo campo `power_mode` (`toggle`/`onoff`) no payload.
- **`set_ac_temp`**: fallback passou a usar o DP real `temperature`.
- **Lista lenta**: os status eram lidos em série (≈43 s para 25 aparelhos).
  Agora em paralelo (`ThreadPoolExecutor`, 8 threads) → **≈11 s**.
- Controles IR não expõem mais canal falso `switch_1`.

### Redesign da interface (`/home`)
- Tema escuro vibrante com aurora de fundo, cards translúcidos e **borda/brilho
  neon na cor do tipo** quando o aparelho está ligado (luz âmbar, tomada verde,
  ar violeta, medidor amarelo, sensor turquesa).
- **Ícones SVG** por tipo e por nome: lâmpada, interruptor, tomada, ar, TV,
  controle, medidor, termômetro, gateway, portão de garagem, bomba, alarme.
- **Toggle grande de um toque** (56 px) no lugar dos dois botões, com estado
  escrito (LIGADO/DESLIGADO) — o desenho nunca é a única indicação.
- Ar com termostato: −/+ de 56 px, temperatura em destaque e chips de modo/vento.
- TV/IR com botão **Power** único quando a tecla é toggle, e aviso de que
  infravermelho não devolve estado.
- Barra de resumo: total, online, offline e quantos estão ligados.
- Offline: card dessaturado, selo OFFLINE e **todos os controles desabilitados**.
- Filtros novos (TV/IR), skeleton de carregamento e alvos de toque ≥ 48 px.

### Validado ao vivo (hardware real)
- Ar Consul: `T25` chegou pelo hub IR; `PowerOff` desligou e o estado voltou
  para `on=false`.
- luz da varanda (3 teclas): ligou e desligou pela interface, com confirmação
  relida da Tuya.
- Aubess offline: API recusa com `Dispositivo offline`.
- Sensor: 24,7 °C / 53,2 % / bateria 21 %.

### Operação
- Havia **dois uvicorn** ativos (8000 coletando, 8001 com reload travado
  servindo código velho). O de :8001 foi reiniciado com
  `--reload-dir app --reload-dir home`; o coletor de :8000 não foi tocado.

## 2026-09-09 (noite, HOME) — Direção visual: painel vibrante para celular/tablet

### Decisão (a evoluir)
- Visual atual do `/home` é **fraco** para o uso real (celular/tablet, no dedo).
  Meta: fundo escuro, cores vibrantes, cartões translúcidos, ícones que remetem
  ao objeto real (luz, interruptor, portão, TV), animações de 300–700 ms.
- Alvo futuro: **React + TypeScript + Babylon.js + Framer Motion + Tailwind**,
  rodando como **PWA em modo kiosk** no tablet.
- **Hoje vamos pelo simples: protótipo em Flutter**, testando vários frameworks
  antes de fixar a escolha. React+Babylon fica como próxima etapa.
- Ajuste em relação à referência pesquisada: ela assume **Home Assistant** e a
  WebSocket API dele. Aqui **não usamos Home Assistant** — a fonte de verdade é
  o próprio `/home/api/*` do FastAPI (e, se precisar de tempo real, um
  WebSocket nosso).
- Invariantes de qualquer protótipo: ação principal em 1 toque, botão grande,
  estado sempre visível (ligado/desligado/indisponível), modo simples de
  fallback, e o desenho **nunca** é a única indicação de estado.

Detalhamento completo: `docs/HOME_UI_STACK.md`.

## 2026-09-09 (noite, HOME) — Status ONLINE/OFFLINE por device

### Adicionado
- `getdevices` não traz `online`; agora a listagem enriquece via
  `GET /v2.0/cloud/thing/batch` (`is_online`), em lotes de 20.
- Controles virtuais IR (ar/TV) herdam a disponibilidade do **hub físico**.
- `get_home_device` consulta `/v2.0/cloud/thing/{id}` e cai no gateway quando o
  virtual aparece offline.
- `set_switch` recusa comando para device offline sem gateway.
- UI: badge ONLINE/OFFLINE, card esmaecido, botões desabilitados e barra de
  status `N devices · X online · Y offline`.
- Estado no momento do teste: **25 devices — 15 online, 10 offline**.

## 2026-09-09 (noite, HOME) — Catálogo por category + product name

### Decisão
- O que mais se **repete** é `category` + **Product Name** (não o device_id).
- Hierarquia do JSON: `categories` → `products` (nome Tuya) → `devices` (só nome
  amigável + exceções).
- Cards HOME passam a mostrar em destaque: **CATEGORY · Product Name**, depois o
  tipo (Luz/Ar/Medidor...).

## 2026-09-09 (noite, HOME) — Aubess 1-gang schema tipado confirmado

### Atualizado
- `eb5946695d88af3469ribh` (`Aubess Smart Switch 1-gang`): `dp_codes` passou de
  lista simples para schema tipado (`switch_1`, `countdown_1`, `relay_status`
  0/1/2, `switch_type` flip/sync/button, strings maxlen 255). Continua offline.

## 2026-09-09 (noite, HOME) — WB03-NCD (luz da varanda) schema completo

### Adicionado
- Device `eb70f50b42d62534a1wnhe` (`WB03-NCD` / **luz da varanda**, cat. `kg`):
  3 teclas `switch_1..3`, countdowns por tecla, `relay_status`
  (`power_off`/`power_on`/`last`), cycle/random/inching.

## 2026-09-09 (noite, HOME) — Lâmpada RGBCW + TV Samsung IR no catálogo

### Adicionado
- `eb1028824b950af6c6rthi` (`TC0000_W600_LIGHT5_RGBCW_P1`, cat. `dj`): luz RGBCW
  com `switch_led`, `work_mode` (white/colour/scene/music), brilho/temp/cor.
  Card previsto: `rgb_light` (liga/desliga já funciona via `switch_led`).
- `ebdb589e70438d7223jryg` (`电视` / **Tv Samsung**, cat. real `infrared_tv`):
  controle virtual no hub `04708305d8bfc017c02e`. Chave de energia = `Power`
  (toggle STRING). Schema completo das teclas gravado (0–9, Volume±, Channel±,
  setas, OK/Menu/Home/Back, `-/--`, e `C` como ENUM 1..999 para canal direto).

## 2026-09-09 (noite, HOME) — Interruptor WiFi+RF433 (portão da garagem)

### Adicionado
- Device `eb61a0c15929a64a0dilbh` (`INTERRUPTOR WIFI + RF433`, nome na conta:
  **portão da garagem**) no catálogo como switch 1 canal.
- DPs: `switch_1`, `countdown_1`, `relay_status`, `switch_type`,
  `remote_add` / `remote_list` (pareamento RF433).
- Validado online: `switch_1=false`, `relay_status=2`, `switch_type=flip`.

## 2026-09-09 (noite, HOME) — Aubess Smart Switch 1-gang no catálogo

### Adicionado
- Device `eb5946695d88af3469ribh` (`Aubess Smart Switch 1-gang`, categoria `tdq`)
  no `home/device_catalog.json` como switch 1 canal (`switch_1`).
- DPs: `countdown_1`, `relay_status` (0/1/2), `random_time`, `cycle_time`,
  `switch_inching`, `switch_type` (`flip`/`sync`/`button`).
- Status no momento do registro: **Offline** (ativado em 2023-02-19).
- Importante: mesma categoria `tdq` do PC473, mas é relé simples — override por
  `device_id` evita tratar como medidor trifásico.

## 2026-09-09 (noite, HOME) — PC473_OUYOU trifásico no catálogo + card L1/L2/L3

### Adicionado
- Device `eb9a1c787c60d712fazces` (`PC473_OUYOU` / medidorCASA) no
  `home/device_catalog.json` como **meter trifásico** (não mais switch `tdq`).
- Card `triphase_meter`: potência total, 60 Hz, kWh rede/solar e L1/L2/L3
  (tensão/potência/corrente) + botão do relé `switch_1`.
- DPs capturados do usuário (Standard Instruction parcial: só
  `switch_1`/`fault`/`relay_status` mapeados; resto `-` → shadow).

### Validação real
- Shadow: L1≈228.9 V / 760 W, L2≈229.5 V / 220 W, L3≈228.1 V / 531 W,
  total 1503 W, freq 60 Hz, `switch_1=true`.

## 2026-09-09 (noite, HOME) — Solar WIFI dual meter no catálogo + card medidor

### Adicionado
- Device `eb12907d3f923984f1wntb` (`Solar WIFI dual meter`) no
  `home/device_catalog.json` com todos os DPs informados pelo usuário.
- Card **Medidor** na UI (aba Medidores): tensão, frequência, potências A/B,
  correntes, direção FORWARD/REVERSE e energias.
- Engine passa a ler `shadow/properties` quando `getstatus` vem vazio ou quando
  o catálogo define `status_source: "shadow"` (caso deste medidor; Standard
  Instruction sem mapeamento `-`).

### Notas técnicas reais
- Categoria Tuya `cz` (parecia tomada), mas não é switch.
- Typos oficiais da API: `energy_forword_*`, `energy_reserse_b`.
- Escalas alinhadas ao poller Energy Meter: V÷10, Hz÷100, A÷1000, FP÷100, kWh÷100.
- `coef_*_reset` bloqueados na UI/API HOME.
- Amostra validada: `voltage_a=230.0 V`, `freq≈58.98 Hz`,
  `energy_forword_a=17.90 kWh`, `direction_a=FORWARD`.

## 2026-09-09 (noite, HOME) — Catálogo JSON + cards sensor/gateway/AC IR

### Adicionado
- `home/device_catalog.json`: conhecimento versionado dos devices reais
  (interruptores 3 teclas, Ar Consul + hub IR, sensor clima `wsdcg`,
  gateway Zigbee `QC-ZB-GW`, hub IR Ekaza).
- Endpoint `GET /home/api/catalog` para inspecionar o conhecimento.
- Cards novos na UI HOME:
  - **Sensor**: temperatura/umidade/bateria + limites de alarme.
  - **Gateway**: estado `normal/alarm`, alarme ativo, som do alarme;
    `factory_reset` bloqueado.
  - Abas Sensores / Gateway.
- Assets HOME em `v=3`.

### Corrigido / consolidado
- Cards de interruptores Tuya `kg` controlam `switch_1`/`switch_2`/`switch_3`.
- Ar Consul usa API IR do hub físico (`04708305d8bfc017c02e`) —
  exige **IR Control Hub Open Service**.
- Sensor `eb9566f34c86a5f2211xsj`: `va_temperature`/`va_humidity` com scale 1
  (ex.: 269 → 26.9 °C). O `switch` do sensor NÃO é luz.
- Gateway `eb0c341d9937c0724av8b4` (`QC-ZB-GW`): só controles seguros.

### Validação real
- `PowerOff` via hub IR desligou fisicamente o Ar Consul.
- Interruptor da frente/quintal/sala: 3 canais lidos corretamente.
- Sensor online com temp/umidade/bateria reais.
- Servidor: `http://127.0.0.1:8001/home`.

## 2026-09-09 (noite, HOME) — Interruptores multi-tecla + ar Consul via IR Hub

### Corrigido
- Cards HOME de interruptores Tuya `kg` controlavam somente `switch_1`, embora os
  dispositivos reais da sala, quintal, frente e varanda exponham também
  `switch_2` e `switch_3`. Cada card agora mostra e aciona separadamente
  **Tecla 1**, **Tecla 2** e **Tecla 3**, usando o código Tuya correto.
- A confirmação após um comando deixou de reler todos os dispositivos da conta;
  consulta somente o device acionado, evitando timeout e estado visual atrasado.
- Assets HOME receberam versão `v=2` para impedir que o navegador reutilize
  JavaScript/CSS antigos.
- **Ar Consul** (`ebb156318969d8d865tuky`): comando direto no device virtual
  retornava `success` sem emitir IR. Passou a usar a API
  `/v2.0/infrareds/{hub}/remotes/{remote}/command` no hub físico
  `04708305d8bfc017c02e` (exige **IR Control Hub Open Service** autorizada).

### Validação real
- Tuya confirmou comando idempotente direto com `success: true`.
- Endpoint HTTP corrigido confirmou `switch_2` com `ok: true`.
- Leitura real do interruptor da sala retornou os três estados:
  `switch_1=true`, `switch_2=false`, `switch_3=true`.
- `PowerOff` via hub IR desligou fisicamente o ar Consul (confirmado pelo usuário).
- Servidor corrigido em `http://127.0.0.1:8001/home`.

## 2026-09-09 (noite, acesso remoto) — Ação futura para 2026-09-10

### Decisão planejada
- Usar **Tailscale** como primeira opção para acessar remotamente o computador do
  escritório, o dashboard (`:8001`) e, quando necessário, o PostgreSQL nativo
  (`:5432`) no `K:\storage`.
- O controle do servidor central, das conexões e dos bancos de outros programas
  fica no projeto irmão `pieng_postgres`. O documento canônico é
  `pieng_postgres/REMOTE_ACCESS.md`; este projeto apenas consome/espelha dados.
- Não expor a porta 5432 diretamente na Internet. O acesso ao banco deve ocorrer
  pelo serviço PostgreSQL através da VPN, nunca compartilhando a pasta `pgdata`.
- Manter a coleta no SQLite local e o flush para o PostgreSQL a cada 30 minutos,
  evitando que uma queda de Internet interrompa as leituras reais.
- Deixar um túnel **WireGuard entre MikroTiks** como alternativa futura para
  interligar redes completas ou instalações com vários equipamentos.

### Ação futura
- Primeiro computador autenticado no Tailscale com sucesso (`100.126.2.58`).
- Instalar e autenticar o computador que hospeda o PostgreSQL e o `K:\storage`.
- Validar primeiro o acesso ao dashboard pelo IP privado Tailscale.
- Se for necessário acesso direto ao banco, restringir `postgresql.conf`,
  `pg_hba.conf` e o Firewall do Windows ao IP Tailscale autorizado.

## 2026-09-09 (noite, cont.) — Navegação de período (dia/semana/mês anterior) + achado: servidores duplicados

### Adicionado
- **Navegação no histórico** ao lado da régua Dia/Semana/Mês: botões ◀ / ▶ +
  "Hoje", pra folhear dias/semanas/meses passados agora que o Postgres/SQLite
  vão acumular várias janelas de dados (antes só dava pra ver "últimas 24h/7d/
  30d a partir de agora", sem navegar pro passado).
  - Backend: `GET /api/metrics` ganhou parâmetro opcional `end` (ISO, âncora
    do fim da janela) — sem ele, comportamento idêntico a antes (janela
    terminando "agora"). `crud.list_measurements` ganhou `until`.
  - Frontend: `anchorEnd` (epoch ms ou `null`="agora"); `metricsUrl()` manda
    `end` em hora LOCAL sem timezone (`toNaiveLocalISOString`) pra bater com
    o que o poller grava (`datetime.now()`, sem tzinfo) — usar `toISOString()`
    (sempre UTC) quebraria a comparação no banco.
  - Detecção de "é trifásico" deixou de depender da janela navegada (checava
    `voltage_l1` dentro do período; navegar pra um dia sem dados fazia cair
    no branch monofásico por engano) — agora é uma checagem de capacidade do
    device, sem filtro de período.
  - Auto-refresh de 30s pausa sozinho quando o usuário está olhando um
    período passado fixo (não tem o que atualizar).
  - Zoom (`timeWindow`) e navegação resetam pro completo ao trocar de
    device/período ou voltar em "Hoje".

### Achado (não corrigido nesta sessão — avaliar com o usuário)
- Durante o teste, encontrados **dois processos uvicorn rodando ao mesmo
  tempo** contra o mesmo `data/app.db`: um na porta 8000 (mais antigo, PID
  invisível para consultas WMI/CIM nesta sessão — possivelmente iniciado em
  outra sessão/elevação) e um par supervisor+worker na porta 8001 (visível,
  `--reload`, reflete corretamente mudanças de código Python). Evidência:
  `power_total` do `medidorCASA` estava sendo gravado a cada ~8-12s em vez
  dos 30s configurados — indica pollers duplicados batendo na API Tuya e no
  SQLite ao mesmo tempo. Templates/estáticos (HTML/CSS/JS) aparecem
  corretamente atualizados nas duas portas porque são lidos do disco a cada
  request; só a lógica Python (ex.: o parâmetro `end` novo) precisa do
  processo realmente recarregado, e isso só foi confirmado na porta 8001.
  Não encerrei nenhum processo — decisão do usuário sobre qual manter.

## 2026-09-09 (noite) — Zoom de tempo compartilhado + fix de loop no chart-wrap

### Corrigido
- **`.chart-wrap` crescendo indefinidamente** (mais visível no card multi-métrica):
  tinha `flex:1` dentro de um `.card` (`display:flex; column`) com altura `auto`
  (`grid-auto-rows:minmax(0,auto)`). Loop: canvas mede 100% do wrapper → wrapper
  (flex:1) cresce → card cresce (altura auto) → wrapper recalcula 100% maior →
  canvas cresce de novo. Trocado `flex:1` por `flex:0 0 auto`, altura passa a vir
  só do `height:220px`/`280px` fixo, sem disputa com o flexbox. `styles.css` v11→v12.

### Adicionado
- **Régua de zoom de tempo única** (`#timeZoomBar`, dois `<input type=range>`
  sobrepostos) acima dos cards: no período "Dia" (24h) dá pra focar, por exemplo,
  só das 12h às 15h — e isso agora reflete em TODOS os cards (valores ao vivo,
  médias, e todos os gráficos: tensão, corrente/potência consumo×injeção, energia,
  multi-métrica), sem refazer requisição ao servidor (filtra client-side os dados
  já carregados do período Dia/Semana/Mês).
- Refatorado `dashboard.js`: `loadData()` agora só busca dados e guarda em
  `rawCache`; todo o desenho (valores + gráficos) foi extraído pra
  `renderFromCache()`, que aplica `filterWindow()` e roda de novo sem rede a cada
  arrasto da régua. Zoom é absoluto (epoch ms), não normalizado — sobrevive ao
  auto-refresh de 30s sem "pular". Trocar de dispositivo ou de período (Dia/
  Semana/Mês) reseta o zoom pro completo automaticamente.
- `dashboard.js` v12→v13, `dashboard.html` v12→v13, `styles.css` v12→v13.

## 2026-09-09 (fim de tarde) — Separação consumo (rede) vs injeção (solar)

### Contexto
- `power_total` do `medidorCASA` fica negativo (ex.: -2308 W). Investigado se seria
  geração solar real ou TC instalado ao contrário. Consultando a API Tuya diretamente
  (dados reais, dispositivo `eb9a1c787c60d712fazces`) confirmou-se que o hardware já
  mede os dois sentidos separadamente por fase: `forward_energy_a/b/c/total`
  (consumida da rede) e `reverse_energy_a/b/c/total` (injetada na rede), além de
  `active_power_a/b/c` virem com sinal. No instante da checagem, fase L2 sozinha
  injetava ~2365 W a FP≈1.0 (10.38 A) enquanto L1/L3 tinham cargas pequenas — padrão
  de inversor solar monofásico num circuito só, não de TC generalizado invertido.
  Teste decisivo pendente: conferir se `power_total` fica positivo de madrugada
  (sem produção solar possível); se continuar negativo à noite, aí sim é TC invertido.

### Adicionado
- `app/services/tuya_poller.py::parse_tuya_data()` agora extrai e grava, por fase e
  total: `energy_imported_*`/`energy_exported_*` (kWh acumulado real do próprio
  hardware, direto de `forward_energy_*`/`reverse_energy_*` — não é estimativa) e
  `power_import_*`/`power_export_*`/`current_import_*`/`current_export_*`
  (instantâneos, derivados do sinal já presente em `active_power_a/b/c/total`).
  Limitação conhecida: `current_*` do Tuya não tem sinal próprio (só magnitude), então
  a corrente é atribuída ao sentido da fase no instante da leitura — não isola a
  corrente do inversor de fato sem um TC dedicado nele (próximo passo se o usuário
  quiser simultaneidade real produção×consumo).
- Card **"Rede / Solar"** no dashboard (`dashboard.html`/`dashboard.js` v11): mostra
  W/A injetados vs consumidos agora, e kWh acumulado injetado vs consumido. Some
  automaticamente para devices que não têm essas métricas (monofásicos sem solar).
- **Gráficos de Potência e Corrente espelhados** (v12): os cards únicos "Potência (W)"
  e "Corrente (A)" (3 fases, valor líquido) viram 2 cards cada quando o device tem
  dado de import/export — "Consumo (Rede)" e "Injeção (Solar)", sempre com L1/L2/L3
  lado a lado. Bate o olho e já mostra qual fase tem solar (no `medidorCASA`, é a L2).
  Devices sem essas métricas continuam vendo o gráfico único de antes.

## 2026-09-09 (noite++) — Flush 30 min + teto cache SQLite 200 MB

### Decisão (teste no escritório, máquina não dedicada)
- Flush SQLite → Postgres (espelho no `K:`) a cada **30 minutos** (antes 10).
- Teto do hot cache SQLite: **200 MB** ≈ **~3 dias com ~3 aparelhos** trifásicos no ritmo atual (~15 MB/dia/device).
- Se o HD `K:` ficar fora, a coleta **não para**: dados ficam no SQLite até o próximo flush bem-sucedido.
- Em máquina dedicada / produção futura, dá para subir intervalo e teto pela UI sem editar código.

### Alterado
- `data/runtime_settings.json`: `postgres_flush_interval_minutes: 30`, `sqlite_cache_max_mb: 200`.
- `app/services/runtime_settings.py`: defaults 30 / 200 + `sqlite_cache_status()`.
- `app/routers/db_panel.py` + `db_panel.html` / `db_panel.js`: campo teto MB + uso atual (% / alerta se passar do teto).
- `app/main.py`: fallback do job `postgres_flush` = 30 min; PATCH `/api/db/settings` reescalona o APScheduler.
- `env.example` + `docs/SETUP_POSTGRES_NATIVO_K.md` + `K:\storage\README.txt` alinhados.

### Operacional
- Servidor de coleta: **http://127.0.0.1:8001/** (porta 8000 ficou com processos zumbis nesta sessão).
- Reinício limpo do uvicorn foi necessário quando `--reload` travou a meio; depois disso status confirmou flush 30 min + cache 200 MB (SQLite ~4–5 MB no momento).

## 2026-09-09 (noite+) — Descoberta Tuya + papel inversor / nuvem

### Contexto
- Storage permanece no **escritório** (`K:\STORAGE`).
- Em casa: novo medidor Tuya na **saída do inversor** (mesmo projeto Cloud).
- Meta: reconhecer medidor novo e incluir no projeto com pouco esforço; acesso remoto via túnel/Tailscale (doc).

### Adicionado
- `GET /api/devices/tuya/discover` — lista Cloud vs cadastrados, sugere `role`.
- `POST /api/devices/tuya/enroll` — inclui com 1 clique (`config.role`: `grid_point` | `inverter_output` | …).
- UI no Setup (`device_setup.html` / `device_setup.js`): card “Tuya na nuvem”.
- `docs/ROADMAP_CASA_INVERSOR_NUVEM.md` — arquitetura escritório/casa/nuvem.

## 2026-09-09 (noite) — Premissa solar: negativo = injeção + métricas Rede×Solar

### Premissa (oficial)
- **Potência/corrente negativas = injeção de usina solar** (export para a rede).
- Positivo = consumo da rede (import).
- Potências finais ficam separadas: `power_import_*` / `power_export_*` (+ correntes e energias).

### Adicionado
- `app/services/flow_split.py` — helper de split + `is_cumulative_energy_metric`.
- `GET /api/metrics/solar_summary` — no período: kWh injetado, kWh da rede, pico de injeção (W + timestamp), pico rede, balanço líquido.
- Card **Rede × Solar (injeção)** na Análise Temporal (`analytics.html`).
- Labels de métricas import/export no seletor.
- SDM630 (`eastron_sdm630.py`) agora também grava split import/export (mesma premissa).
- `period_summary` trata `energy_imported_*` / `energy_exported_*` como acumuladores (delta no período).

### Notas
- Preferência de energia: delta de `energy_exported_total` / `energy_imported_total` (hardware Tuya); fallback = integração de `power_export_total` / `power_import_total`; último recurso = `power_total` com sinal.

## 2026-09-09 (tarde++) — Favicon PIENG

### Alterado
- Favicon estava vazio (`app/static/favicon.png` = 0 bytes). Substituído pelos assets oficiais da pasta `E:\Projetos\Pieng_doc\backend\logo\` (π dourado / escudo).
- `base.html` agora referencia `favicon.ico` + PNG 16/32/48 + apple-touch (`static/brand/logo-app-96.png`).
- Cópias da marca em `app/static/brand/` (`logo-pieng.png`, `logo-escuro.png`, `logo-app-96.png`).

## 2026-09-09 (tarde+) — Painel Banco/Storage + flush SQLite→Postgres configurável

### Adicionado
- **Painel** `GET /api/db` — status do Postgres no K:, contagens SQLite×Postgres, browser de tabelas, flush manual.
- **Flush automático** SQLite (hot) → Postgres espelho, intervalo em `data/runtime_settings.json` (UI altera sem editar .env). Padrão **10 min**; usuário sobe para **30** de noite.
- Serviços: `app/services/postgres_mirror.py`, `app/services/runtime_settings.py`, router `app/routers/db_panel.py`.

### Comportamento
- Dashboard/coleta **continuam no SQLite**. Postgres no K: é espelho.
- Explicação do `DATABASE_URL` está no próprio painel (não trocamos a URL ao vivo).

### Docs
- `docs/SETUP_POSTGRES_NATIVO_K.md`, `CHANGELOG.md`, `.claude/session_context.json`, nav em `base.html`.

## 2026-09-09 (tarde) — Postgres nativo no HD K:\STORAGE (teste escritório)

### Contexto
- Usuário disponibilizou o HD `K:` (rótulo STORAGE, ~149 GB, USB ASMT) para storage multi-banco.
- Mini PC / Fidelco ainda **não** implementado; Docker Desktop **não** instalado nesta máquina.
- Decisão: usar **Postgres nativo** para o teste agora; **manter** `docker-compose.yml` intacto para o futuro.

### Infra / storage
- Layout criado em `K:\storage\` (`postgres\`, `backups\`, `cache\`, `dados\`) + `K:\storage\README.txt`.
- **PostgreSQL 17.11** instalado via EDB (serviço `postgresql-x64-17`, Automatic).
- Data directory: `K:\storage\postgres\energy_meter\pgdata` (confirmado com `data_directory`).
- Role/DB de app: `energy_meter` / `energy_meter` (senha de teste alinhada ao compose).
- Migração REAL: `migrate_sqlite_to_postgres.py` → 4 clients, 1 device (`medidorCASA` id=5), **2641 measurements**.
- `psycopg2-binary` atualizado na venv para `>=2.9.12` (wheel cp313; 2.9.9 não buildava no Python 3.13).

### Docker preservado (não apagado)
- `docker-compose.yml` mantido de propósito.
- Volume Docker separado: `K:/storage/postgres/energy_meter_docker` (não colide com o nativo).
- Porta host do compose mudada para **5433** (nativo já ocupa 5432).

### Documentação
- Novo: `docs/SETUP_POSTGRES_NATIVO_K.md`
- Atualizados: `CHANGELOG.md`, `.claude/session_context.json`, `env.example`, `requirements.txt`, `K:\storage\README.txt`
- Nota em `SETUP_FIDELCO.md` apontando o estado atual do escritório

### Política HD + cache (combinada)
- HD mecânico: preferir **ficar ligado** a ciclar spin-up/spin-down.
- Hot path = SQLite no NVMe (coleta ~30s); espelho = Postgres no `K:`.
- Flush a cada 5–10 min é opção futura; não exige desligar o HD.

### Não feito de propósito
- **Não** trocou `DATABASE_URL` do app ao vivo (uvicorn continua no SQLite).
- **Não** instalou Docker Desktop.
- **Não** removeu arquivos preparados para Docker.

## 2026-09-09 — Sessão: fix de boot sem libs do Google, storage do Postgres de teste no HD do escritório

### Corrigido
- **App quebrava ao iniciar na venv do projeto**: `app/connectors/google_drive.py` importava `google.oauth2`/`googleapiclient` incondicionalmente; esses pacotes não estão instalados em `.venv` (só no Python global). Import agora é opcional (`GOOGLE_AVAILABLE` flag) e `app/routers/__init__.py` registra o router de storage só se ele carregar, sem derrubar o resto da API. Emojis removidos dos prints (mesmo motivo de cp1252 já corrigido no poller Tuya).
- **Prefixo duplicado em `/api/storage`**: `app/routers/storage.py` declarava `prefix="/api/storage"` e era montado de novo sob `/api` em `main.py`, resultando em `/api/api/storage/...`. Corrigido para `prefix="/storage"`.

### Alterado
- **Postgres de teste (`docker-compose.yml`)**: volume movido de `./data/postgres_data` (nunca chegou a ser usado nesta máquina, sem dados) para path no HD do escritório. Em seguida (mesma data, sessão da tarde) o path Docker foi separado de novo para `energy_meter_docker` + porta 5433, porque o teste passou a usar Postgres **nativo** em `energy_meter\pgdata`.

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
