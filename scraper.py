"""
Scraper de anuncios de alquiler — orquestador multi-portal, multi-ciudad y
multi-usuario.

Cada portal tiene su propio parser en fuentes/<portal>.py, con:
- parsear(html) -> lista de anuncios {portal, id, titulo, subtitulo, url,
  precio, m2, habitaciones, banos}
- url_ciudad(ciudad) -> URL de búsqueda de ese portal para esa ciudad

Ya no hay una lista fija de búsquedas: cada ejecución mira qué ciudades
tienen a alguien registrado en Supabase (más Valencia siempre, como base) y
construye sobre la marcha las 3 URLs (una por portal) para cada una. Así el
scraper crece solo según quién se vaya registrando, sin tener que tocar
código para añadir una ciudad nueva.

Flujo de cada ejecución:
1. Procesa los mensajes que la gente le haya mandado al bot (/alta, /baja).
2. Carga los filtros activos y calcula qué ciudades vigilar.
3. Para cada (ciudad, portal): descarga, parsea, marca en Supabase qué
   anuncios son nuevos de verdad.
4. Cada anuncio nuevo se compara contra el filtro de cada persona activa
   (ciudad, zona, precio); si encaja, se le manda por Telegram solo a ella.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

import storage
import registro
from filtros import cargar_filtros_activos, obtener_ciudades_activas, anuncio_coincide
from notifier import enviar_telegram
from fuentes import enalquiler, trovimap, pisos
from fuentes.utils import decodificar

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
DELAY_ENTRE_PETICIONES = 3  # segundos, cortesía con el servidor

# Se usa solo si todavía no hay nadie registrado en Supabase (o Supabase no
# está configurado): todo se manda a tu chat personal, como al principio.
CHAT_ID_RESPALDO = os.environ.get("TELEGRAM_CHAT_ID")

# Cada entrada: (nombre_del_portal, función_urls_ciudad, función_parsear)
PORTALES = [
    ("enalquiler", enalquiler.urls_ciudad, enalquiler.parsear),
    ("Trovimap", trovimap.urls_ciudad, trovimap.parsear),
    ("Pisos.com", pisos.urls_ciudad, pisos.parsear),
]


def construir_busquedas(ciudades: set) -> list:
    """(nombre_para_ti, url, parsear, ciudad) por cada combinación
    ciudad x portal."""
    busquedas = []
    for ciudad in sorted(ciudades):
        for nombre_portal, urls_fn, parsear in PORTALES:
            nombre = f"{ciudad.title()} - {nombre_portal}"
            busquedas.append((nombre, urls_fn(ciudad), parsear, ciudad))
    return busquedas


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
        if CHAT_ID_RESPALDO:
            enviar_telegram(mensaje, CHAT_ID_RESPALDO)
        return

    for filtro in filtros_activos:
        if anuncio_coincide(anuncio, nombre_busqueda, filtro):
            enviar_telegram(mensaje, filtro["chat_id"])


def descargar_y_parsear(urls: list[str], parsear):
    """Prueba cada URL candidata y devuelve los anuncios de la primera que
    responda bien y traiga resultados."""
    for url in urls:
        try:
            respuesta = requests.get(url, headers=HEADERS, timeout=15)
            respuesta.raise_for_status()
        except requests.RequestException as e:
            print(f"  ⚠️  {url} -> {e}")
            continue
        anuncios = parsear(decodificar(respuesta))
        if anuncios:
            return anuncios
        print(f"  ⚠️  {url} -> 0 anuncios, probando otra URL...")
    return []


def revisar_busqueda(nombre: str, urls: list[str], parsear, ciudad: str, filtros_activos: list[dict]) -> int:
    print(f"Revisando: {nombre}...")
    anuncios = descargar_y_parsear(urls, parsear)
    for a in anuncios:
        a["ciudad"] = ciudad
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
    ciudades = obtener_ciudades_activas(filtros_activos)

    total_nuevos = 0
    for nombre, urls, parsear, ciudad in construir_busquedas(ciudades):
        total_nuevos += revisar_busqueda(nombre, urls, parsear, ciudad, filtros_activos)
        time.sleep(DELAY_ENTRE_PETICIONES)

    print(f"Listo. {total_nuevos} anuncio(s) nuevo(s) en total, en {len(ciudades)} ciudad(es).")


if __name__ == "__main__":
    main()
