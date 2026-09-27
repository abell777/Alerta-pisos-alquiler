"""
EJECUTA ESTO UNA SOLA VEZ, en tu ordenador, justo después de crear las
tablas en Supabase (supabase_esquema.sql) y de haber puesto SUPABASE_URL y
SUPABASE_SERVICE_KEY en tu .env local.

Copia lo que ya tenías en vistos.json a la tabla "vistos" de Supabase, para
que no se te vuelvan a notificar como "nuevos" los ~150 anuncios que ya
conocías.

Uso:
    python migrar_vistos.py
"""

import json
import os
from dotenv import load_dotenv
import requests

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates",
}

with open("vistos.json", encoding="utf-8") as f:
    claves = json.load(f)

print(f"Migrando {len(claves)} claves a Supabase...")

LOTE = 500
for i in range(0, len(claves), LOTE):
    lote = [{"clave": c} for c in claves[i:i + LOTE]]
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/vistos",
        headers=HEADERS,
        params={"on_conflict": "clave"},
        json=lote,
        timeout=30,
    )
    r.raise_for_status()
    print(f"  {min(i + LOTE, len(claves))}/{len(claves)}")

print("Listo. vistos.json ya no se usa (puedes borrarlo o dejarlo, da igual).")
