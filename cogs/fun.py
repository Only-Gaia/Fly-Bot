import random

import discord
from discord.ext import commands

RISPOSTE_8BALL = [
    "Sì, decisamente.", "È certo.", "Senza dubbio.", "Sì.",
    "Molto probabile.", "Le prospettive sono buone.",
    "Rispondi di nuovo più tardi.", "Chiedi di nuovo.",
    "Meglio non dirtelo ora.", "Non posso prevederlo ora.",
    "Non contarci.", "La mia risposta è no.", "Le mie fonti dicono di no.",
    "Molto dubbio.",
]


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="8ball")
    async def eightball(self, ctx, *, domanda: str):
        await ctx.send(f"🎱 **Domanda:** {domanda}\n**Risposta:** {random.choice(RISPOSTE_8BALL)}")

    @commands.command(name="say")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, testo: str):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(testo)

    @commands.command(name="ship")
    async def ship(self, ctx, membro1: discord.Member, membro2: discord.Member = None):
        membro2 = membro2 or ctx.author
        percentuale = random.randint(0, 100)
        barra_piena = "❤️" * (percentuale // 10)
        barra_vuota = "🖤" * (10 - percentuale // 10)
        nome_ship = membro1.display_name[:len(membro1.display_name)//2] + membro2.display_name[len(membro2.display_name)//2:]
        embed = discord.Embed(
            title=f"💘 {membro1.display_name} + {membro2.display_name} = {nome_ship}",
            description=f"{barra_piena}{barra_vuota} **{percentuale}%**",
            color=discord.Color.pink(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="rendigay")
    async def rendigay(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        percentuale = random.randint(0, 100)
        await ctx.send(f"🏳️‍🌈 {member.mention} è **{percentuale}%** gay!")

    @commands.command(name="rendilesbica", aliases=["rendilesbico"])
    async def rendilesbica(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        percentuale = random.randint(0, 100)
        await ctx.send(f"🏳️‍🌈 {member.mention} è **{percentuale}%** lesbica/o!")

    # ---------------------------- AZIONI ----------------------------
    @commands.command(name="kiss")
    async def kiss(self, ctx, member: discord.Member):
        await ctx.send(f"💋 {ctx.author.mention} bacia {member.mention}!")

    @commands.command(name="clap")
    async def clap(self, ctx, member: discord.Member):
        await ctx.send(f"👏 {ctx.author.mention} applaude {member.mention}!")

    @commands.command(name="slap")
    async def slap(self, ctx, member: discord.Member):
        await ctx.send(f"👋 {ctx.author.mention} schiaffeggia {member.mention}!")

    @commands.command(name="hug")
    async def hug(self, ctx, member: discord.Member):
        await ctx.send(f"🤗 {ctx.author.mention} abbraccia {member.mention}!")

    @commands.command(name="kill")
    async def kill(self, ctx, member: discord.Member):
        await ctx.send(f"🔪 {ctx.author.mention} uccide (per finta!) {member.mention}!")

    # ---------------------------- NITRODONATE (scherzo) ----------------------------
    @commands.command(name="nitrodonate")
    async def nitrodonate(self, ctx, member: discord.Member):
        """Scherzo: finto regalo di Nitro, al click compare una gif buffa."""
        embed = discord.Embed(
            title="Hai ricevuto un regalo!",
            description=f"{ctx.author.mention} ha inviato **Discord Nitro** a {member.mention}!\nPremi il pulsante per riscattarlo.",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/en/6/6f/Discord_Nitro_Logo.png")

        view = discord.ui.View(timeout=300)
        button = discord.ui.Button(label="Reclama Nitro", style=discord.ButtonStyle.primary, emoji="🎁")

        async def callback(interaction: discord.Interaction):
            if interaction.user != member:
                return await interaction.response.send_message(
                    "Questo regalo non è per te!", ephemeral=True
                )
            scherzo_embed = discord.Embed(
                title="😹 PESCATO!",
                description="Non hai ricevuto nessun Nitro, era solo uno scherzo!",
                color=discord.Color.red(),
            )
            # GIF divertente di un gatto/cane che balla
            scherzo_embed.set_image(url="https://media.tenor.com/2roX3uxSKfEAAAAC/dancing-cat.gif")
            await interaction.response.edit_message(embed=scherzo_embed, view=None)

        button.callback = callback
        view.add_item(button)
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
