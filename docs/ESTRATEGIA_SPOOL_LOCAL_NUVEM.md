# Estratégia futura — coleta local + nuvem + spool (pós-cota Tuya)

Atualizado: **2026-09-10**  
Status: **decisão de direção** (ações futuras; ainda não implementado por completo).

## Por que mudar

O plano **Trial / free** da Tuya IoT Core limita, entre outras coisas:

| Limite | Trial (ordem de grandeza) |
|--------|---------------------------|
| API calls / mês | ~**26.000** |
| Devices controláveis | ~**10** (erro `60001001` além disso) |

Poller Tuya a cada **30 s** com 2 medidores ≈ **~173 mil calls/mês** — estoura o free em poucos dias.  
Conclusão: **Tuya Cloud não pode ser o coração da coleta contínua**. Serve para comando ocasional / ponte temporária.

Hardware que o usuário **já tem** e deve virar eixo da medição:

- **Elfin EW11** → Modbus TCP (ex.: SDM630)
- **PZEM-004T** → Modbus RTU (USB-RS485)

Drivers/pollers já existem no Energy Meter (`modbus`, `modbus_tcp`, `pzem004t`, `eastron_sdm630`).

## Nova arquitetura (alvo)

```text
                    ┌─────────────────────────────┐
  Casa / planta     │  Spool LOCAL (buffer)         │
  Elfin + PZEM      │  SQLite / fila / arquivo       │
  (+ opcional LTE)  │  coleta mesmo sem Internet    │
                    └──────────────┬──────────────┘
                                   │ flush quando houver rede
                                   ▼
                    ┌─────────────────────────────┐
                    │  Banco na NUVEM / central     │
                    │  Postgres (pieng_postgres)    │
                    │  recebe medições + comando    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │  Apps: Dashboard, HOME,       │
                    │  Flutter/mobile, tablet       │
                    └─────────────────────────────┘
```

### Princípios

1. **Medição crítica = local (Modbus)** — zero cota Tuya.  
2. **Spool local** — se a Internet cair, os dados **não se perdem**; descarregam depois (mesmo espírito do flush SQLite→Postgres atual, mas o coletor pode ficar na planta).  
3. **Banco central/nuvem** — verdade compartilhada para vários clientes/apps.  
4. **Tuya Cloud** — só comando pontual ou devices ainda sem LAN; poll longo (minutos) ou desligado.  
5. **HOME / mobile** — mesma API PIENG; mudam os conectores, não a ideia do painel.

## Peças do desenho

### A) Spool local (coletor na planta)

#### Decisão 2026-09-10 (noite++) — edge no cliente

| Fase | Onde roda o coletor | Quando usar |
|------|---------------------|-------------|
| **Produção (preferida)** | **Mini PC barato no cliente** (ligado 24/7) | Multi-cliente; spool local → sobe via API |
| **Piloto / provisório** | PC do cliente + **Tailscale** + Energy Meter | Testar 1–2 plantas sem comprar hardware ainda |
| **Sem Wi‑Fi estável** | **USR-G771 LTE** (já no inventário) | Remoto / rural |

**Papéis (não confundir):**

```text
PZEM/SDM → Elfin (só bridge RS485→Wi‑Fi / Modbus TCP)
                ↓
         Mini PC (poller + spool SQLite)
                ↓  POST /api/ingest  (não abrir Postgres :5432 no cliente)
         Banco central / nuvem
```

- **Elfin** = melhor para **medição contínua** (zero cota Tuya). **Não** grava sozinho no banco: só deixa o medidor acessível na rede.
- **Mini PC** = sobe a informação (barato; HD grande fica no servidor central).
- **Tailscale no PC do cliente** = ok só como piloto (PC precisa ficar ligado; risco se Postgres for exposto). Preferir API com token.
- HD/router sozinho no cliente = fraco; preferir mini PC + spool.

Opções ainda válidas:

| Opção | Descrição |
|-------|-----------|
| **Mini PC / NUC / Raspberry** na casa | **Escolha principal** — poller + SQLite spool + flush para API/Postgres central |
| **Gateway industrial** (ex. USR-G771 LTE) | Modbus → 4G → Internet, com buffer se o chip/rede oscilar |
| **PC do cliente + Tailscale** | Piloto provisório; não escala como produto |
| **App mobile como “ponte”** | Campo/diagnóstico; não substitui coletor 24/7 |
| **Dispositivo dedicado “edge”** | ESP32/PLC/gateway MQTT (futuro) |

