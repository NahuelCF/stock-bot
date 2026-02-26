import requests
import re
import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "TU_TOKEN"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# 👇 Productos monitoreados dinámicamente
products = {}


def extract_product_id(html):
    match = re.search(r'"productId":"(\d+)"', html)
    if match:
        return match.group(1)
    return None


def check_stock(url, product_id, sizes):
    r = requests.get(url, headers=HEADERS)
    html = r.text

    match = re.search(
        rf'"jsonConfig":({{.*?"productId":"{product_id}".*?}})',
        html
    )

    if not match:
        return False

    data = json.loads(match.group(1))
    options = data["attributes"]["272"]["options"]

    for option in options:
        if option["label"] in sizes and option["products"]:
            return True

    return False


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = context.args[0]
        sizes = context.args[1:]

        r = requests.get(url, headers=HEADERS)
        product_id = extract_product_id(r.text)

        if not product_id:
            await update.message.reply_text("No pude detectar el producto.")
            return

        products[url] = {
            "product_id": product_id,
            "sizes": sizes,
            "notified": False
        }

        await update.message.reply_text(f"Agregado ✅\n{url}\nTalles: {', '.join(sizes)}")

    except:
        await update.message.reply_text("Uso correcto:\n/add URL talle talle")


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not products:
        await update.message.reply_text("No hay productos monitoreados.")
        return

    msg = "📦 Productos monitoreados:\n\n"
    for url, data in products.items():
        msg += f"{url}\nTalles: {', '.join(data['sizes'])}\n\n"

    await update.message.reply_text(msg)


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.args[0]
    if url in products:
        del products[url]
        await update.message.reply_text("Eliminado ✅")
    else:
        await update.message.reply_text("No encontrado.")


async def monitor(app):
    while True:
        for url, data in products.items():
            available = check_stock(url, data["product_id"], data["sizes"])

            if available and not data["notified"]:
                await app.bot.send_message(
                    chat_id=list(app.bot_data["chat_ids"])[0],
                    text=f"🔥 STOCK DISPONIBLE\n{url}\nTalles: {', '.join(data['sizes'])}"
                )
                data["notified"] = True

            if not available:
                data["notified"] = False

        await asyncio.sleep(600)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.application.bot_data.setdefault("chat_ids", set()).add(update.effective_chat.id)
    await update.message.reply_text("Bot activo 👟")


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_products))
    app.add_handler(CommandHandler("remove", remove))

    asyncio.create_task(monitor(app))

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())