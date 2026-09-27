"""
Guarda qué anuncios ya hemos visto, para no notificar dos veces el mismo.

Versión actual: un archivo JSON local (vistos.json). Sencillo, funciona perfecto
para probar el proyecto y para las primeras semanas.

Cuando pasemos a producción de verdad (con usuarios y filtros por persona),
sustituiremos este archivo por tablas en Supabase, pero la función de
scraper.py que lo usa (cargar_vistos/guardar_vistos) no tendrá que cambiar
mucho: solo lo que hay dentro de estas dos funciones.
"""

import json
import os

ARCHIVO_VISTOS = os.path.join(os.path.dirname(__file__), "vistos.json")


def cargar_vistos() -> set:
    if not os.path.exists(ARCHIVO_VISTOS):
        return set()
    with open(ARCHIVO_VISTOS, "r", encoding="utf-8") as f:
        try:
            return set(json.load(f))
        except json.JSONDecodeError:
            return set()


def guardar_vistos(vistos: set) -> None:
    with open(ARCHIVO_VISTOS, "w", encoding="utf-8") as f:
        json.dump(sorted(vistos), f, ensure_ascii=False, indent=2)
