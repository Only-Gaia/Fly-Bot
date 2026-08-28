import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands

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

if not TOKEN:
    raise SystemExit(
        "Token mancante. Imposta la variabile d'ambiente DISCORD_TOKEN "
        "(su Railway) oppure crea config.json con il token (in locale)."
    )

CONFIG["token"] = TOKEN
CONFIG["prefix"] = PREFIX

# Intents: abilita quelli di cui hai bisogno (message_content è spesso necessario
# per i comandi testuali con prefisso)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


@bot.event
async def on_ready():
    log.info(f"Bot connesso come {bot.user} (ID: {bot.user.id})")


async def load_extensions():
    """Carica automaticamente tutte le cogs nella cartella cogs/, se esiste."""
    cogs_path = Path(__file__).parent / "cogs"
    if not cogs_path.exists():
        return
    for file in cogs_path.glob("*.py"):
        if file.stem == "__init__":
            continue
        extension = f"cogs.{file.stem}"
        try:
            await bot.load_extension(extension)
            log.info(f"Estensione caricata: {extension}")
        except Exception as e:
            log.error(f"Errore caricando {extension}: {e}")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
