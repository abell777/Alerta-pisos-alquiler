"""
Scraper de anuncios de alquiler — orquestador multi-portal.

Cada portal tiene su propio parser en fuentes/<portal>.py, con una función
parsear(html) que devuelve una lista de anuncios en formato común:
{portal, id, titulo, url, precio, m2, habitaciones, banos}

Este archivo solo se encarga de: descargar cada URL configurada, pasarla al
parser que corresponda, comparar contra lo ya visto (ahora por portal+id, así
un mismo piso no se notifica dos veces aunque aparezca en dos búsquedas del
mismo portal) y notificar los anuncios nuevos por Telegram.
"""

import time
import requests
from dotenv import load_dotenv

load_dotenv()  # antes de importar notifier, que lee variables de entorno al cargarse

from storage import cargar_vistos, guardar_vistos
from notifier import enviar_telegram
from fuentes import enalquiler, trovimap

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
DELAY_ENTRE_PETICIONES = 3  # segundos, cortesía con el servidor

# Cada entrada: (nombre_para_ti, url, función_parsear_del_portal)
BUSQUEDAS = [
    ("Valencia - piso particular", "https://www.enalquiler.com/alquilar/alquiler-piso-particular-valencia_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Exposició", "https://www.enalquiler.com/alquilar/alquiler-pisos-exposicio_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Malvarrosa/Patacona", "https://www.enalquiler.com/alquilar/alquiler-pisos-malvarrosa-patacona_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Plana", "https://www.enalquiler.com/alquilar/alquiler-pisos-plana-valencia_2_50692_48.html", enalquiler.parsear),
    ("Valencia - Trovimap", "https://www.trovimap.com/alquiler/vivienda/Valencia/Valencia", trovimap.parsear),
]


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


def revisar_busqueda(nombre: str, url: str, parsear, vistos: set) -> int:
    print(f"Revisando: {nombre}...")
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=15)
        respuesta.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Error descargando la página: {e}")
        return 0

    anuncios = parsear(respuesta.text)
    print(f"  {len(anuncios)} anuncios encontrados en la página.")

    nuevos = 0
    for anuncio in anuncios:
        clave = f"{anuncio['portal']}:{anuncio['id']}"
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

    for nombre, url, parsear in BUSQUEDAS:
        total_nuevos += revisar_busqueda(nombre, url, parsear, vistos)
        time.sleep(DELAY_ENTRE_PETICIONES)

    guardar_vistos(vistos)
    print(f"Listo. {total_nuevos} anuncio(s) nuevo(s) en total.")


if __name__ == "__main__":
    main()
