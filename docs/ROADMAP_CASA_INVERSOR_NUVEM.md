# Casa + inversor + nuvem (escritório como storage)

Atualizado: 2026-09-09

## Situação combinada

| Onde | Papel |
|------|--------|
| **Escritório (agora)** | Coletor Energy Meter + HD `K:\STORAGE` (Postgres espelho) + SQLite hot |
| **Casa (próximo)** | Novo medidor Tuya na **saída do inversor** → corrente realmente gerada/injetada |
| **Nuvem Tuya** | Mesmo usuário/projeto (`TUYA_ACCESS_ID` / secret no `.env`) |

## Dois pontos de medição (arquitetura)

1. **`grid_point`** — ponto de entrega / disjuntor (hoje: `medidorCASA`)  
   - Mede líquido rede ↔ casa (consumo e injeção no PON).  
   - Potência/corrente negativas = export líquido.

2. **`inverter_output`** — TC/medidor **na saída do inversor** (a instalar em casa)  
   - Mede a geração bruta do inversor (o que o usuário quer como “corrente realmente injetada/gerada”).  
   - Permite cruzar: geração inversor vs export líquido na rede vs consumo.

O sistema já grava `role` no `Device.config` ao incluir pela descoberta Tuya.

## Inclusão sem esforço (já implementado)

Na página **Dispositivos** (`/api/setup`):

1. Bloco **“Tuya na nuvem — incluir no projeto”**
2. Lista devices do mesmo projeto Cloud
3. Marca os já cadastrados
4. Sugere papel (`inverter_output` / `grid_point` / …)
5. Botão **Incluir no projeto** → `POST /api/devices/tuya/enroll`

APIs:

- `GET /api/devices/tuya/discover`
- `POST /api/devices/tuya/enroll`

Fluxo em casa: parear o medidor no app Tuya (mesmo projeto IoT) → abrir Setup no Energy Meter → Procurar na nuvem → Incluir como **Saída do inversor**.

## Storage no escritório (mantém)

- Hot: SQLite no NVMe do PC do escritório  
- Espelho: Postgres nativo em `K:\storage\postgres\energy_meter\pgdata`  
- Flush configurável em `/api/db`  
- Docker compose preservado para o mini PC futuro

## Acesso “na nuvem” / de fora do escritório

O coletor continua no PC do escritório. Para entrar de casa sem VPN complexa, opções (escolher uma):

| Opção | Esforço | Notas |
|-------|---------|--------|
| **A) Cloudflare Tunnel / Tailscale** no PC do escritório | Médio | Expõe `uvicorn` com HTTPS seguro; ideal para Dashboard remoto |
| **B) Firebase** (já no código, desligado) | Baixo p/ ligar | Backup/leituras na nuvem; não substitui o painel completo |
| **C) Mini PC em casa + sync** | Alto | Futuro Fidelco; `pg_dump` do K: ou dual-write |

Recomendação imediata (atualizada **2026-09-10**): medição contínua preferir
**Elfin/PZEM (Modbus local) + spool → Postgres central**; Tuya Cloud só pontual.
Ver `docs/ESTRATEGIA_SPOOL_LOCAL_NUVEM.md`. Tailscale continua para acesso remoto
ao storage/API. O medidor do inversor, quando possível, também em Modbus/LAN
em vez de poll Tuya 30 s.

## Próximos passos de código (quando o medidor do inversor existir)

1. Incluir via discover com role `inverter_output`
2. No `solar_summary` / Dashboard: card “Geração inversor” usando esse device  
3. Comparar `inverter_output.power` vs `grid_point.power_export_total` (perdas / autoconsumo)
4. Expor acesso remoto (Tunnel/Tailscale)

## Premissa solar (já vigente)

Potência/corrente negativas no ponto de rede = injeção líquida.  
Corrente na saída do inversor = geração real (quando o 2º medidor estiver ativo).
