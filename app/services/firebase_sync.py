"""
Firebase Firestore - Backup em nuvem das leituras REAIS de hardware.

Grava UM documento por leitura de cada dispositivo (todas as métricas do poll
agrupadas em um único doc), e não um documento por métrica. Isso mantém o
volume de writes dentro da cota gratuita do Firestore mesmo com vários
equipamentos coletando a cada 30s (ver análise em CLAUDE.md/histórico de sessão).

Nunca deve derrubar um poller: qualquer falha aqui é logada e ignorada — o
SQLite local continua sendo a fonte de verdade dos dados.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger("pieng.firebase")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler("data/audit.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

_client = None
_init_attempted = False


def _get_client():
    """Inicializa o Firebase Admin SDK uma única vez (lazy singleton)."""
    global _client, _init_attempted

    if _client is not None:
        return _client

    if not settings.firebase_enabled:
        return None

    if _init_attempted:
        # já tentou antes e falhou; não fica tentando toda leitura
        return None
    _init_attempted = True

    if not settings.firebase_credentials_path:
        logger.warning("FIREBASE_DISABLED | motivo=FIREBASE_CREDENTIALS_PATH nao configurado")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred)

        _client = firestore.client()
        logger.info("FIREBASE_INIT_OK")
        return _client

    except ImportError:
        logger.error("FIREBASE_INIT_ERROR | motivo=firebase-admin nao instalado (pip install firebase-admin)")
        return None
    except Exception as e:
        logger.error(f"FIREBASE_INIT_ERROR | error={e}")
        return None


def push_reading(
    device_id: int,
    device_name: str,
    device_type: str,
    metrics: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> bool:
    """
    Grava uma leitura (todas as métricas de um poll) como UM documento no Firestore.

    Retorna True se gravou, False se Firebase está desabilitado/indisponível ou
    a gravação falhou — nos dois casos o chamador deve seguir normalmente, pois
    o SQLite local já é a cópia autoritativa do dado real.
    """
    if not metrics:
        return False

    client = _get_client()
    if client is None:
        return False

    try:
        doc = {
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "timestamp": timestamp or datetime.utcnow(),
            **metrics,
        }
        client.collection(settings.firebase_collection).add(doc)
        return True
    except Exception as e:
        logger.error(f"FIREBASE_WRITE_ERROR | device_id={device_id} | name={device_name} | error={e}")
        return False
