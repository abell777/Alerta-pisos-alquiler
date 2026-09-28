"""
Prueba qué portales devuelven anuncios para una ciudad, SIN notificar nada
ni tocar Supabase. Úsalo antes de que alguien se registre en una ciudad nueva.

Uso (desde la carpeta del proyecto):
    python probar_ciudad.py Madrid
    python probar_ciudad.py Barcelona Sevilla Bilbao
"""

import sys
import requests
from bs4 import BeautifulSoup

from fuentes import enalquiler, trovimap, pisos
from fuentes.utils import localizar_linea

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

PORTALES = [
    ("enalquiler", enalquiler.urls_ciudad, enalquiler.parsear),
    ("Trovimap", trovimap.urls_ciudad, trovimap.parsear),
    ("Pisos.com", pisos.urls_ciudad, pisos.parsear),
]


def volcar_contexto(html: str, titulo: str) -> None:
    """Enseña las líneas de texto justo antes del título de un anuncio, para
    ver por qué no se ha podido leer el precio."""
    soup = BeautifulSoup(html, "html.parser")
    lineas = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]
    idx = localizar_linea(lineas, titulo)
    if idx is None:
        print("     (no encuentro el título en el texto para mostrar contexto)")
        return
    print("     --- 14 líneas antes del título ---")
    for l in lineas[max(0, idx - 14):idx + 1]:
        print(f"     | {l[:110]!r}")
    print("     ----------------------------------")


def probar(ciudad: str) -> None:
    print(f"\n=== {ciudad} ===")
    for nombre, urls_fn, parsear in PORTALES:
        funciono = False
        for url in urls_fn(ciudad):
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
            except requests.RequestException as e:
                print(f"❌ {nombre}: error de red ({e})  ->  {url}")
                continue
            if r.status_code != 200:
                print(f"❌ {nombre}: HTTP {r.status_code}  ->  {url}")
                continue

            anuncios = parsear(r.text)
            if r.url.rstrip("/") != url.rstrip("/"):
                print(f"     (redirigido a: {r.url})")
            if nombre == "Trovimap" and len(anuncios) < 10:
                crudos = r.text.count("/inmueble/")
                print(f"     [diagnóstico Trovimap] enlaces '/inmueble/' en el HTML: {crudos}, "
                      f"tamaño de la página: {len(r.text)} caracteres")
                import re as _re
                sopa = BeautifulSoup(r.text, "html.parser")
                for a in sopa.find_all("a", href=_re.compile(r"/inmueble/")):
                    print(f"       enlace: ...{a['href'][-22:]} | texto: {a.get_text(strip=True)[:50]!r}")
            if not anuncios:
                print(f"⚠️  {nombre}: la página carga pero 0 anuncios  ->  {url}")
                continue

            con_precio = sum(1 for a in anuncios if a.get("precio"))
            print(f"✅ {nombre}: {len(anuncios)} anuncios ({con_precio} con precio)  ->  {url}")
            print(f"     ejemplo: {anuncios[0]['titulo']} | precio: {anuncios[0].get('precio')}")
            if con_precio == 0:
                volcar_contexto(r.text, anuncios[0]["titulo"])
            funciono = True
            break

        if not funciono:
            print(f"   >>> {nombre}: ninguna URL funcionó para {ciudad}")


def comprobar_version() -> None:
    import fuentes.utils as u
    ok = hasattr(u, "buscar_m2") and hasattr(u, "buscar_precio")
    import inspect
    print(f"Usando fuentes desde: {u.__file__}")
    if "buscar_precio" not in inspect.getsource(enalquiler):
        print("⚠️  fuentes/enalquiler.py es la versión VIEJA (no usa buscar_precio). "
              "Copia el enalquiler.py del zip nuevo en esa misma carpeta.")
    else:
        print("✔ enalquiler.py actualizado.")
    if not ok:
        print("⚠️  ESA carpeta tiene el utils.py VIEJO (sin el arreglo de precio). "
              "Copia ahí fuentes/utils.py y fuentes/enalquiler.py del zip nuevo.")
    else:
        print("✔ utils.py con el arreglo de precio.")


if __name__ == "__main__":
    comprobar_version()
    ciudades = sys.argv[1:] or ["Madrid", "Barcelona"]
    for c in ciudades:
        probar(c)
