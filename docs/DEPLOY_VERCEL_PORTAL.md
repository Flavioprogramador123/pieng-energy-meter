# Deploy Vercel — portal do cliente (somente visualização)

## O que NÃO vai no Vercel

O **Energy Meter completo** (poller Tuya/Modbus, watchdog, APScheduler, gravação
no Postgres F:) **não roda no Vercel**.

Motivo: Vercel = funções serverless (segundos de vida). Coleta a cada **3 min**
e watchdog precisam de um processo **24/7** → isso fica na **cca-tecnica**
(`EnergyMeterServer.exe` no F:, ver `docs/SETUP_EXE_CCA_F.md`).

O antigo `api/index.py` + `vercel.json` na raiz tentavam hospedar o FastAPI no
Vercel — **não use** para produção com hardware real.

## Arquitetura correta

```text
Cliente (browser / link)
        │  HTTPS
        ▼
  Vercel  = portal/  (HTML estático, só leitura)
        │  fetch API
        ▼
  API pública read-only  ← Cloudflare Tunnel / Funnel / domínio
        │
        ▼
  cca-tecnica  Postgres F: + coleta 3 min + watchdog
        (Tailscale privado para você/admin)
```

## Portal neste repo

Pasta: [`portal/`](../portal/)

- Dashboard leve (Chart.js) só leitura
- Configura a URL da API em `portal/config.js`
- Deploy: `cd portal && vercel --yes`

## Passos para o cliente acompanhar

1. **CCA** coleta e grava no Postgres F: (oficial).
2. Exponha **só** a API de métricas com túnel HTTPS (ex.: Cloudflare Tunnel
   apontando para `http://127.0.0.1:8001` na CCA) — **não** abra `5432`.
3. Em `portal/config.js`:
   ```js
   window.PIENG_API_BASE = "https://seu-tunel.exemplo.com";
   ```
4. `cd portal && vercel --prod`
5. Cliente abre o link do Vercel (sem Tailscale).

## Isolamento multi-cliente (próximo passo)

- Token / `client_id` na API pública
- Portal não chama `/api/setup`, HOME admin, flush, etc.
- Ideal: endpoint `/api/public/...` filtrado (ainda a criar)

## Variáveis

| Onde | O quê |
|------|--------|
| CCA `.env` | `DATABASE_URL=...@127.0.0.1:5432/...` |
| CCA runtime | `collectors_interval_seconds=180`, watchdog on |
| `portal/config.js` | `PIENG_API_BASE` = URL HTTPS do túnel |

## Resumo

| Camada | Onde |
|--------|------|
| Coleta + banco | CCA / F: (exe) |
| Você (admin) | Tailscale → `cca-tecnica:8001` |
| Cliente (só ver) | Vercel `portal/` → API túnel |
