"""Parser para enalquiler.com"""

import re
from bs4 import BeautifulSoup
from .utils import localizar_linea, buscar_en_lineas, buscar_precio, slug_ciudad

NOMBRE_PORTAL = "enalquiler"

PATRON_ID = re.compile(r"/alquiler_piso_[^/]+/[^/]+_(\d{5,})\.html$")


def url_ciudad(ciudad: str) -> str:
    """Página genérica de "toda la provincia" de enalquiler.com. Confirmada
    (probado con Valencia y Barcelona): funciona igual para cualquier
    ciudad/provincia de España, solo cambia el slug. Es más amplia que las
    URLs de zona concreta que usábamos antes para Valencia (esas cubrían 4
    barrios; esta cubre toda la provincia en una sola petición)."""
    return f"https://www.enalquiler.com/pisos-alquiler-{slug_ciudad(ciudad)}.html"


def urls_ciudad(ciudad: str) -> list[str]:
    return [url_ciudad(ciudad)]


def parsear(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    enlaces = soup.find_all("a", href=PATRON_ID)

    texto_completo = soup.get_text("\n")
    lineas = [l.strip() for l in texto_completo.split("\n") if l.strip()]

    anuncios = []
    ids_vistos = set()
    puntero = 0

    for enlace in enlaces:
        href = enlace.get("href", "")
        match = PATRON_ID.search(href)
        if not match:
            continue
        anuncio_id = match.group(1)
        if anuncio_id in ids_vistos:
            continue
        ids_vistos.add(anuncio_id)

        titulo = enlace.get_text(strip=True) or enlace.get("title", "")
        if not titulo:
            continue

        idx = localizar_linea(lineas, titulo, desde=puntero)
        if idx is None:
            idx = localizar_linea(lineas, titulo, desde=0)
        if idx is not None:
            puntero = idx + 1
            ventana_antes = lineas[max(0, idx - 12):idx]
        else:
            ventana_antes = []

        precio = buscar_precio(ventana_antes)
        m2 = buscar_en_lineas(ventana_antes, r"(\d+)\s*m[2²]")
        habitaciones = buscar_en_lineas(ventana_antes, r"(\d+)\s*Hab")
        banos = buscar_en_lineas(ventana_antes, r"(\d+)\s*Baño")

        url_completa = href if href.startswith("http") else "https://www.enalquiler.com" + href

        anuncios.append({
            "portal": NOMBRE_PORTAL,
            "id": anuncio_id,
            "titulo": titulo,
            "url": url_completa,
            "precio": precio,
            "m2": m2,
            "habitaciones": habitaciones,
            "banos": banos,
        })

    return anuncios
