"""
Filtros de cada persona registrada (ciudad, zona, precio, habitaciones mínimas y m² mínimos), guardados
en la tabla "usuarios_filtros" de Supabase. Se dan de alta/baja hablando con
el bot de Telegram (ver registro.py); este archivo solo lee/escribe Supabase
y decide si un anuncio concreto encaja con el filtro de alguien.
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

CIUDAD_POR_DEFECTO = "valencia"


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    ).lower()


def _a_entero(valor):
    try:
        return int(str(valor).replace(".", "").replace(",", ""))
    except (ValueError, TypeError):
        return None


def cargar_filtros_activos() -> list[dict]:
    """Devuelve la lista de filtros con activo=true. Lista vacía si Supabase
    no está configurado o si falla la consulta."""
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


def obtener_ciudades_activas(filtros_activos: list[dict] | None = None) -> set:
    """Ciudades que hay que vigilar esta pasada: todas las que tengan al
    menos una persona registrada, más Valencia siempre (para no perder
    cobertura de tu ciudad base aunque todavía no se haya registrado nadie
    ahí explícitamente, y para que el scraper siga funcionando igual que
    antes si Supabase no está configurado)."""
    if filtros_activos is None:
        filtros_activos = cargar_filtros_activos()
    ciudades = {_sin_acentos(f["ciudad"]) for f in filtros_activos if f.get("ciudad")}
    ciudades.add(CIUDAD_POR_DEFECTO)
    return ciudades


def anuncio_coincide(anuncio: dict, nombre_busqueda: str, filtro: dict) -> bool:
    """nombre_busqueda es la etiqueta de la búsqueda (p.ej. "Valencia -
    enalquiler"), que ayuda a matchear zona en portales cuyo anuncio no trae
    el barrio explícito en el título."""
    if filtro.get("ciudad") and anuncio.get("ciudad"):
        if _sin_acentos(filtro["ciudad"]) != _sin_acentos(anuncio["ciudad"]):
            return False

    zona = filtro.get("zona")
    if zona:
        texto = _sin_acentos(
            f"{anuncio.get('titulo', '')} {anuncio.get('subtitulo', '')} {nombre_busqueda}"
        )
        # varias zonas separadas por coma: basta con que encaje una (Russafa, Ruzafa)
        zonas = [_sin_acentos(z).strip() for z in zona.split(",") if z.strip()]
        if zonas and not any(z in texto for z in zonas):
            return False

    # Si el portal no informa de habitaciones/m2, dejamos pasar el anuncio
    # (mejor un aviso de más que perder un piso bueno).
    if filtro.get("habs_min"):
        habs = _a_entero(anuncio.get("habitaciones"))
        if habs is not None and habs < filtro["habs_min"]:
            return False
    if filtro.get("m2_min"):
        m2 = _a_entero(anuncio.get("m2"))
        if m2 is not None and m2 < filtro["m2_min"]:
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


def upsert_filtro(chat_id: int, ciudad: str, zona: str | None, precio_min: int | None, precio_max: int | None,
                  habs_min: int | None = None, m2_min: int | None = None) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    payload = {
        "chat_id": chat_id,
        "ciudad": (ciudad or CIUDAD_POR_DEFECTO).strip().lower(),
        "zona": zona,
        "precio_min": precio_min,
        "precio_max": precio_max,
        "habs_min": habs_min,
        "m2_min": m2_min,
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


def obtener_filtro(chat_id: int) -> dict | None:
    """Filtro guardado de una persona (para /estado). None si no tiene."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/usuarios_filtros",
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "select": "*"},
            timeout=15,
        )
        r.raise_for_status()
        filas = r.json()
        return filas[0] if filas else None
    except requests.RequestException as e:
        print(f"⚠️  Error leyendo el filtro de {chat_id}: {e}")
        return None


def borrar_datos(chat_id: int) -> bool:
    """Derecho de supresión (RGPD): elimina por completo los datos de la persona."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/usuarios_filtros",
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}"},
            timeout=15,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Error borrando datos de {chat_id}: {e}")
        return False
