"""
Cola de avisos con retraso para el plan gratis.

Los usuarios premium reciben el aviso al instante; los gratis lo reciben
RETRASO_GRATIS_MIN minutos después (por defecto 30). Al detectar un piso
nuevo se guarda el mensaje en la tabla "cola_retardo" de Supabase con su hora
de envío, y cada ejecución del scraper (cada 5 min) manda los que ya vencieron.
"""

import os
from datetime import datetime, timedelta, timezone

import requests

from notifier import enviar_telegram

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}
try:
    RETRASO_MIN = int(os.environ.get("RETRASO_GRATIS_MIN", "30"))
except ValueError:
    RETRASO_MIN = 30

PIE_GRATIS = "\n\n⏱️ Aviso con retraso (plan gratis). Con /premium los recibes al instante."


def encolar(chat_id, mensaje: str) -> bool:
    enviar_a = datetime.now(timezone.utc) + timedelta(minutes=RETRASO_MIN)
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/cola_retardo",
            headers={**HEADERS, "Prefer": "return=minimal"},
            json={"chat_id": chat_id, "mensaje": mensaje + PIE_GRATIS, "enviar_a": enviar_a.isoformat()},
            timeout=15,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Error encolando aviso para {chat_id}: {e}")
        return False


def enviar_vencidos() -> int:
    """Manda los avisos cuya hora ya pasó y los borra de la cola."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return 0
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/cola_retardo",
            headers=HEADERS,
            params={
                "enviar_a": f"lte.{datetime.now(timezone.utc).isoformat()}",
                "select": "id,chat_id,mensaje",
                "order": "id.asc",
                "limit": "300",
            },
            timeout=15,
        )
        r.raise_for_status()
        pendientes = r.json()
    except requests.RequestException as e:
        print(f"⚠️  Error leyendo la cola de avisos: {e}")
        return 0

    enviados = 0
    for p in pendientes:
        if enviar_telegram(p["mensaje"], p["chat_id"]):
            enviados += 1
        # se borra igualmente: si el usuario bloqueó el bot, no reintentar eternamente
        try:
            requests.delete(
                f"{SUPABASE_URL}/rest/v1/cola_retardo",
                headers=HEADERS, params={"id": f"eq.{p['id']}"}, timeout=10,
            )
        except requests.RequestException as e:
            print(f"⚠️  No pude borrar el aviso {p['id']} de la cola: {e}")
    if pendientes:
        print(f"Cola: {enviados}/{len(pendientes)} avisos con retraso enviados.")
    return enviados
