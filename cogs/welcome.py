import discord
from discord.ext import commands

from utils.storage import Storage

welcome_db = Storage("welcome.json")  # gid -> {"channel": id, "message": str}
goodbye_db = Storage("goodbye.json")  # gid -> {"channel": id, "message": str}

PLACEHOLDER_HELP = "Placeholder disponibili: {utente}, {menzione}, {server}, {membri}"


def format_message(template: str, member: discord.Member) -> str:
    return (
        template.replace("{utente}", member.name)
        .replace("{menzione}", member.mention)
        .replace("{server}", member.guild.name)
        .replace("{membri}", str(member.guild.member_count))
    )


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="setwelcome")
    @commands.has_permissions(manage_guild=True)
    async def setwelcome(self, ctx, canale: discord.TextChannel, *, messaggio: str):
        f"""?setwelcome #canale Benvenuto {{menzione}} su {{server}}! {PLACEHOLDER_HELP}"""
        welcome_db.set(ctx.guild.id, {"channel": canale.id, "message": messaggio})
        await ctx.send(f"✅ Messaggio di benvenuto impostato su {canale.mention}.\n{PLACEHOLDER_HELP}")

    @commands.command(name="setgoodbye")
    @commands.has_permissions(manage_guild=True)
    async def setgoodbye(self, ctx, canale: discord.TextChannel, *, messaggio: str):
        goodbye_db.set(ctx.guild.id, {"channel": canale.id, "message": messaggio})
        await ctx.send(f"✅ Messaggio di addio impostato su {canale.mention}.\n{PLACEHOLDER_HELP}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = welcome_db.get(member.guild.id, default=None)
        if not config:
            return
        channel = member.guild.get_channel(config["channel"])
        if channel:
            await channel.send(format_message(config["message"], member))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = goodbye_db.get(member.guild.id, default=None)
        if not config:
            return
        channel = member.guild.get_channel(config["channel"])
        if channel:
            await channel.send(format_message(config["message"], member))


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
