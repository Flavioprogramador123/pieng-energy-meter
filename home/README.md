# PIENG HOME

Módulo separado do Energy Meter para controle residencial via Tuya Cloud.
Foco: celular / tablet — luzes, interruptores, ar, sensores e gateway.

## URLs (backend Energy Meter rodando)

- Interface: http://localhost:8001/home
- Listar devices: GET /home/api/devices
- Catálogo de conhecimento: GET /home/api/catalog
- Ligar/desligar: POST /home/api/devices/{id}/switch
  `{ "on": true, "code": "switch_2" }`
- Interruptores com vários circuitos exibem uma linha por tecla
  (`switch_1`, `switch_2`, `switch_3`).
- AC power: POST /home/api/devices/{id}/ac/power  `{ "on": true }`
- AC temp: POST /home/api/devices/{id}/ac/temp  `{ "temp": 24 }`

## Conhecimento dos devices

Arquivo canônico: `home/device_catalog.json`

- Guarda categorias, DPs, escalas, hub IR, teclas validadas e códigos proibidos.
- O engine (`home/tuya_client.py` + `home/static/home.js`) lê esse JSON para montar os cards.
- Durante os testes, qualquer discovery novo deve ir primeiro para o JSON e depois para a UI.
- `factory_reset` do gateway fica bloqueado.

Credenciais: reutiliza `TUYA_*` do `.env` na raiz do projeto.

Branch: `feature/home-module`
