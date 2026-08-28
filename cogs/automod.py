import re
import time
import datetime
from collections import defaultdict, deque

import discord
from discord.ext import commands

from utils.storage import Storage

config_db = Storage("automod.json")

LINK_REGEX = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
SPAM_WINDOW = 6          # secondi
SPAM_MAX_MESSAGES = 5    # messaggi nella finestra per essere considerato spam


def default_config():
    return {
        "enabled": False,
        "link_filter": False,
        "spam_filter": False,
        "log_channel": None,
    }


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recent_messages = defaultdict(lambda: defaultdict(deque))  # guild -> user -> timestamps

    def get_config(self, guild_id: int) -> dict:
        cfg = config_db.get(guild_id, default=None)
        if cfg is None:
            cfg = default_config()
            config_db.set(guild_id, cfg)
        return cfg

    def set_config(self, guild_id: int, cfg: dict):
        config_db.set(guild_id, cfg)

    async def log_action(self, guild: discord.Guild, description: str):
        cfg = self.get_config(guild.id)
        channel_id = cfg.get("log_channel")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(description=description, color=discord.Color.red(),
                                   timestamp=discord.utils.utcnow())
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        cfg = self.get_config(message.guild.id)
        if not cfg["enabled"]:
            return
        if isinstance(message.author, discord.Member) and message.author.guild_permissions.manage_messages:
            return  # non filtriamo i moderatori

        # --- Filtro link ---
        if cfg["link_filter"] and LINK_REGEX.search(message.content):
            try:
                await message.delete()
                await message.channel.send(
                    f"🔗 {message.author.mention}, i link non sono permessi qui.", delete_after=5
                )
            except discord.Forbidden:
                pass
            await self.log_action(
                message.guild,
                f"🔗 Link rimosso di {message.author.mention} in {message.channel.mention}:\n```{message.content[:500]}```"
            )
            return

        # --- Filtro spam ---
        if cfg["spam_filter"]:
            now = time.time()
            dq = self.recent_messages[message.guild.id][message.author.id]
            dq.append(now)
            while dq and now - dq[0] > SPAM_WINDOW:
                dq.popleft()
            if len(dq) >= SPAM_MAX_MESSAGES:
                try:
                    await message.channel.send(
                        f"🚫 {message.author.mention} stai mandando troppi messaggi, rallenta.",
                        delete_after=5,
                    )
                    await message.author.timeout(
                        discord.utils.utcnow() + datetime.timedelta(minutes=1),
                        reason="Automod: spam rilevato",
                    )
                except Exception:
                    pass
                await self.log_action(
                    message.guild,
                    f"🚫 Spam rilevato da {message.author.mention} in {message.channel.mention}"
                )
                dq.clear()

    # ---------------------------- COMANDI ----------------------------
    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def automod(self, ctx, stato: str = None):
        """?automod on / ?automod off"""
        cfg = self.get_config(ctx.guild.id)
        if stato is None:
            log_display = f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "non impostato"
            return await ctx.send(
                f"🛡️ Automod: **{'attivo' if cfg['enabled'] else 'disattivo'}**\n"
                f"🔗 Filtro link: **{'attivo' if cfg['link_filter'] else 'disattivo'}**\n"
                f"🚫 Filtro spam: **{'attivo' if cfg['spam_filter'] else 'disattivo'}**\n"
                f"📝 Canale log: {log_display}"
            )
        stato = stato.lower()
        if stato not in ("on", "off"):
            return await ctx.send("⚠️ Usa `on` oppure `off`.")
        cfg["enabled"] = stato == "on"
        self.set_config(ctx.guild.id, cfg)
        await ctx.send(f"🛡️ Automod {'attivato ✅' if cfg['enabled'] else 'disattivato ❌'}.")

    @automod.command(name="link")
    @commands.has_permissions(manage_guild=True)
    async def automod_link(self, ctx, stato: str):
        cfg = self.get_config(ctx.guild.id)
        stato = stato.lower()
        if stato not in ("on", "off"):
            return await ctx.send("⚠️ Usa `on` oppure `off`.")
        cfg["link_filter"] = stato == "on"
        self.set_config(ctx.guild.id, cfg)
        await ctx.send(f"🔗 Filtro link {'attivato ✅' if cfg['link_filter'] else 'disattivato ❌'}.")

    @automod.command(name="spam")
    @commands.has_permissions(manage_guild=True)
    async def automod_spam(self, ctx, stato: str):
        cfg = self.get_config(ctx.guild.id)
        stato = stato.lower()
        if stato not in ("on", "off"):
            return await ctx.send("⚠️ Usa `on` oppure `off`.")
        cfg["spam_filter"] = stato == "on"
        self.set_config(ctx.guild.id, cfg)
        await ctx.send(f"🚫 Filtro spam {'attivato ✅' if cfg['spam_filter'] else 'disattivato ❌'}.")

    @automod.command(name="log")
    @commands.has_permissions(manage_guild=True)
    async def automod_log(self, ctx, canale: discord.TextChannel = None):
        """?automod log #canale  oppure  ?automod log off"""
        cfg = self.get_config(ctx.guild.id)
        if canale is None:
            return await ctx.send("⚠️ Specifica un canale, oppure usa `?automod log off`.")
        cfg["log_channel"] = canale.id
        self.set_config(ctx.guild.id, cfg)
        await ctx.send(f"📝 Canale log impostato su {canale.mention}.")

    @automod_log.error
    async def automod_log_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            # Gestisce "?automod log off"
            arg = ctx.message.content.split()[-1].lower()
            if arg == "off":
                cfg = self.get_config(ctx.guild.id)
                cfg["log_channel"] = None
                self.set_config(ctx.guild.id, cfg)
                return await ctx.send("📝 Log automod disattivato.")
        raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
