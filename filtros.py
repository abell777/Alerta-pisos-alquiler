"""
Filtros de cada persona registrada (zona y rango de precio), guardados en la
tabla "usuarios_filtros" de Supabase. Se dan de alta/baja hablando con el bot
de Telegram (ver registro.py); este archivo solo lee/escribe Supabase y
decide si un anuncio concreto encaja con el filtro de alguien.
"""

import os
import unicodedata
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    ).lower()


def cargar_filtros_activos() -> list[dict]:
    """Devuelve la lista de filtros con activo=true. Lista vacía si Supabase
    no está configurado o si falla la consulta (así el scraper no revienta,
    simplemente no reparte avisos personalizados esa pasada)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/usuarios_filtros",
            headers=HEADERS,
            params={"activo": "eq.true", "select": "*"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"⚠️  Error cargando filtros de Supabase: {e}")
        return []


def anuncio_coincide(anuncio: dict, nombre_busqueda: str, filtro: dict) -> bool:
    """nombre_busqueda es la etiqueta de la búsqueda (p.ej. "Valencia -
    Exposició"), que ayuda a matchear zona en portales cuyo anuncio no trae
    el barrio explícito en el título."""
    zona = filtro.get("zona")
    if zona:
        texto = _sin_acentos(
            f"{anuncio.get('titulo', '')} {anuncio.get('subtitulo', '')} {nombre_busqueda}"
        )
        if _sin_acentos(zona) not in texto:
            return False

    precio = anuncio.get("precio")
    if precio:
        try:
            precio_num = int(str(precio).replace(".", "").replace(",", ""))
        except ValueError:
            precio_num = None
        if precio_num is not None:
            if filtro.get("precio_min") and precio_num < filtro["precio_min"]:
                return False
            if filtro.get("precio_max") and precio_num > filtro["precio_max"]:
                return False

    return True


def upsert_filtro(chat_id: int, zona: str | None, precio_min: int | None, precio_max: int | None) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    payload = {
        "chat_id": chat_id,
        "zona": zona,
        "precio_min": precio_min,
        "precio_max": precio_max,
        "activo": True,
    }
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/usuarios_filtros",
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
            params={"on_conflict": "chat_id"},
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Error guardando filtro en Supabase: {e}")
        return False


def desactivar_filtro(chat_id: int) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/usuarios_filtros",
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}"},
            json={"activo": False},
            timeout=15,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Error desactivando filtro en Supabase: {e}")
        return False
