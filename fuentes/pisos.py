"""Parser para pisos.com"""

import re
from bs4 import BeautifulSoup

NOMBRE_PORTAL = "pisos"


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
            "url": url_completa,
            "precio": precio,
            "m2": m2,
            "habitaciones": habitaciones,
            "banos": banos,
        })

    return anuncios
