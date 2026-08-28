import discord
from discord.ext import commands

from utils.storage import Storage

invites_db = Storage("invites.json")       # gid -> uid -> quantita_inviti_effettivi
config_db = Storage("invites_config.json")  # gid -> {"log_channel": id}


class Invites(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache = {}  # gid -> {invite_code: uses}

    async def cache_guild_invites(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
            self.cache[guild.id] = {inv.code: inv.uses for inv in invites}
        except discord.Forbidden:
            self.cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.cache_guild_invites(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        self.cache.setdefault(invite.guild.id, {})[invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        old_invites = self.cache.get(guild.id, {})
        try:
            new_invites = await guild.invites()
        except discord.Forbidden:
            return

        used_invite = None
        for inv in new_invites:
            if old_invites.get(inv.code, 0) < inv.uses:
                used_invite = inv
                break

        await self.cache_guild_invites(guild)

        if used_invite and used_invite.inviter:
            inviter_id = used_invite.inviter.id
            current = invites_db.get(guild.id, inviter_id, default=0)
            invites_db.set(guild.id, inviter_id, current + 1)

            config = config_db.get(guild.id, default=None)
            if config and config.get("log_channel"):
                channel = guild.get_channel(config["log_channel"])
                if channel:
                    await channel.send(
                        f"📨 {member.mention} è entrato invitato da <@{inviter_id}> "
                        f"(ora ha {current + 1} inviti)."
                    )

    @commands.command(name="showinvites", aliases=["invites"])
    async def showinvites(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        count = invites_db.get(ctx.guild.id, member.id, default=0)
        await ctx.send(f"📨 {member.mention} ha **{count}** inviti.")

    @commands.command(name="setinviteschannel")
    @commands.has_permissions(manage_guild=True)
    async def setinviteschannel(self, ctx, canale: discord.TextChannel):
        config = config_db.get(ctx.guild.id, default={})
        config["log_channel"] = canale.id
        config_db.set(ctx.guild.id, config)
        await ctx.send(f"✅ Canale log inviti impostato su {canale.mention}.")

    @commands.command(name="resetinvites")
    @commands.has_permissions(manage_guild=True)
    async def resetinvites(self, ctx, member: discord.Member):
        invites_db.set(ctx.guild.id, member.id, 0)
        await ctx.send(f"🧹 Inviti di {member.mention} azzerati.")

    @commands.command(name="addinvites")
    @commands.has_permissions(manage_guild=True)
    async def addinvites(self, ctx, member: discord.Member, quantita: int):
        current = invites_db.get(ctx.guild.id, member.id, default=0)
        invites_db.set(ctx.guild.id, member.id, current + quantita)
        await ctx.send(f"✅ Aggiunti {quantita} inviti a {member.mention}. Totale: {current + quantita}")

    @commands.command(name="removeinvites")
    @commands.has_permissions(manage_guild=True)
    async def removeinvites(self, ctx, member: discord.Member, quantita: int):
        current = invites_db.get(ctx.guild.id, member.id, default=0)
        nuovo = max(0, current - quantita)
        invites_db.set(ctx.guild.id, member.id, nuovo)
        await ctx.send(f"✅ Rimossi {quantita} inviti a {member.mention}. Totale: {nuovo}")

    @commands.command(name="invitebot")
    async def invitebot(self, ctx):
        app_info = await self.bot.application_info()
        link = discord.utils.oauth_url(app_info.id, permissions=discord.Permissions(administrator=True))
        await ctx.send(f"🔗 Invita il bot con questo link:\n{link}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Invites(bot))
