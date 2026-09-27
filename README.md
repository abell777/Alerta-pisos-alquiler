# Alertas de pisos — v0.1 (un solo portal, prueba de concepto)

Este es el **primer paso** del proyecto: un scraper que vigila anuncios de
alquiler en enalquiler.com (Valencia) y te avisa por Telegram en cuanto sale
uno nuevo. Sin filtros por usuario, sin base de datos externa todavía — eso
viene en la fase 2. Ahora mismo el objetivo único es: **¿detecta de verdad
anuncios nuevos y me avisa?**

## Paso 1 — Crear el bot de Telegram (5 min, gratis)

1. Abre Telegram y busca **@BotFather**.
2. Envíale `/newbot`, ponle un nombre (ej. "Alertas Pisos VLC").
3. Te dará un **token** (algo como `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxx`).
   Guárdalo, es tu `TELEGRAM_BOT_TOKEN`.
4. Ahora busca tu bot por su usuario (el que le pusiste) y pulsa "Iniciar"
   /escríbele cualquier cosa, para "activar" la conversación.
5. Para saber tu `TELEGRAM_CHAT_ID`, abre en el navegador (sustituyendo TU_TOKEN):
   `https://api.telegram.org/botTU_TOKEN/getUpdates`
   y busca el número en `"chat":{"id": ...}`.

## Paso 2 — Probarlo en tu ordenador (antes de subirlo a ningún sitio)

```bash
cd alertas-pisos
python -m venv .venv
source .venv/bin/activate    # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# abre .env y pon tu TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID reales

python scraper.py
```

La primera vez que lo corras, notificará TODOS los anuncios que encuentre
(porque `vistos.json` está vacío) — es normal, es la "carga inicial". A
partir de la segunda ejecución solo te avisará de los que sean nuevos de
verdad.

Si algo falla en el parseo (por ejemplo, 0 anuncios encontrados cuando debería
haber varios), lo más probable es que enalquiler.com haya cambiado el HTML de
su página desde que escribí este scraper — tráeme el error o pégame el HTML
de la página y lo ajustamos juntos.

## Paso 3 — Subirlo a GitHub

1. Crea un repositorio nuevo en GitHub (puede ser privado).
2. Desde la carpeta del proyecto:

```bash
git init
git add .
git commit -m "Primera versión: scraper enalquiler.com + Telegram"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/alertas-pisos.git
git push -u origin main
```

(El `.env` con tus claves reales **no se sube** — está en `.gitignore` a
propósito, por seguridad.)

## Paso 4 — Configurar los secretos en GitHub (para que corra solo, gratis)

1. En tu repo de GitHub: **Settings → Secrets and variables → Actions → New
   repository secret**.
2. Crea dos secretos:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Ya está. El archivo `.github/workflows/scrape.yml` hará que GitHub ejecute
   el scraper automáticamente cada 5 minutos, gratis (dentro del límite de
   minutos gratuitos de GitHub Actions, que es de sobra para esto).
4. Puedes forzar una ejecución manual desde la pestaña **Actions** de tu
   repo → selecciona el workflow "Vigilar pisos" → **Run workflow**.

## Qué es "cambios necesarios" a partir de ahora

Como quedamos: a partir de aquí, cuando toquemos algo, te doy solo el
`.zip` con los archivos que cambian, no el proyecto entero otra vez —
salvo que sea la primera entrega, como esta.

## Siguiente paso sugerido (fase 2)

Una vez confirmes que esto detecta y avisa bien durante un par de días:
1. Añadir un segundo portal (Pisos.com o Habitaclia).
2. Meter filtros (zona, precio) en vez de recibir todos los anuncios.
3. Pasar de "un solo Telegram fijo" a que cualquiera pueda registrarse y
   poner sus propios filtros (aquí entra Supabase).

Dime cuándo lo has probado y seguimos.
