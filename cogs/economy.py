import random
import time

import discord
from discord.ext import commands

from utils.storage import Storage

eco_db = Storage("economy.json")       # gid -> uid -> {"balance": int, "luck": int}
cooldown_db = Storage("cooldowns.json")  # gid -> uid -> {"daily": ts, "work": ts, "mine": ts, "luckybox": ts}
shop_db = Storage("shop.json")         # gid -> {item: {"prezzo": int, "descrizione": str}}
inventory_db = Storage("inventory.json")  # gid -> uid -> {item: quantita}

DAILY_AMOUNT = 250
WORK_MIN, WORK_MAX = 50, 200
MINE_MIN, MINE_MAX = 20, 150
LUCKYBOX_MIN, LUCKYBOX_MAX = 50, 1000

DEFAULT_SHOP = {
    "box_comune": {"prezzo": 100, "descrizione": "Una box con premi in monete"},
    "box_rara": {"prezzo": 500, "descrizione": "Una box con premi migliori"},
    "box_leggendaria": {"prezzo": 2000, "descrizione": "Box con il jackpot più alto"},
}


def get_user(gid, uid):
    user = eco_db.get(gid, uid, default=None)
    if user is None:
        user = {"balance": 0, "luck": 0}
        eco_db.set(gid, uid, user)
    return user


def set_balance(gid, uid, value):
    user = get_user(gid, uid)
    user["balance"] = max(0, value)
    eco_db.set(gid, uid, user)


def add_balance(gid, uid, amount):
    user = get_user(gid, uid)
    set_balance(gid, uid, user["balance"] + amount)


def get_cooldown(gid, uid, key):
    return cooldown_db.get(gid, uid, key, default=0)


def set_cooldown(gid, uid, key):
    data = cooldown_db.get(gid, uid, default={})
    data[key] = time.time()
    cooldown_db.set(gid, uid, data)


