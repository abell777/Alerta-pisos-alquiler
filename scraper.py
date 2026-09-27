"""
Scraper de anuncios de alquiler — orquestador multi-portal y multi-usuario.

Cada portal tiene su propio parser en fuentes/<portal>.py, con una función
parsear(html) que devuelve una lista de anuncios en formato común:
{portal, id, titulo, subtitulo, url, precio, m2, habitaciones, banos}

Flujo de cada ejecución:
1. Procesa los mensajes que la gente le haya mandado al bot (/alta, /baja)
   y actualiza sus filtros en Supabase (registro.py).
2. Carga la lista de filtros activos (filtros.py).
3. Para cada búsqueda configurada: descarga, parsea, y marca en Supabase
   qué anuncios son nuevos de verdad (storage.py).
4. Cada anuncio nuevo se compara contra el filtro de cada persona activa;
   si encaja, se le manda por Telegram solo a ella.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()  # antes de leer nada de os.environ

import storage
import registro
from filtros import cargar_filtros_activos, anuncio_coincide
from notifier import enviar_telegram
from fuentes import enalquiler, trovimap, pisos

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
DELAY_ENTRE_PETICIONES = 3  # segundos, cortesía con el servidor

# Se usa solo si todavía no hay nadie registrado en Supabase (o Supabase no
# está configurado), para no perder el comportamiento de las primeras
# semanas: todo se manda a tu chat personal.
CHAT_ID_RESPALDO = os.environ.get("TELEGRAM_CHAT_ID")

# Cada entrada: (nombre_para_ti, url, función_parsear_del_portal)
BUSQUEDAS = [
    ("Valencia - piso particular", "https://www.enalquiler.com/alquilar/alquiler-piso-particular-valencia_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Exposició", "https://www.enalquiler.com/alquilar/alquiler-pisos-exposicio_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Malvarrosa/Patacona", "https://www.enalquiler.com/alquilar/alquiler-pisos-malvarrosa-patacona_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Plana", "https://www.enalquiler.com/alquilar/alquiler-pisos-plana-valencia_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Trovimap", "https://www.trovimap.com/alquiler/vivienda/Valencia/Valencia", trovimap.parsear),
    ("Valencia - Pisos.com", "https://www.pisos.com/alquiler/pisos-valencia_capital_zona_urbana/", pisos.parsear),
]


def formatear_mensaje(anuncio: dict, nombre_busqueda: str) -> str:
    partes = [f"🏠 Nuevo anuncio ({nombre_busqueda})", anuncio["titulo"]]
    datos = []
    if anuncio.get("precio"):
        datos.append(f"{anuncio['precio']}€")
    if anuncio.get("m2"):
        datos.append(f"{anuncio['m2']} m²")
    if anuncio.get("habitaciones"):
        datos.append(f"{anuncio['habitaciones']} hab")
    if anuncio.get("banos"):
        datos.append(f"{anuncio['banos']} baños")
    if datos:
        partes.append(" · ".join(datos))
    partes.append(anuncio["url"])
    return "\n".join(partes)


def notificar_anuncio(anuncio: dict, nombre_busqueda: str, filtros_activos: list[dict]) -> None:
    mensaje = formatear_mensaje(anuncio, nombre_busqueda)

    if not filtros_activos:
        # Todavía nadie registrado (o Supabase sin configurar): comportamiento
        # antiguo, todo va a tu chat fijo.
        if CHAT_ID_RESPALDO:
            enviar_telegram(mensaje, CHAT_ID_RESPALDO)
        return

    for filtro in filtros_activos:
        if anuncio_coincide(anuncio, nombre_busqueda, filtro):
            enviar_telegram(mensaje, filtro["chat_id"])


def revisar_busqueda(nombre: str, url: str, parsear, filtros_activos: list[dict]) -> int:
    print(f"Revisando: {nombre}...")
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=15)
        respuesta.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Error descargando la página: {e}")
        return 0

    anuncios = parsear(respuesta.text)
    print(f"  {len(anuncios)} anuncios encontrados en la página.")

    claves = [f"{a['portal']}:{a['id']}" for a in anuncios]
    claves_nuevas = storage.marcar_nuevos(claves)

    nuevos = 0
    for anuncio in anuncios:
        clave = f"{anuncio['portal']}:{anuncio['id']}"
        if clave not in claves_nuevas:
            continue
        nuevos += 1
        notificar_anuncio(anuncio, nombre, filtros_activos)
        print(f"  ✅ Nuevo anuncio notificado: {anuncio['titulo']}")

    return nuevos


def main():
    registro.procesar_mensajes_pendientes()
    filtros_activos = cargar_filtros_activos()

    total_nuevos = 0
    for nombre, url, parsear in BUSQUEDAS:
        total_nuevos += revisar_busqueda(nombre, url, parsear, filtros_activos)
        time.sleep(DELAY_ENTRE_PETICIONES)

    print(f"Listo. {total_nuevos} anuncio(s) nuevo(s) en total.")


if __name__ == "__main__":
    main()
