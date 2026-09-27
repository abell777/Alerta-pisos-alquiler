"""
Procesa lo que la gente le escribe directamente a tu bot de Telegram para
darse de alta/baja en las alertas, y guarda su filtro en Supabase.

Comandos que entiende:
  /start                          -> explica los comandos
  /alta                           -> recibir TODOS los anuncios nuevos
  /alta zona=Russafa              -> solo cuando el anuncio menciona esa zona
  /alta zona=Ciutat Vella precio_max=900
  /alta precio_min=500 precio_max=1000
  /baja                           -> dejar de recibir avisos
  /estado                         -> recordatorio de los comandos

Se llama una vez al principio de cada ejecución del scraper (cada 5 min),
leyendo solo los mensajes nuevos desde el último que se procesó (el
"offset" se guarda en la tabla bot_estado de Supabase para no perder la
cuenta entre una ejecución y la siguiente).
"""

import os
import re
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

AYUDA = (
    "Comandos disponibles:\n"
    "/alta — recibir todos los avisos\n"
    "/alta zona=Russafa — solo esa zona\n"
    "/alta zona=Ciutat Vella precio_max=900\n"
    "/alta precio_min=500 precio_max=1000\n"
    "/baja — dejar de recibir avisos"
)


def _leer_offset() -> int:
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/bot_estado",
            headers=HEADERS_SB,
            params={"id": "eq.1", "select": "ultimo_update_id"},
            timeout=10,
        )
        r.raise_for_status()
        filas = r.json()
        return filas[0]["ultimo_update_id"] if filas else 0
    except requests.RequestException as e:
        print(f"⚠️  Error leyendo el offset del bot: {e}")
        return 0


def _guardar_offset(update_id: int) -> None:
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/bot_estado",
            headers={**HEADERS_SB, "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "id"},
            json={"id": 1, "ultimo_update_id": update_id},
            timeout=10,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️  Error guardando el offset del bot: {e}")


def _responder(chat_id: int, texto: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": texto},
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"⚠️  Error respondiendo por Telegram: {e}")


def _extraer_parametros(texto: str) -> dict:
    """De "/alta zona=Ciutat Vella precio_max=900" saca
    {"zona": "Ciutat Vella", "precio_max": "900"}. Admite valores con
    espacios (nombres de zona de varias palabras)."""
    patron = re.compile(r"(zona|precio_min|precio_max)=", re.IGNORECASE)
    coincidencias = list(patron.finditer(texto))
    resultado = {}
    for i, m in enumerate(coincidencias):
        clave = m.group(1).lower()
        inicio = m.end()
        fin = coincidencias[i + 1].start() if i + 1 < len(coincidencias) else len(texto)
        resultado[clave] = texto[inicio:fin].strip()
    return resultado


def procesar_mensajes_pendientes() -> None:
    if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
        return  # todavía no está todo configurado; el scraper sigue funcionando igual

    from filtros import upsert_filtro, desactivar_filtro

    offset = _leer_offset()
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": offset + 1, "timeout": 0},
            timeout=15,
        )
        r.raise_for_status()
        actualizaciones = r.json().get("result", [])
    except requests.RequestException as e:
        print(f"⚠️  Error consultando mensajes de Telegram: {e}")
        return

    ultimo_id = offset
    for act in actualizaciones:
        ultimo_id = max(ultimo_id, act["update_id"])
        mensaje = act.get("message", {})
        texto = (mensaje.get("text") or "").strip()
        chat_id = mensaje.get("chat", {}).get("id")
        if not texto or not chat_id:
            continue

        if texto.startswith("/alta"):
            params = _extraer_parametros(texto)
            zona = params.get("zona") or None
            precio_min = int(params["precio_min"]) if params.get("precio_min", "").isdigit() else None
            precio_max = int(params["precio_max"]) if params.get("precio_max", "").isdigit() else None

            if upsert_filtro(chat_id, zona, precio_min, precio_max):
                resumen = []
                if zona:
                    resumen.append(f"zona: {zona}")
                if precio_min:
                    resumen.append(f"desde {precio_min}€")
                if precio_max:
                    resumen.append(f"hasta {precio_max}€")
                detalle = " · ".join(resumen) if resumen else "sin filtro (todos los anuncios)"
                _responder(chat_id, f"✅ Alta hecha. Recibirás avisos con: {detalle}\n\nPuedes cambiarlo mandando otro /alta, o /baja para parar.")
            else:
                _responder(chat_id, "⚠️ No he podido guardar tu alta, inténtalo en un rato.")

        elif texto.startswith("/baja"):
            if desactivar_filtro(chat_id):
                _responder(chat_id, "🛑 Baja hecha. Ya no recibirás avisos. Manda /alta cuando quieras volver.")
            else:
                _responder(chat_id, "⚠️ No he podido procesar tu baja, inténtalo en un rato.")

        else:  # /start, /estado, o cualquier otra cosa
            _responder(chat_id, AYUDA)

    if ultimo_id > offset:
        _guardar_offset(ultimo_id)
