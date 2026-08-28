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
