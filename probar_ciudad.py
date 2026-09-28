"""
Prueba qué portales devuelven anuncios para una ciudad, SIN notificar nada
ni tocar Supabase. Úsalo antes de que alguien se registre en una ciudad nueva.

Uso (desde la carpeta del proyecto):
    python probar_ciudad.py Madrid
    python probar_ciudad.py Barcelona Sevilla Bilbao
"""

import sys
import requests

from fuentes import enalquiler, trovimap, pisos

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

PORTALES = [
    ("enalquiler", enalquiler.url_ciudad, enalquiler.parsear),
    ("Trovimap", trovimap.url_ciudad, trovimap.parsear),
    ("Pisos.com", pisos.url_ciudad, pisos.parsear),
]


def probar(ciudad: str) -> None:
    print(f"\n=== {ciudad} ===")
    for nombre, url_fn, parsear in PORTALES:
        url = url_fn(ciudad)
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"❌ {nombre}: HTTP {r.status_code}  ->  {url}")
                continue
            anuncios = parsear(r.text)
        except requests.RequestException as e:
            print(f"❌ {nombre}: error de red ({e})  ->  {url}")
            continue

        if not anuncios:
            print(f"⚠️  {nombre}: la página carga pero 0 anuncios (URL o parser a revisar)  ->  {url}")
            continue

        con_precio = sum(1 for a in anuncios if a.get("precio"))
        print(f"✅ {nombre}: {len(anuncios)} anuncios ({con_precio} con precio)  ->  {url}")
        print(f"     ejemplo: {anuncios[0]['titulo']}")


if __name__ == "__main__":
    ciudades = sys.argv[1:] or ["Madrid", "Barcelona"]
    for c in ciudades:
        probar(c)
