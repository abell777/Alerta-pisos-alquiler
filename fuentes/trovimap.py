"""Parser para trovimap.com (agregador de anuncios de varias agencias)."""

import re
from bs4 import BeautifulSoup
from .utils import localizar_linea, buscar_en_lineas

NOMBRE_PORTAL = "trovimap"

# Las fichas de anuncio enlazan a /inmueble/<id1>-<id2>. La misma URL aparece
# dos veces por anuncio (el título y el botón "Ver más"), por eso deduplicamos.
PATRON_ID = re.compile(r"/inmueble/(\d+-\d+)$")


def url_ciudad(ciudad: str) -> str:
    """OJO: solo confirmado para Valencia (/alquiler/vivienda/Valencia/Valencia).
    Trovimap organiza la URL como /alquiler/vivienda/<Región>/<Ciudad>; para
    una capital de provincia suele coincidir región=ciudad, pero no está
    verificado para otras ciudades. La primera vez que añadas una ciudad
    nueva, comprueba en el navegador que esta URL carga anuncios de verdad
    (y no una página vacía o de error) antes de darla por buena."""
    c = (ciudad or "").strip().title()
    return f"https://www.trovimap.com/alquiler/vivienda/{c}/{c}"


# URLs que hay que fijar a mano cuando el patrón automático no da la ciudad
# completa. Abre trovimap.com, busca alquiler en esa ciudad y pega aquí la URL
# de la barra del navegador. Ejemplo:
#   "barcelona": "https://www.trovimap.com/alquiler/vivienda/....",
URLS_MANUALES = {
}


def urls_ciudad(ciudad: str) -> list[str]:
    from .utils import slug_ciudad
    manual = URLS_MANUALES.get(slug_ciudad(ciudad))
    return [manual] if manual else [url_ciudad(ciudad)]


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

        titulo = enlace.get_text(strip=True)
        # el enlace "Ver más" apunta a la misma URL pero sin título útil: lo saltamos
        if not titulo or titulo.lower() in ("ver más", "contactar"):
            continue

        ids_vistos.add(anuncio_id)

        idx = localizar_linea(lineas, titulo, desde=puntero)
        if idx is None:
            idx = localizar_linea(lineas, titulo, desde=0)
        if idx is not None:
            puntero = idx + 1
            ventana_antes = lineas[max(0, idx - 8):idx]
        else:
            ventana_antes = []

        precio = buscar_en_lineas(ventana_antes, r"^([\d.,]+)\s*€$")
        # línea típica: "113 m² 3 2"  →  m2, habitaciones, baños
        m2 = habitaciones = banos = None
        for linea in reversed(ventana_antes):
            m = re.search(r"(\d+)\s*m[²2]\s+(\d+)\s+(\d+)", linea)
            if m:
                m2, habitaciones, banos = m.group(1), m.group(2), m.group(3)
                break
            m_solo_m2 = re.search(r"^(\d+)\s*m[²2]", linea)
            if m_solo_m2 and m2 is None:
                m2 = m_solo_m2.group(1)

        url_completa = href if href.startswith("http") else "https://www.trovimap.com" + href

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
