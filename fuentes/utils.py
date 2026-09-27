"""Utilidades compartidas entre los distintos parsers de portales (fuentes/)."""

import re


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
