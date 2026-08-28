import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

CONFIG_PATH = Path(__file__).parent / "config.json"

# Priorità: variabili d'ambiente (usate su Railway/hosting) > config.json (uso locale)
CONFIG = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)

TOKEN = os.environ.get("DISCORD_TOKEN") or CONFIG.get("token")
PREFIX = os.environ.get("PREFIX") or CONFIG.get("prefix", "?")
MONGO_URI = os.environ.get("MONGO_URI") or CONFIG.get("mongo_uri")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME") or CONFIG.get("mongo_db_name", "flybot")

if not TOKEN:
    raise SystemExit(
        "Token mancante. Imposta la variabile d'ambiente DISCORD_TOKEN "
        "(su Railway) oppure crea config.json con il token (in locale)."
    )

if not MONGO_URI:
    raise SystemExit(
        "MongoDB URI mancante. Imposta la variabile d'ambiente MONGO_URI "
        "(su Railway) oppure crea config.json con 'mongo_uri' (in locale)."
    )

CONFIG["token"] = TOKEN
CONFIG["prefix"] = PREFIX
CONFIG["mongo_uri"] = MONGO_URI
CONFIG["mongo_db_name"] = MONGO_DB_NAME

# --- Setup MongoDB ---
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]

# --- Setup Discord bot ---
intents = discord.Intents.default()
intents.message_content = True  # necessario se usi comandi con prefisso

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.db = db  # rende il db accessibile da ogni cog/comando tramite bot.db


@bot.event
async def on_ready():
    log.info(f"Bot connesso come {bot.user} (ID: {bot.user.id})")
    try:
        # ping al database per verificare la connessione all'avvio
        await mongo_client.admin.command("ping")
        log.info("Connessione a MongoDB riuscita.")
    except Exception as e:
        log.error(f"Errore di connessione a MongoDB: {e}")


@bot.command(name="ping")
async def ping(ctx):
    """Comando di test: verifica che il bot risponda."""
    await ctx.send(f"Pong! Latenza: {round(bot.latency * 1000)}ms")


async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
