"""
Envía mensajes por Telegram usando tu bot.

Antes mandaba siempre al mismo TELEGRAM_CHAT_ID fijo; ahora cada aviso se
manda al chat_id de la persona a la que corresponde (según su filtro en
Supabase), así que enviar_telegram recibe el chat_id como parámetro.

Necesita una variable de entorno:
- TELEGRAM_BOT_TOKEN: el token que te da @BotFather
"""

import os
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def enviar_telegram(mensaje: str, chat_id) -> bool:
    if not BOT_TOKEN or not chat_id:
        print("⚠️  Falta TELEGRAM_BOT_TOKEN o chat_id. Mensaje NO enviado, solo mostrado aquí:")
        print(mensaje)
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje, "disable_web_page_preview": False}

    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Error enviando a Telegram (chat_id={chat_id}): {e}")
        return False