Regra do spool (igual Six Sigma / auditoria):

- Gravar **só dado real** com timestamp.  
- Flush **at-least-once** com idempotência (`device_id + timestamp + metric` ou id de lote).  
- Se a nuvem estiver fora: continuar gravando local; retentar com backoff.

O flush atual (`postgres_flush` 30 min, teto SQLite 200 MB) é o **protótipo** dessa ideia no escritório; generalizar para “edge → cloud”.

### B) Banco na nuvem / central

- Dono: projeto **`pieng_postgres`**.  
- Acesso remoto: **Tailscale** (não abrir `5432` na Internet) — ver `pieng_postgres/REMOTE_ACCESS.md`.  
- Apps (Energy Meter UI, HOME, Flutter) leem/escrevem via API ou Postgres conforme o papel.

### C) Comando (luz / ar / interruptor)

- Não pollear cloud a cada 30 s.  
- Preferir **LAN** (Tuya local, MQTT, Zigbee local, relé Modbus) no médio prazo.  
- Cloud só no toque, e só para devices no **pool controlável**.

### D) Mobile / Flutter

Já combinado em `docs/HOME_UI_STACK.md`:

- Protótipo **Flutter** consumindo `/home/api/*` e APIs de métricas.  
- Pode, no futuro, também:  
  - ver dados da nuvem (operador remoto);  
  - em modo campo, ajudar a “empurrar” spool / diagnosticar Elfin/PZEM (não substituir o coletor fixo).

## Mapa Tuya vs Modbus (ações futuras)

| Função | Hoje | Futuro |
|--------|------|--------|
| kWh / potência contínuos | Poller Tuya 30 s | **Elfin + PZEM (Modbus)** + spool |
| Medidor Tuya trifásico | Ativo | Backup ou intervalo ≥ 3–5 min |
| Interruptores / ar | HOME via Cloud | Cloud sob demanda → depois local |
| Storage | SQLite + espelho K: | Edge spool + **Postgres central/nuvem** |
| Acesso remoto | Tailscale | Mantém + API na nuvem |

## Próximas ações (checklist)

- [ ] Reduzir ou pausar poller Tuya de medidores (intervalo longo) para não queimar a cota.  
- [ ] Validar comunicação **Elfin EW11** (IP) + SDM630 e/ou **PZEM** (COM).  
- [ ] Cadastrar esses devices como fonte oficial de medição no Energy Meter.  
- [ ] Desenhar contrato do **spool** (formato do lote, retry, idempotência).  
- [x] Definir edge: **mini PC no cliente** (produção); Tailscale no PC do cliente só piloto; LTE se sem Wi‑Fi.  
- [ ] Comprar/especificar mini PC (baixo custo, SSD pequeno, boot automático do poller).  
- [ ] Postgres central acessível via Tailscale; edge sobe via **API** (`/api/ingest`), não Postgres cru.  
- [ ] HOME: não auto-refresh agressivo; comando sob demanda.  
- [ ] Protótipo Flutter em cima da API (painel + depois modo campo).  
- [ ] Atualizar inventário: quais devices ficam nos 10 controláveis Tuya.

## Premissas que não mudam

- **Só dados reais** — sem mock para “encher gráfico”.  
- Offline = vazio/`NULL`/fila local, nunca inventar medição.  
- Auditoria rastreável (`data/audit.log` / logs de flush).

## Docs relacionados

- `docs/HOME_UI_STACK.md` — UI tablet/Flutter vs React+Babylon  
- `docs/SETUP_POSTGRES_NATIVO_K.md` — espelho local atual  
- `pieng_postgres/REMOTE_ACCESS.md` — Tailscale + Postgres  
- `docs/ROADMAP_CASA_INVERSOR_NUVEM.md` — medidor no inversor (revisar: priorizar Modbus/Elfin em vez de Tuya 30 s)  
- `CHANGELOG.md` — entrada 2026-09-10
