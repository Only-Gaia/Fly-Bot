import discord
from discord.ext import commands

HELP_STRUTTURA = {
    "🛡️ Moderazione": [
        "pex", "depex", "timeout", "untimeout", "ban", "unban", "kick", "changename",
        "warn", "unwarn", "clearwarn", "warncount", "purge", "lock", "unlock",
        "livello", "xpadd", "xpremove", "messagecount", "addmessages",
        "resetmessages", "leavemessages",
    ],
    "🤖 Automod": ["automod on/off", "automod link on/off", "automod spam on/off", "automod log #canale/off"],
    "💰 Economia": [
        "balance", "daily", "work", "mine", "tris", "pay", "add", "remove",
        "coinflip", "blackjack", "roulette", "leaderboard", "shop", "buy",
        "inventory", "openbox", "luckybox", "lucky",
    ],
    "🎉 Gioco": ["8ball", "say", "ship", "rendigay", "rendilesbica", "kiss", "clap", "slap", "hug", "kill", "nitrodonate"],
    "🎫 Supporto": ["pannelloticket"],
    "🎁 Giveaway": ["giveaway create", "giveaway end", "giveaway reroll", "giveaway list"],
    "👋 Benvenuto/Inviti": [
        "setwelcome", "setgoodbye", "showinvites", "setinviteschannel",
        "resetinvites", "addinvites", "removeinvites", "invitebot",
    ],
    "ℹ️ Info": ["userinfo", "serverinfo", "help"],
}


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="userinfo", aliases=["whois"])
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"Informazioni su {member}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nickname", value=member.nick or "Nessuno", inline=True)
        embed.add_field(name="Bot", value="Sì" if member.bot else "No", inline=True)
        embed.add_field(name="Account creato", value=discord.utils.format_dt(member.created_at, "F"), inline=False)
        embed.add_field(name="Entrato nel server", value=discord.utils.format_dt(member.joined_at, "F"), inline=False)
        ruoli = [r.mention for r in member.roles if r.name != "@everyone"]
        embed.add_field(name=f"Ruoli ({len(ruoli)})", value=" ".join(ruoli) if ruoli else "Nessuno", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title=f"Informazioni su {guild.name}", color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Proprietario", value=guild.owner.mention if guild.owner else "Sconosciuto", inline=True)
        embed.add_field(name="Membri", value=guild.member_count, inline=True)
        embed.add_field(name="Canali testuali", value=len(guild.text_channels), inline=True)
        embed.add_field(name="Canali vocali", value=len(guild.voice_channels), inline=True)
        embed.add_field(name="Ruoli", value=len(guild.roles), inline=True)
        embed.add_field(name="Creato il", value=discord.utils.format_dt(guild.created_at, "F"), inline=False)
        embed.add_field(name="Boost", value=f"Livello {guild.premium_tier} ({guild.premium_subscription_count} boost)", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="help")
    async def help_command(self, ctx, *, comando: str = None):
        prefix = self.bot.config.get("prefix", "?")
        if comando:
            cmd = self.bot.get_command(comando)
            if not cmd:
                return await ctx.send(f"⚠️ Comando `{comando}` non trovato.")
            return await ctx.send(f"**{prefix}{cmd.name}** — {cmd.help or 'Nessuna descrizione disponibile.'}")

        embed = discord.Embed(
            title="📖 Lista comandi",
            description=f"Prefisso attuale: `{prefix}`",
            color=discord.Color.blurple(),
        )
        for categoria, comandi in HELP_STRUTTURA.items():
            valore = ", ".join(f"`{prefix}{c}`" for c in comandi)
            embed.add_field(name=categoria, value=valore, inline=False)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
