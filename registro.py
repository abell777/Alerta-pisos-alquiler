"""
Procesa lo que la gente le escribe directamente a tu bot de Telegram para
darse de alta/baja en las alertas, y guarda su filtro en Supabase.

Comandos que entiende:
  /start                          -> explica los comandos
  /alta                           -> Valencia, todos los anuncios nuevos
  /alta ciudad=Madrid             -> todos los anuncios nuevos de Madrid
  /alta ciudad=Madrid zona=Chamberí precio_max=900
  /alta zona=Russafa              -> Valencia (por defecto) + esa zona
  /baja                           -> dejar de recibir avisos
  /alta ... habs=2 m2=60          -> habitaciones y m² mínimos
  /estado                         -> ver tu filtro actual
  /borrar /privacidad             -> RGPD

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
    "🏠 Alertas de pisos en alquiler, al instante.\n\n"
    "/alta — Valencia, todos los avisos\n"
    "/alta ciudad=Madrid zona=Chamberí precio_max=900 habs=2 m2=60\n"
    "  · zona: admite varias separadas por coma (zona=Russafa,Ruzafa)\n"
    "  · habs: habitaciones mínimas · m2: metros mínimos\n"
    "/estado — ver tu filtro actual\n"
    "/baja — pausar avisos\n"
    "/borrar — eliminar todos mis datos\n"
    "/privacidad — qué datos guardo"
)

PRIVACIDAD = (
    "🔒 Privacidad: solo guardo tu identificador de Telegram y el filtro que "
    "configuras (ciudad, zona, precio, habitaciones, m²). Lo uso únicamente para "
    "enviarte avisos de pisos; no lo vendo ni lo comparto. "
    "Con /borrar lo elimino por completo cuando quieras."
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
    """De "/alta ciudad=Madrid zona=Chamberí precio_max=900" saca
    {"ciudad": "Madrid", "zona": "Chamberí", "precio_max": "900"}. Admite
    valores con espacios (nombres de ciudad/zona de varias palabras)."""
    patron = re.compile(r"(ciudad|zona|precio_min|precio_max|habs|m2)=", re.IGNORECASE)
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

    from filtros import upsert_filtro, desactivar_filtro, obtener_filtro, borrar_datos

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
            ciudad = params.get("ciudad") or "valencia"
            zona = params.get("zona") or None
            precio_min = int(params["precio_min"]) if params.get("precio_min", "").isdigit() else None
            precio_max = int(params["precio_max"]) if params.get("precio_max", "").isdigit() else None

            habs_min = int(params["habs"]) if params.get("habs", "").isdigit() else None
            m2_min = int(params["m2"]) if params.get("m2", "").isdigit() else None

            if upsert_filtro(chat_id, ciudad, zona, precio_min, precio_max, habs_min, m2_min):
                resumen = [f"ciudad: {ciudad}"]
                if zona:
                    resumen.append(f"zona: {zona}")
                if precio_min:
                    resumen.append(f"desde {precio_min}€")
                if precio_max:
                    resumen.append(f"hasta {precio_max}€")
                if habs_min:
                    resumen.append(f"{habs_min}+ hab")
                if m2_min:
                    resumen.append(f"{m2_min}+ m²")
                detalle = " · ".join(resumen)
                _responder(chat_id, f"✅ Alta hecha. Recibirás avisos con: {detalle}\n\nPuedes cambiarlo mandando otro /alta, o /baja para parar.")
            else:
                _responder(chat_id, "⚠️ No he podido guardar tu alta, inténtalo en un rato.")

        elif texto.startswith("/baja"):
            if desactivar_filtro(chat_id):
                _responder(chat_id, "🛑 Baja hecha. Ya no recibirás avisos. Manda /alta cuando quieras volver.")
            else:
                _responder(chat_id, "⚠️ No he podido procesar tu baja, inténtalo en un rato.")

        elif texto.startswith("/estado"):
            f = obtener_filtro(chat_id)
            if not f:
                _responder(chat_id, "No tienes ningún filtro. Crea uno con /alta")
            else:
                partes = [f"ciudad: {f.get('ciudad')}"]
                if f.get("zona"): partes.append(f"zona: {f['zona']}")
                if f.get("precio_min"): partes.append(f"desde {f['precio_min']}€")
                if f.get("precio_max"): partes.append(f"hasta {f['precio_max']}€")
                if f.get("habs_min"): partes.append(f"{f['habs_min']}+ hab")
                if f.get("m2_min"): partes.append(f"{f['m2_min']}+ m²")
                estado = "✅ activo" if f.get("activo") else "⏸️ en pausa (/alta para reactivar)"
                _responder(chat_id, f"Tu filtro: {' · '.join(partes)}\nEstado: {estado}")

        elif texto.startswith("/borrar"):
            ok = borrar_datos(chat_id)
            _responder(chat_id, "🗑️ Todos tus datos han sido eliminados." if ok else "⚠️ No he podido borrar tus datos, inténtalo en un rato.")

        elif texto.startswith("/privacidad"):
            _responder(chat_id, PRIVACIDAD)

        elif texto.startswith("/start"):
            _responder(chat_id, AYUDA + "\n\n" + PRIVACIDAD)

        else:
            _responder(chat_id, AYUDA)

    if ultimo_id > offset:
        _guardar_offset(ultimo_id)
