"""Parser para pisos.com"""

import re
from bs4 import BeautifulSoup

NOMBRE_PORTAL = "pisos"


def url_ciudad(ciudad: str) -> str:
    """OJO: solo confirmado para Valencia
    (/alquiler/pisos-valencia_capital_zona_urbana/). El patrón
    "<ciudad>_capital_zona_urbana" es el que usa pisos.com para capitales de
    provincia; probablemente generaliza a Madrid, Barcelona, Sevilla, etc.,
    pero no está verificado. Compruébalo en el navegador la primera vez que
    añadas una ciudad nueva, igual que hicimos con Valencia.
    """
    from .utils import slug_ciudad
    return f"https://www.pisos.com/alquiler/pisos-{slug_ciudad(ciudad)}_capital_zona_urbana/"


def urls_ciudad(ciudad: str) -> list[str]:
    """Varias URLs candidatas, de más a menos precisa. El scraper usa la
    primera que responda bien y traiga anuncios. Confirmado: Valencia y
    Madrid funcionan con "_capital_zona_urbana"; Barcelona da 404 con ese
    patrón, así que se prueban variantes."""
    from .utils import slug_ciudad
    s = slug_ciudad(ciudad)
    base = "https://www.pisos.com/alquiler/pisos-"
    return [
        f"{base}{s}_capital_zona_urbana/",
        f"{base}{s}_capital/",
        f"{base}{s}/",
    ]


def parsear(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tarjetas = soup.find_all("div", class_="ad-preview")

    anuncios = []
    for tarjeta in tarjetas:
        anuncio_id = tarjeta.get("id")
        if not anuncio_id:
            continue

        enlace_titulo = tarjeta.find("a", class_="ad-preview__title")
        if not enlace_titulo:
            continue
        titulo = enlace_titulo.get_text(strip=True)
        href = enlace_titulo.get("href", "")
        if not titulo or not href:
            continue

        subtitulo_tag = tarjeta.find("p", class_="ad-preview__subtitle")
        subtitulo = subtitulo_tag.get_text(strip=True) if subtitulo_tag else ""

        precio_tag = tarjeta.find("span", class_="ad-preview__price")
        precio = None
        if precio_tag:
            m = re.search(r"([\d.,]+)\s*€", precio_tag.get_text(strip=True))
            if m:
                precio = m.group(1)

        m2 = habitaciones = banos = None
        for caract in tarjeta.find_all("p", class_="ad-preview__char"):
            texto = caract.get_text(strip=True)
            m = re.search(r"(\d+)\s*hab", texto, re.IGNORECASE)
            if m:
                habitaciones = m.group(1)
                continue
            m = re.search(r"(\d+)\s*ba[nñ]o", texto, re.IGNORECASE)
            if m:
                banos = m.group(1)
                continue
            m = re.search(r"(\d+)\s*m[²2]", texto)
            if m:
                m2 = m.group(1)

        url_completa = href if href.startswith("http") else "https://www.pisos.com" + href

        anuncios.append({
            "portal": NOMBRE_PORTAL,
            "id": anuncio_id,
            "titulo": titulo,
            "subtitulo": subtitulo,
            "url": url_completa,
            "precio": precio,
            "m2": m2,
            "habitaciones": habitaciones,
            "banos": banos,
        })

    return anuncios