def cooldown_left(gid, uid, key, seconds):
    last = get_cooldown(gid, uid, key)
    remaining = seconds - (time.time() - last)
    return max(0, remaining)


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------------------- BALANCE ----------------------------
    @commands.command(name="balance", aliases=["bal", "soldi"])
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = get_user(ctx.guild.id, member.id)
        embed = discord.Embed(title=f"💰 Portafoglio di {member.display_name}", color=discord.Color.green())
        embed.add_field(name="Monete", value=f"{user['balance']} 🪙")
        embed.add_field(name="Fortuna", value=f"{user['luck']} 🍀")
        await ctx.send(embed=embed)

    # ---------------------------- DAILY ----------------------------
    @commands.command(name="daily")
    async def daily(self, ctx):
        gid, uid = ctx.guild.id, ctx.author.id
        remaining = cooldown_left(gid, uid, "daily", 86400)
        if remaining > 0:
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            return await ctx.send(f"⏳ Hai già riscattato la daily. Riprova tra {h}h {m}m.")
        add_balance(gid, uid, DAILY_AMOUNT)
        set_cooldown(gid, uid, "daily")
        await ctx.send(f"🎁 Hai ricevuto la tua ricompensa giornaliera: **{DAILY_AMOUNT} 🪙**")

    # ---------------------------- WORK ----------------------------
    @commands.command(name="work")
    async def work(self, ctx):
        gid, uid = ctx.guild.id, ctx.author.id
        remaining = cooldown_left(gid, uid, "work", 3600)
        if remaining > 0:
            return await ctx.send(f"⏳ Sei stanco, riposa ancora {int(remaining // 60)} minuti.")
        guadagno = random.randint(WORK_MIN, WORK_MAX)
        add_balance(gid, uid, guadagno)
        set_cooldown(gid, uid, "work")
        lavori = ["barista", "programmatore", "tassista", "streamer", "cuoco", "corriere"]
        await ctx.send(f"💼 Hai lavorato come {random.choice(lavori)} e guadagnato **{guadagno} 🪙**")

    # ---------------------------- MINE ----------------------------
    @commands.command(name="mine")
    async def mine(self, ctx):
        gid, uid = ctx.guild.id, ctx.author.id
        remaining = cooldown_left(gid, uid, "mine", 1800)
        if remaining > 0:
            return await ctx.send(f"⏳ Il piccone deve raffreddarsi ancora {int(remaining // 60)} minuti.")
        guadagno = random.randint(MINE_MIN, MINE_MAX)
        add_balance(gid, uid, guadagno)
        set_cooldown(gid, uid, "mine")
        minerali = ["ferro", "oro", "diamante", "carbone", "smeraldo"]
        await ctx.send(f"⛏️ Hai minato {random.choice(minerali)} e guadagnato **{guadagno} 🪙**")

    # ---------------------------- TRIS (contro un altro utente) ----------------------------
    @commands.command(name="tris")
    async def tris(self, ctx, avversario: discord.Member, puntata: int = 0):
        """Sfida un altro utente a tris (bot arbitra, esito casuale semplificato)."""
        if avversario.bot or avversario == ctx.author:
            return await ctx.send("⚠️ Scegli un avversario umano diverso da te.")
        gid = ctx.guild.id
        if puntata > 0:
            sfidante = get_user(gid, ctx.author.id)
            sfidato = get_user(gid, avversario.id)
            if sfidante["balance"] < puntata or sfidato["balance"] < puntata:
                return await ctx.send("⚠️ Uno dei due giocatori non ha abbastanza monete per questa puntata.")

        msg = await ctx.send(
            f"❌⭕ {ctx.author.mention} sfida {avversario.mention} a Tris"
            + (f" per {puntata} 🪙!" if puntata else "!")
            + f"\n{avversario.mention}, reagisci con ✅ entro 30s per accettare."
        )
        await msg.add_reaction("✅")

        def check(reaction, user):
            return user == avversario and str(reaction.emoji) == "✅" and reaction.message.id == msg.id

        try:
            await self.bot.wait_for("reaction_add", timeout=30, check=check)
        except Exception:
            return await ctx.send("⌛ Nessuna risposta, sfida annullata.")

        vincitore = random.choice([ctx.author, avversario])
        perdente = avversario if vincitore == ctx.author else ctx.author
        if puntata > 0:
            add_balance(gid, vincitore.id, puntata)
            add_balance(gid, perdente.id, -puntata)
        await ctx.send(f"🏆 {vincitore.mention} ha vinto il Tris contro {perdente.mention}!"
                        + (f" (+{puntata} 🪙)" if puntata else ""))

    # ---------------------------- PAY / ADD / REMOVE ----------------------------
    @commands.command(name="pay")
    async def pay(self, ctx, member: discord.Member, importo: int):
        if importo <= 0:
            return await ctx.send("⚠️ L'importo deve essere positivo.")
        gid, uid = ctx.guild.id, ctx.author.id
        user = get_user(gid, uid)
        if user["balance"] < importo:
            return await ctx.send("⚠️ Non hai abbastanza monete.")
        add_balance(gid, uid, -importo)
        add_balance(gid, member.id, importo)
        await ctx.send(f"💸 {ctx.author.mention} ha inviato **{importo} 🪙** a {member.mention}.")

    @commands.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def add(self, ctx, member: discord.Member, importo: int):
        add_balance(ctx.guild.id, member.id, importo)
        await ctx.send(f"✅ Aggiunti **{importo} 🪙** a {member.mention}.")

    @commands.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def remove(self, ctx, member: discord.Member, importo: int):
        add_balance(ctx.guild.id, member.id, -importo)
        await ctx.send(f"✅ Rimossi **{importo} 🪙** a {member.mention}.")

    # ---------------------------- COINFLIP ----------------------------
    @commands.command(name="coinflip", aliases=["cf"])
    async def coinflip(self, ctx, puntata: int, scelta: str):
        scelta = scelta.lower()
        if scelta not in ("testa", "croce"):
            return await ctx.send("⚠️ Scegli `testa` oppure `croce`.")
        gid, uid = ctx.guild.id, ctx.author.id
        user = get_user(gid, uid)
        if puntata <= 0 or user["balance"] < puntata:
            return await ctx.send("⚠️ Puntata non valida o monete insufficienti.")
        esito = random.choice(["testa", "croce"])
        if esito == scelta:
            add_balance(gid, uid, puntata)
            await ctx.send(f"🪙 È uscito **{esito}**! Hai vinto **{puntata} 🪙**")
        else:
            add_balance(gid, uid, -puntata)
            await ctx.send(f"🪙 È uscito **{esito}**! Hai perso **{puntata} 🪙**")

    # ---------------------------- BLACKJACK ----------------------------
    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx, puntata: int):
        gid, uid = ctx.guild.id, ctx.author.id
        user = get_user(gid, uid)
        if puntata <= 0 or user["balance"] < puntata:
            return await ctx.send("⚠️ Puntata non valida o monete insufficienti.")

        def draw():
            return random.randint(1, 11)

        player = [draw(), draw()]
        dealer = [draw(), draw()]

        await ctx.send(
            f"🃏 Le tue carte: {player} (totale {sum(player)})\n"
            f"🃏 Carta visibile del banco: {dealer[0]}\n"
            f"Scrivi `carta` per pescare o `stai` per fermarti (hai 20s per mossa)."
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ("carta", "stai")

        while sum(player) < 21:
            try:
                m = await self.bot.wait_for("message", timeout=20, check=check)
            except Exception:
                break
            if m.content.lower() == "carta":
                player.append(draw())
                await ctx.send(f"🃏 Le tue carte: {player} (totale {sum(player)})")
            else:
                break

        player_total = sum(player)
        if player_total > 21:
            add_balance(gid, uid, -puntata)
            return await ctx.send(f"💥 Hai sballato con {player_total}! Perdi **{puntata} 🪙**")

        while sum(dealer) < 17:
            dealer.append(draw())
        dealer_total = sum(dealer)

        await ctx.send(f"🏦 Carte del banco: {dealer} (totale {dealer_total})")

        if dealer_total > 21 or player_total > dealer_total:
            add_balance(gid, uid, puntata)
            await ctx.send(f"🎉 Hai vinto **{puntata} 🪙**!")
        elif player_total == dealer_total:
            await ctx.send("🤝 Pareggio, nessuna moneta persa.")
        else:
            add_balance(gid, uid, -puntata)
            await ctx.send(f"😔 Hai perso **{puntata} 🪙**.")

    # ---------------------------- ROULETTE ----------------------------
    @commands.command(name="roulette")
    async def roulette(self, ctx, puntata: int, colore: str):
        colore = colore.lower()
        if colore not in ("rosso", "nero", "verde"):
            return await ctx.send("⚠️ Scegli `rosso`, `nero` o `verde`.")
        gid, uid = ctx.guild.id, ctx.author.id
        user = get_user(gid, uid)
        if puntata <= 0 or user["balance"] < puntata:
            return await ctx.send("⚠️ Puntata non valida o monete insufficienti.")

        numero = random.randint(0, 36)
        if numero == 0:
            esito = "verde"
        else:
            esito = "rosso" if numero % 2 == 1 else "nero"

        if colore == esito:
            moltiplicatore = 14 if esito == "verde" else 2
            vincita = puntata * moltiplicatore
            add_balance(gid, uid, vincita - puntata)
            await ctx.send(f"🎡 È uscito **{numero} ({esito})**! Hai vinto **{vincita} 🪙**")
        else:
            add_balance(gid, uid, -puntata)
            await ctx.send(f"🎡 È uscito **{numero} ({esito})**! Hai perso **{puntata} 🪙**")

    # ---------------------------- LEADERBOARD ----------------------------
    @commands.command(name="leaderboard", aliases=["lb", "eco-top"])
    async def leaderboard(self, ctx):
        data = eco_db.get(ctx.guild.id, default={})
        if not data:
            return await ctx.send("Nessun dato economico disponibile.")
        ranking = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Classifica economia", color=discord.Color.gold())
        for i, (uid, u) in enumerate(ranking, start=1):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"Utente {uid}"
            embed.add_field(name=f"#{i} {name}", value=f"{u['balance']} 🪙", inline=False)
        await ctx.send(embed=embed)

    # ---------------------------- SHOP / BUY / INVENTORY ----------------------------
    @commands.command(name="shop")
    async def shop(self, ctx):
        items = shop_db.get(ctx.guild.id, default=None)
        if items is None:
            items = DEFAULT_SHOP
            shop_db.set(ctx.guild.id, items)
        embed = discord.Embed(title="🛒 Shop", color=discord.Color.blue())
        for name, info in items.items():
            embed.add_field(name=f"{name} - {info['prezzo']} 🪙", value=info["descrizione"], inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, *, oggetto: str):
        gid, uid = ctx.guild.id, ctx.author.id
        items = shop_db.get(gid, default=DEFAULT_SHOP)
        oggetto = oggetto.lower().replace(" ", "_")
        if oggetto not in items:
            return await ctx.send("⚠️ Oggetto non trovato nello shop. Controlla `?shop`.")
        prezzo = items[oggetto]["prezzo"]
        user = get_user(gid, uid)
        if user["balance"] < prezzo:
            return await ctx.send("⚠️ Non hai abbastanza monete.")
        add_balance(gid, uid, -prezzo)
        inv = inventory_db.get(gid, uid, default={})
        inv[oggetto] = inv.get(oggetto, 0) + 1
        inventory_db.set(gid, uid, inv)
        await ctx.send(f"✅ Hai acquistato **{oggetto}**!")

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        inv = inventory_db.get(ctx.guild.id, member.id, default={})
        if not inv:
            return await ctx.send(f"{member.mention} non ha oggetti nell'inventario.")
        embed = discord.Embed(title=f"🎒 Inventario di {member.display_name}", color=discord.Color.purple())
        for item, qty in inv.items():
            embed.add_field(name=item, value=f"x{qty}", inline=True)
        await ctx.send(embed=embed)

    # ---------------------------- OPEN BOX ----------------------------
    @commands.command(name="openbox", aliases=["apribox"])
    async def openbox(self, ctx, *, oggetto: str):
        gid, uid = ctx.guild.id, ctx.author.id
        oggetto = oggetto.lower().replace(" ", "_")
        inv = inventory_db.get(gid, uid, default={})
        if inv.get(oggetto, 0) <= 0:
            return await ctx.send("⚠️ Non possiedi questa box. Compra con `?buy`.")
        inv[oggetto] -= 1
        if inv[oggetto] <= 0:
            inv.pop(oggetto)
        inventory_db.set(gid, uid, inv)

        base = {"box_comune": (50, 200), "box_rara": (200, 800), "box_leggendaria": (800, 3000)}
        low, high = base.get(oggetto, (50, 200))
        user = get_user(gid, uid)
        bonus = 1 + (user["luck"] * 0.01)
        premio = int(random.randint(low, high) * bonus)
        add_balance(gid, uid, premio)
        await ctx.send(f"📦 Hai aperto **{oggetto}** e ottenuto **{premio} 🪙**!")

    # ---------------------------- LUCKYBOX (1 al giorno) ----------------------------
    @commands.command(name="luckybox")
    async def luckybox(self, ctx):
        gid, uid = ctx.guild.id, ctx.author.id
        remaining = cooldown_left(gid, uid, "luckybox", 86400)
        if remaining > 0:
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            return await ctx.send(f"⏳ Hai già aperto la luckybox oggi. Riprova tra {h}h {m}m.")
        user = get_user(gid, uid)
        bonus = 1 + (user["luck"] * 0.01)
        premio = int(random.randint(LUCKYBOX_MIN, LUCKYBOX_MAX) * bonus)
        add_balance(gid, uid, premio)
        set_cooldown(gid, uid, "luckybox")
        await ctx.send(f"🍀 Hai aperto la tua luckybox giornaliera e ottenuto **{premio} 🪙**!")

    # ---------------------------- LUCKY (aumenta fortuna) ----------------------------
    @commands.command(name="lucky")
    async def lucky(self, ctx, costo: int = 500):
        """Spende monete per aumentare di 1 punto la fortuna (aumenta i premi delle box)."""
        gid, uid = ctx.guild.id, ctx.author.id
        user = get_user(gid, uid)
        if user["balance"] < costo:
            return await ctx.send(f"⚠️ Ti servono almeno {costo} 🪙 per aumentare la fortuna.")
        add_balance(gid, uid, -costo)
        user = get_user(gid, uid)
        user["luck"] += 1
        eco_db.set(gid, uid, user)
        await ctx.send(f"🍀 Fortuna aumentata! Ora hai **{user['luck']}** punti fortuna.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
