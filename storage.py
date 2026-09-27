"""
Guarda qué anuncios ya hemos visto, para no notificar dos veces el mismo.

Versión Supabase: ya no usamos vistos.json local (no encajaba con tener
usuarios y muchos más anuncios acumulados). En su lugar, cada anuncio
encontrado se intenta insertar en la tabla "vistos" de Supabase; los que
Postgres rechaza por ya existir (clave duplicada) son los que ya
conocíamos, y los que acepta son los realmente nuevos. Así no hace falta
descargar el histórico completo en cada ejecución, por muy grande que se
haga con el tiempo.

Necesita dos variables de entorno:
- SUPABASE_URL: la URL de tu proyecto (https://xxxx.supabase.co)
- SUPABASE_SERVICE_KEY: la "service_role key" (Settings -> API en Supabase).
  Solo debe estar en GitHub Secrets / tu .env local, nunca en código
  público: esta clave salta las políticas de seguridad de fila.
"""

import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates,return=representation",
}


def marcar_nuevos(claves: list[str]) -> set:
    """
    Recibe las claves (formato "portal:id") de los anuncios encontrados en
    esta pasada. Inserta en Supabase las que no existieran ya y devuelve el
    subconjunto que la base de datos aceptó, es decir, las realmente nuevas.

    Si Supabase no está configurado todavía (SUPABASE_URL/SUPABASE_SERVICE_KEY
    vacíos), avisa por consola y trata todo como nuevo, para que el scraper
    siga funcionando en local con el comportamiento antiguo mientras montas
    Supabase.
    """
    if not claves:
        return set()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  Falta configurar SUPABASE_URL / SUPABASE_SERVICE_KEY. "
              "Tratando todos los anuncios de esta pasada como nuevos.")
        return set(claves)

    payload = [{"clave": c} for c in claves]
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/vistos",
            headers=HEADERS,
            params={"on_conflict": "clave"},
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        return {fila["clave"] for fila in r.json()}
    except requests.RequestException as e:
        print(f"⚠️  Error consultando Supabase (tabla vistos): {e}")
        # Ante un fallo de red/DB, no notificamos nada en esta pasada para no
        # arriesgarnos a duplicar avisos si el error fuera intermitente.
        return set()
