"""Trava de instância única para os coletores (pollers) e o flush Postgres.

Problema real encontrado em 2026-09-09: dois processos uvicorn (portas 8000 e
8001) ficaram rodando ao mesmo tempo, cada um com seu próprio scheduler —
resultado: o disjuntor Tuya era consultado ~2x mais rápido que o previsto
(API Cloud da Tuya no data center US) e o flush pro Postgres no HD K: rodava
em dobro, justamente o oposto do que se queria (reduzir I/O na peça mecânica).

Solução: trava de arquivo em nível de SO (`msvcrt.locking` no Windows,
`fcntl.flock` em POSIX). O primeiro processo a conseguir a trava vira "dono"
dos pollers/flush; qualquer outro processo iniciado depois (ex.: uma segunda
instância de teste noutra porta) continua servindo a API/Dashboard
normalmente a partir do mesmo SQLite, mas NÃO inicia scheduler nenhum — não
duplica requisição de hardware/nuvem nem escrita no HD. A trava é liberada
automaticamente pelo SO se o processo cair (crash, kill -9, etc.), então
nunca fica "presa" precisando limpeza manual.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_LOCK_PATH = Path("data/.scheduler.lock")
_handle = None  # mantido aberto pela vida do processo — é o que sustenta a trava


def acquire_scheduler_lock() -> bool:
    """Tenta se tornar o dono único dos pollers/flush neste host.

    Retorna True se este processo deve rodar o scheduler, False se outro
    processo já é o dono (então este só serve API/Dashboard, sem coletar).
    """
    global _handle
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    f = open(_LOCK_PATH, "a+")
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return False

    f.seek(0)
    f.truncate()
    f.write(str(os.getpid()))
    f.flush()
    _handle = f  # não fechar: fechar/o processo sair libera a trava pro SO
    return True
