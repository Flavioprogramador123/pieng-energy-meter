# HOME — Direção visual e escolha de stack

Status: **em avaliação** (decidido em 2026-09-09, noite).

## Problema

A tela atual (`/home`, HTML+CSS+JS puro servido pelo FastAPI) é funcional, mas
visualmente fraca para o uso real: **celular e tablet**, com o dedo, em casa.
Falta identidade "tecnológica": vibração de cor, ícones que remetam a luz,
interruptor, tomada, portão, TV, e feedback animado do estado.

## Objetivo

Painel residencial com cara de produto, não de formulário:

- fundo escuro, cores vibrantes, cartões translúcidos;
- figuras/ícones que remetem ao objeto real (lâmpada acende, portão sobe,
  cortina corre, TV liga);
- ação principal em **um toque**, botão grande;
- animações de **300–700 ms**;
- estado sempre explícito: ligado / desligado / abrindo / fechando /
  **indisponível (offline)**;
- modo simples de fallback se a cena pesada travar;
- o estado nunca depende só do desenho — sempre há texto/badge junto;
- tolerante a queda de rede momentânea.

## Stack "topo de linha" avaliada (alvo futuro)

| Necessidade | Tecnologia |
|---|---|
| Interface principal | React + TypeScript |
| Visual 3D | **Babylon.js** (preferido) ou Three.js |
| Animações de UI | Framer Motion |
| Estilo | Tailwind CSS |
| Execução no tablet | PWA em modo kiosk / tela cheia |
| Transporte de estado | WebSocket |

**Babylon.js** é o preferido no lugar de Three.js: já traz câmera, iluminação,
sombras, animação, `.glb`/`.gltf`, interação por toque e boa performance em
móvel — mais perto de "painel de automação" do que de engine crua.

Ideia de tela: casa 3D estilizada no centro (tocar na lâmpada acende e muda a
iluminação da cena; tocar na TV abre painel lateral; tocar no portão anima a
abertura), topo com hora/temperatura/clima/status e rodapé com ambientes
(Sala, Quarto, Cozinha, Garagem, Jardim).

## Ajuste importante para o nosso caso

A referência original assume **Home Assistant** e sua WebSocket API.
**Este projeto não usa Home Assistant.** A fonte de verdade é o próprio backend:

- `GET /home/api/devices` — lista + estado + `online`
- `GET /home/api/catalog` — conhecimento dos devices
- `POST /home/api/devices/{id}/switch` — liga/desliga (com `code` do canal)
- `POST /home/api/devices/{id}/ac/power` e `/ac/temp`

Ou seja: onde a receita diz "Home Assistant WebSocket", aqui será **a REST
atual** e, se a atualização em tempo real virar gargalo, um **WebSocket próprio
no FastAPI** publicando mudanças de estado. Autenticação também é nossa, não
token do HA.

## Alternativas consideradas

- **Lovelace + Mushroom/Bubble Cards** — descartado: exigiria Home Assistant.
- **Flutter** — app nativo Android/iPad, toque refinado, animação boa;
  cena 3D complexa é mais trabalhosa que no React+Babylon.
- **Unity** — só se virasse casa virtual navegável; pesado demais para painel.

## Decisão desta sessão

Vamos **testar vários frameworks** antes de fixar. Começar pelo caminho
**simples** (Flutter como app de painel), deixando React + Babylon.js como
evolução quando a base de dados/estado estiver estável.

Regra que não muda em nenhum protótipo: **só dados reais** da Tuya, e device
offline aparece marcado e sem comando.
