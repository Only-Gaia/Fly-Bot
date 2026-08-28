import datetime

import discord
from discord.ext import commands

from utils.storage import Storage
from utils.timeconv import parse_duration, human_duration

warns_db = Storage("warns.json")
xp_db = Storage("xp.json")
msg_db = Storage("messages.json")


def xp_for_level(level: int) -> int:
    """XP totale richiesta per raggiungere un dato livello."""
    return 5 * (level ** 2) + 50 * level + 100


def level_from_xp(xp: int) -> int:
    level = 0
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------- CONTATORE MESSAGGI / XP AUTOMATICO ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        gid, uid = message.guild.id, message.author.id
        count = msg_db.get(gid, uid, default=0) + 1
        msg_db.set(gid, uid, count)

        xp = xp_db.get(gid, uid, default=0)
        old_level = level_from_xp(xp)
        xp += 5
        new_level = level_from_xp(xp)
        xp_db.set(gid, uid, xp)
        if new_level > old_level:
            try:
                await message.channel.send(
                    f"🎉 {message.author.mention} è salito al livello **{new_level}**!"
                )
            except discord.Forbidden:
                pass

    # ---------------------------- PEX / DEPEX ----------------------------
    @commands.command(name="pex")
    @commands.has_permissions(manage_roles=True)
    async def pex(self, ctx, member: discord.Member, role: discord.Role):
        """Assegna un ruolo a un utente."""
        if role in member.roles:
            return await ctx.send(f"⚠️ {member.mention} ha già il ruolo {role.mention}.")
        await member.add_roles(role, reason=f"Pex da {ctx.author}")
        await ctx.send(f"✅ Ruolo {role.mention} assegnato a {member.mention}.")

    @commands.command(name="depex")
    @commands.has_permissions(manage_roles=True)
    async def depex(self, ctx, member: discord.Member, role: discord.Role):
        """Rimuove un ruolo a un utente."""
        if role not in member.roles:
            return await ctx.send(f"⚠️ {member.mention} non ha il ruolo {role.mention}.")
        await member.remove_roles(role, reason=f"Depex da {ctx.author}")
        await ctx.send(f"✅ Ruolo {role.mention} rimosso a {member.mention}.")

    # ---------------------------- TIMEOUT ----------------------------
    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, durata: str, *, motivo: str = "Nessun motivo"):
        """Mette in timeout un utente. Es: ?timeout @user 10m spam"""
        try:
            seconds = parse_duration(durata)
        except ValueError as e:
            return await ctx.send(f"⚠️ {e}")
        if seconds > 28 * 86400:
            return await ctx.send("⚠️ Il timeout massimo su Discord è 28 giorni.")
        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        await member.timeout(until, reason=f"{motivo} - da {ctx.author}")
        await ctx.send(f"🔇 {member.mention} è in timeout per **{human_duration(seconds)}**. Motivo: {motivo}")

    @commands.command(name="untimeout")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        """Rimuove il timeout da un utente."""
        await member.timeout(None, reason=f"Untimeout da {ctx.author}")
        await ctx.send(f"🔊 Timeout rimosso da {member.mention}.")

    # ---------------------------- BAN / KICK ----------------------------
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, motivo: str = "Nessun motivo"):
        await member.ban(reason=f"{motivo} - da {ctx.author}")
        await ctx.send(f"🔨 {member.mention} è stato bannato. Motivo: {motivo}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        user = discord.Object(id=user_id)
        try:
            await ctx.guild.unban(user)
            await ctx.send(f"✅ Utente con ID `{user_id}` sbannato.")
        except discord.NotFound:
            await ctx.send("⚠️ Utente non trovato tra i banditi.")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, motivo: str = "Nessun motivo"):
        await member.kick(reason=f"{motivo} - da {ctx.author}")
        await ctx.send(f"👢 {member.mention} è stato espulso. Motivo: {motivo}")

    # ---------------------------- CHANGENAME ----------------------------
    @commands.command(name="changename")
    @commands.has_permissions(manage_nicknames=True)
    async def changename(self, ctx, member: discord.Member, *, nuovo_nome: str):
        await member.edit(nick=nuovo_nome, reason=f"Changename da {ctx.author}")
        await ctx.send(f"✏️ Nickname di {member.mention} cambiato in **{nuovo_nome}**.")

    # ---------------------------- WARN SYSTEM ----------------------------
    @commands.command(name="warn")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, motivo: str = "Nessun motivo"):
        gid, uid = ctx.guild.id, member.id
        warns = warns_db.get(gid, uid, default=[])
        warns.append({
            "motivo": motivo,
            "mod": ctx.author.id,
            "data": discord.utils.utcnow().isoformat(),
        })
        warns_db.set(gid, uid, warns)
        await ctx.send(f"⚠️ {member.mention} ha ricevuto un warn ({len(warns)} totali). Motivo: {motivo}")

    @commands.command(name="unwarn")
    @commands.has_permissions(moderate_members=True)
    async def unwarn(self, ctx, member: discord.Member, indice: int):
        """Rimuove un singolo warn tramite indice (vedi ?warncount)."""
        gid, uid = ctx.guild.id, member.id
        warns = warns_db.get(gid, uid, default=[])
        if not (1 <= indice <= len(warns)):
            return await ctx.send("⚠️ Indice non valido.")
        removed = warns.pop(indice - 1)
        warns_db.set(gid, uid, warns)
        await ctx.send(f"✅ Rimosso il warn #{indice} ({removed['motivo']}) da {member.mention}.")

    @commands.command(name="clearwarn", aliases=["clearwarns", "resetwarn"])
    @commands.has_permissions(moderate_members=True)
    async def clearwarn(self, ctx, member: discord.Member):
        """Cancella tutti i warn di un utente."""
        warns_db.set(ctx.guild.id, member.id, [])
        await ctx.send(f"🧹 Tutti i warn di {member.mention} sono stati cancellati.")

    @commands.command(name="warncount")
    async def warncount(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        warns = warns_db.get(ctx.guild.id, member.id, default=[])
        if not warns:
            return await ctx.send(f"{member.mention} non ha warn.")
        embed = discord.Embed(title=f"Warn di {member}", color=discord.Color.orange())
        for i, w in enumerate(warns, start=1):
            mod = ctx.guild.get_member(w["mod"])
            embed.add_field(
                name=f"#{i} - {w['data'][:10]}",
                value=f"Motivo: {w['motivo']}\nDa: {mod.mention if mod else 'Sconosciuto'}",
                inline=False,
            )
        await ctx.send(embed=embed)

    # ---------------------------- PURGE ----------------------------
    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, quantita: int):
        """Cancella un numero di messaggi dal canale."""
        if quantita < 1 or quantita > 1000:
            return await ctx.send("⚠️ Inserisci un numero tra 1 e 1000.")
        deleted = await ctx.channel.purge(limit=quantita + 1)  # +1 per includere il comando stesso
        msg = await ctx.send(f"🧹 Cancellati {len(deleted) - 1} messaggi.")
        await msg.delete(delay=3)

    # ---------------------------- LOCK / UNLOCK ----------------------------
    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"🔒 {channel.mention} è stato bloccato.")

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"🔓 {channel.mention} è stato sbloccato.")

    # ---------------------------- LIVELLO / XP ----------------------------
    @commands.command(name="livello", aliases=["level", "rank"])
    async def livello(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        xp = xp_db.get(ctx.guild.id, member.id, default=0)
        level = level_from_xp(xp)
        next_level_xp = xp_for_level(level + 1)
        embed = discord.Embed(title=f"Livello di {member}", color=discord.Color.blurple())
        embed.add_field(name="Livello", value=str(level))
        embed.add_field(name="XP", value=f"{xp}/{next_level_xp}")
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="xpadd")
    @commands.has_permissions(manage_guild=True)
    async def xpadd(self, ctx, member: discord.Member, quantita: int):
        xp = xp_db.get(ctx.guild.id, member.id, default=0) + quantita
        xp_db.set(ctx.guild.id, member.id, max(0, xp))
        await ctx.send(f"✅ Aggiunti {quantita} XP a {member.mention}. Totale: {max(0, xp)}")

    @commands.command(name="xpremove")
    @commands.has_permissions(manage_guild=True)
    async def xpremove(self, ctx, member: discord.Member, quantita: int):
        xp = xp_db.get(ctx.guild.id, member.id, default=0) - quantita
        xp_db.set(ctx.guild.id, member.id, max(0, xp))
        await ctx.send(f"✅ Rimossi {quantita} XP a {member.mention}. Totale: {max(0, xp)}")

    # ---------------------------- MESSAGGI ----------------------------
    @commands.command(name="messagecount", aliases=["messaggicontati"])
    async def messagecount(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        count = msg_db.get(ctx.guild.id, member.id, default=0)
        await ctx.send(f"💬 {member.mention} ha inviato **{count}** messaggi.")

    @commands.command(name="addmessages")
    @commands.has_permissions(manage_guild=True)
    async def addmessages(self, ctx, member: discord.Member, quantita: int):
        count = msg_db.get(ctx.guild.id, member.id, default=0) + quantita
        msg_db.set(ctx.guild.id, member.id, max(0, count))
        await ctx.send(f"✅ Aggiunti {quantita} messaggi a {member.mention}. Totale: {max(0, count)}")

    @commands.command(name="resetmessages")
    @commands.has_permissions(manage_guild=True)
    async def resetmessages(self, ctx, member: discord.Member):
        msg_db.set(ctx.guild.id, member.id, 0)
        await ctx.send(f"🧹 Contatore messaggi di {member.mention} azzerato.")

    @commands.command(name="leavemessages", aliases=["messagesleaderboard", "topmessaggi"])
    async def leavemessages(self, ctx):
        """Classifica degli utenti per numero di messaggi inviati."""
        data = msg_db.get(ctx.guild.id, default={})
        if not data:
            return await ctx.send("Nessun dato disponibile.")
        ranking = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Classifica messaggi", color=discord.Color.gold())
        for i, (uid, count) in enumerate(ranking, start=1):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"Utente {uid}"
            embed.add_field(name=f"#{i} {name}", value=f"{count} messaggi", inline=False)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
