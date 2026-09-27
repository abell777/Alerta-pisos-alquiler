"""
Envía mensajes por Telegram usando el bot que vas a crear (ver README, paso 2).

Necesita dos variables de entorno:
- TELEGRAM_BOT_TOKEN: el token que te da @BotFather
- TELEGRAM_CHAT_ID: el id de chat al que se manda el aviso (puede ser tu chat
  personal con el bot, o el id de un grupo/canal si más adelante quieres
  mandarlo a varias personas)
"""

import os
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def enviar_telegram(mensaje: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  Falta configurar TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID. "
              "Mensaje NO enviado, solo mostrado aquí:")
        print(mensaje)
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "disable_web_page_preview": False}

    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Error enviando a Telegram: {e}")
        return False
