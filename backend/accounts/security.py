"""AGROTECH accounts — seguridad transversal (FASE 4).

Backoff progresivo (segunda capa tras throttling) y registro de eventos
de seguridad. Regla: NUNCA pasar por aquí passwords, OTP, tokens,
cookies de sesión, SECRET_KEY ni secretos.
"""

import logging
import time

from django.conf import settings
from django.core.cache import cache

sec = logging.getLogger("agrotech.security")


def audit(event: str, **fields) -> None:
    """Evento de auditoría. Solo datos operativos (p. ej. user_id, email)."""
    safe = {k: v for k, v in fields.items() if v is not None}
    sec.info("%s %s", event, safe)


def _backoff_cfg(prefix: str):
    return {
        "threshold": int(getattr(settings, f"BACKOFF_{prefix}_THRESHOLD", 5)),
        "window": int(getattr(settings, f"BACKOFF_{prefix}_WINDOW_SECONDS", 900)),
        "base": int(getattr(settings, f"BACKOFF_{prefix}_BASE_SECONDS", 30)),
        "max": int(getattr(settings, f"BACKOFF_{prefix}_MAX_SECONDS", 300)),
    }


def backoff_wait(key: str, prefix: str) -> int:
    """Segundos de espera vigentes (0 = libre). Ventana deslizante."""
    cfg = _backoff_cfg(prefix)
    state = cache.get(f"agrotech:backoff:{prefix}:{key}")
    if not state:
        return 0
    fails, first = state
    if time.time() - first > cfg["window"]:
        cache.delete(f"agrotech:backoff:{prefix}:{key}")
        return 0
    if fails < cfg["threshold"]:
        return 0
    return min(cfg["base"] * 2 ** (fails - cfg["threshold"]), cfg["max"])


def backoff_fail(key: str, prefix: str) -> int:
    """Registra un fallo y devuelve la espera resultante."""
    cfg = _backoff_cfg(prefix)
    ck = f"agrotech:backoff:{prefix}:{key}"
    state = cache.get(ck)
    now = time.time()
    if not state or now - state[1] > cfg["window"]:
        state = [0, now]
    state[0] += 1
    cache.set(ck, state, cfg["window"])
    return backoff_wait(key, prefix)


def backoff_clear(key: str, prefix: str) -> None:
    cache.delete(f"agrotech:backoff:{prefix}:{key}")
