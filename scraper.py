"""
Scraper de anuncios de alquiler (portal inicial: enalquiler.com)

Qué hace:
1. Descarga una página de resultados de búsqueda de enalquiler.com
2. Extrae cada anuncio (id, título, precio, m2, habitaciones, baños, zona, url)
3. Compara contra los anuncios ya vistos (guardados en storage.py)
4. Envía por Telegram solo los anuncios NUEVOS

IMPORTANTE (léelo antes de correrlo muchas veces seguidas):
- Este script hace peticiones HTTP normales (no un navegador headless), así que es
  ligero, pero si lo lanzas cada pocos segundos durante horas es fácil que el portal
  te bloquee la IP. Por eso hay un delay configurable entre páginas y un User-Agent
  identificable. Para producción, correrlo cada 3-5 min (vía GitHub Actions) es
  más que suficiente para "llegar antes que nadie".
- La estructura del HTML se puede romper si el portal cambia el diseño. Si un día
  deja de detectar anuncios, lo primero es revisar si cambió el HTML (ver README).
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Hay que cargar el .env ANTES de importar notifier, porque notifier lee
# las variables de entorno en el momento en que se importa el módulo.
load_dotenv()

from storage import cargar_vistos, guardar_vistos
from notifier import enviar_telegram

# --- Configuración ---
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
DELAY_ENTRE_PETICIONES = 3  # segundos, cortesía con el servidor

# URLs de búsqueda a vigilar. Añade aquí más zonas/ciudades cuando quieras escalar.
# Cada entrada: (nombre_para_ti, url_de_busqueda)
BUSQUEDAS = [
    (
        "Valencia - piso particular",
        "https://www.enalquiler.com/alquilar/alquiler-piso-particular-valencia_2_50692_48.html",
    ),
]


def extraer_anuncios(html: str) -> list[dict]:
    """Parsea el HTML de una página de resultados y devuelve una lista de anuncios."""
    soup = BeautifulSoup(html, "html.parser")
    anuncios = []

    # Solo cuentan como "anuncio real" los enlaces bajo /alquiler_piso_<ciudad>/
    # con un id largo (6-7 dígitos). Esto descarta enlaces de idioma, paginación
    # o menú, que también acaban en "_NUMERO.html" pero con números cortos.
    patron_id = re.compile(r"/alquiler_piso_[^/]+/[^/]+_(\d{5,})\.html$")

    enlaces = soup.find_all("a", href=patron_id)

    # Texto de toda la página, línea a línea, en el mismo orden en que aparece
    # en el HTML. Cada anuncio es un bloque: precio/m2/hab/baños ANTES del
    # título, y la dirección justo DESPUÉS.
    texto_completo = soup.get_text("\n")
    lineas = [l.strip() for l in texto_completo.split("\n") if l.strip()]

    ids_vistos_en_esta_pagina = set()
    puntero = 0  # evita volver a emparejar un título ya usado (hay títulos repetidos)

    for enlace in enlaces:
        href = enlace.get("href", "")
        match = patron_id.search(href)
        if not match:
            continue
        anuncio_id = match.group(1)

        if anuncio_id in ids_vistos_en_esta_pagina:
            continue  # el mismo anuncio puede aparecer más de una vez en la página
        ids_vistos_en_esta_pagina.add(anuncio_id)

        titulo = enlace.get_text(strip=True) or enlace.get("title", "")
        if not titulo:
            continue

        idx = _localizar_linea(lineas, titulo, desde=puntero)
        if idx is None:
            idx = _localizar_linea(lineas, titulo, desde=0)
        if idx is not None:
            puntero = idx + 1
            ventana_antes = lineas[max(0, idx - 12):idx]
            ventana_despues = lineas[idx + 1:idx + 4]
        else:
            ventana_antes, ventana_despues = [], []

        precio = _buscar_en_lineas(ventana_antes, r"^([\d.,]+)\s*€$")
        m2 = _buscar_en_lineas(ventana_antes, r"(\d+)\s*m[2²]")
        habitaciones = _buscar_en_lineas(ventana_antes, r"(\d+)\s*Hab")
        banos = _buscar_en_lineas(ventana_antes, r"(\d+)\s*Baño")

        url_completa = href if href.startswith("http") else "https://www.enalquiler.com" + href

        anuncios.append(
            {
                "id": anuncio_id,
                "titulo": titulo,
                "url": url_completa,
                "precio": precio,
                "m2": m2,
                "habitaciones": habitaciones,
                "banos": banos,
            }
        )

    return anuncios


def _localizar_linea(lineas: list[str], texto: str, desde: int):
    for i in range(desde, len(lineas)):
        if lineas[i] == texto:
            return i
    return None


def _buscar_en_lineas(lineas: list[str], patron: str):
    """Busca el patrón empezando por la línea MÁS CERCANA al título (de abajo hacia arriba)."""
    for linea in reversed(lineas):
        m = re.search(patron, linea)
        if m:
            grupo = next((g for g in m.groups() if g), None) if m.groups() else m.group(0)
            return grupo
    return None


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


def revisar_busqueda(nombre: str, url: str, vistos: set) -> int:
    print(f"Revisando: {nombre}...")
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=15)
        respuesta.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Error descargando la página: {e}")
        return 0

    anuncios = extraer_anuncios(respuesta.text)
    print(f"  {len(anuncios)} anuncios encontrados en la página.")

    nuevos = 0
    for anuncio in anuncios:
        clave = f"{nombre}:{anuncio['id']}"
        if clave in vistos:
            continue
        vistos.add(clave)
        nuevos += 1
        mensaje = formatear_mensaje(anuncio, nombre)
        enviar_telegram(mensaje)
        print(f"  ✅ Nuevo anuncio notificado: {anuncio['titulo']}")

    return nuevos


def main():
    vistos = cargar_vistos()
    total_nuevos = 0

    for nombre, url in BUSQUEDAS:
        total_nuevos += revisar_busqueda(nombre, url, vistos)
        time.sleep(DELAY_ENTRE_PETICIONES)

    guardar_vistos(vistos)
    print(f"Listo. {total_nuevos} anuncio(s) nuevo(s) en total.")


if __name__ == "__main__":
    main()
