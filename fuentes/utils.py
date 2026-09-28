"""Utilidades compartidas entre los distintos parsers de portales (fuentes/)."""

import re
import unicodedata


def localizar_linea(lineas: list[str], texto: str, desde: int = 0):
    for i in range(desde, len(lineas)):
        if lineas[i] == texto:
            return i
    return None


def buscar_en_lineas(lineas: list[str], patron: str, grupo: int = 0):
    """Busca el patrón empezando por la línea MÁS CERCANA (de abajo hacia arriba)."""
    for linea in reversed(lineas):
        m = re.search(patron, linea)
        if m:
            if m.groups():
                return next((g for g in m.groups() if g), None)
            return m.group(0)
    return None


def slug_ciudad(ciudad: str) -> str:
    """"Ciutat Vella" -> "ciutat-vella", "Sant Cugat del Vallès" -> "sant-cugat-del-valles".
    Usado para construir las URLs de búsqueda de cada portal a partir del
    nombre de ciudad que escribe la gente en /alta ciudad=..."""
    texto = unicodedata.normalize("NFD", ciudad or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto


_PRECIO_RE = re.compile(r"[1-9]\d{0,2}(?:\.\d{3})*")


def _precio_plausible(texto: str) -> bool:
    if not _PRECIO_RE.fullmatch(texto):
        return False
    return 200 <= int(texto.replace(".", "")) <= 20000


def precio_desde_linea(linea: str):
    """Extrae el precio de una línea que acaba en €. Admite el caso en que el
    contador de fotos va pegado delante ("1/251.590€" = foto 1 de 25 + 1.590€).
    Como no se puede saber dónde acaba el contador, se prueban las dos
    opciones (1 o 2 dígitos) y se queda la que da un precio de alquiler
    razonable (200-20.000 €)."""
    l = (linea or "").strip()
    if not l.endswith("€"):
        return None
    cuerpo = l[:-1].strip()

    if _precio_plausible(cuerpo):
        return cuerpo

    m = re.fullmatch(r"\d{1,2}/(\d+(?:\.\d+)*)", cuerpo)
    if m:
        resto = m.group(1)
        for k in (1, 2):
            candidato = resto[k:]
            if candidato and _precio_plausible(candidato):
                return candidato
    return None


def buscar_precio(lineas: list[str]):
    """Como buscar_en_lineas, pero para el precio: línea más cercana primero."""
    for linea in reversed(lineas):
        p = precio_desde_linea(linea)
        if p:
            return p
    return None
