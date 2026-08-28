import discord
from discord.ext import commands

from utils.storage import Storage

ticket_db = Storage("tickets.json")  # gid -> {"category": id, "log_channel": id}
open_tickets_db = Storage("open_tickets.json")  # gid -> channel_id -> {"owner": id, "claimed_by": id|None, "tipo": str}

TIPI_TICKET = {
    "partnership": ("🤝", "Partnership"),
    "provino": ("🎤", "Provino Staff"),
    "segnala": ("🚨", "Segnala Utente"),
    "giveaway": ("🎉", "Riscatta Giveaway"),
    "aiuto": ("❓", "Aiuto Generale"),
}


def get_settings(gid):
    return ticket_db.get(gid, default={"category": None, "log_channel": None})


class TicketOpenView(discord.ui.View):
    """Vista persistente del pannello ticket iniziale."""

    def __init__(self):
        super().__init__(timeout=None)

    async def crea_ticket(self, interaction: discord.Interaction, tipo: str):
        guild = interaction.guild
        emoji, label = TIPI_TICKET[tipo]
        settings = get_settings(guild.id)
        category = guild.get_channel(settings["category"]) if settings["category"] else None

        # Evita ticket duplicati dello stesso tipo aperti dallo stesso utente
        existing = open_tickets_db.get(guild.id, default={})
        for chan_id, info in existing.items():
            if info["owner"] == interaction.user.id and info["tipo"] == tipo:
                canale = guild.get_channel(int(chan_id))
                if canale:
                    return await interaction.response.send_message(
                        f"Hai già un ticket aperto: {canale.mention}", ephemeral=True
                    )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        channel_name = f"{tipo}-{interaction.user.name}"[:90]
        canale = await guild.create_text_channel(
            channel_name, category=category, overwrites=overwrites,
            reason=f"Ticket aperto da {interaction.user}"
        )

        all_tickets = open_tickets_db.get(guild.id, default={})
        all_tickets[str(canale.id)] = {"owner": interaction.user.id, "claimed_by": None, "tipo": tipo}
        open_tickets_db.set(guild.id, all_tickets)

        embed = discord.Embed(
            title=f"{emoji} Ticket: {label}",
            description=f"Ciao {interaction.user.mention}! Lo staff ti risponderà a breve.\n"
                        f"Usa i pulsanti sotto per gestire il ticket.",
            color=discord.Color.blurple(),
        )
        await canale.send(embed=embed, view=TicketManageView())
        await interaction.response.send_message(f"✅ Ticket creato: {canale.mention}", ephemeral=True)

    @discord.ui.button(label="Partnership", emoji="🤝", style=discord.ButtonStyle.primary, custom_id="ticket_partnership")
    async def partnership(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crea_ticket(interaction, "partnership")

    @discord.ui.button(label="Provino Staff", emoji="🎤", style=discord.ButtonStyle.primary, custom_id="ticket_provino")
    async def provino(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crea_ticket(interaction, "provino")

    @discord.ui.button(label="Segnala Utente", emoji="🚨", style=discord.ButtonStyle.danger, custom_id="ticket_segnala")
    async def segnala(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crea_ticket(interaction, "segnala")

    @discord.ui.button(label="Riscatta Giveaway", emoji="🎉", style=discord.ButtonStyle.success, custom_id="ticket_giveaway")
    async def giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crea_ticket(interaction, "giveaway")

    @discord.ui.button(label="Aiuto Generale", emoji="❓", style=discord.ButtonStyle.secondary, custom_id="ticket_aiuto")
    async def aiuto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crea_ticket(interaction, "aiuto")


class TicketManageView(discord.ui.View):
    """Vista persistente dentro ogni ticket già aperto."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", emoji="🙋", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Solo lo staff può fare claim.", ephemeral=True)
        tickets = open_tickets_db.get(interaction.guild.id, default={})
        info = tickets.get(str(interaction.channel.id))
        if not info:
            return await interaction.response.send_message("⚠️ Ticket non trovato nel database.", ephemeral=True)
        info["claimed_by"] = interaction.user.id
        tickets[str(interaction.channel.id)] = info
        open_tickets_db.set(interaction.guild.id, tickets)
        await interaction.response.send_message(f"🙋 Ticket preso in carico da {interaction.user.mention}.")

    @discord.ui.button(label="Unclaim", emoji="🙅", style=discord.ButtonStyle.secondary, custom_id="ticket_unclaim")
    async def unclaim(self, interaction: discord.Interaction, button: discord.ui.Button):
        tickets = open_tickets_db.get(interaction.guild.id, default={})
        info = tickets.get(str(interaction.channel.id))
        if not info:
            return await interaction.response.send_message("⚠️ Ticket non trovato nel database.", ephemeral=True)
        info["claimed_by"] = None
        tickets[str(interaction.channel.id)] = info
        open_tickets_db.set(interaction.guild.id, tickets)
        await interaction.response.send_message(f"🙅 Ticket rilasciato da {interaction.user.mention}.")

    @discord.ui.button(label="Aggiungi Utente", emoji="➕", style=discord.ButtonStyle.secondary, custom_id="ticket_add_user")
    async def aggiungi_utente(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Solo lo staff può aggiungere utenti.", ephemeral=True)
        await interaction.response.send_message(
            "Scrivi in chat la menzione dell'utente da aggiungere (hai 30s).", ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.mentions

        try:
            msg = await interaction.client.wait_for("message", timeout=30, check=check)
        except Exception:
            return
        member = msg.mentions[0]
        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.channel.send(f"➕ {member.mention} è stato aggiunto al ticket.")

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Il ticket verrà chiuso tra 5 secondi...")
        tickets = open_tickets_db.get(interaction.guild.id, default={})
        tickets.pop(str(interaction.channel.id), None)
        open_tickets_db.set(interaction.guild.id, tickets)
        await interaction.channel.send("⏳ Chiusura in corso...", delete_after=5)
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket chiuso da {interaction.user}")

    @discord.ui.button(label="Close with reaction", emoji="✅", style=discord.ButtonStyle.secondary, custom_id="ticket_close_reaction")
    async def close_with_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = await interaction.channel.send(
            f"{interaction.user.mention} vuole chiudere il ticket. Reagisci con ✅ per confermare (30s)."
        )
        await msg.add_reaction("✅")
        await interaction.response.defer()

        def check(reaction, user):
            return (
                reaction.message.id == msg.id
                and str(reaction.emoji) == "✅"
                and not user.bot
            )

        try:
            await interaction.client.wait_for("reaction_add", timeout=30, check=check)
        except Exception:
            return await interaction.channel.send("⌛ Chiusura annullata, nessuna conferma ricevuta.")

        tickets = open_tickets_db.get(interaction.guild.id, default={})
        tickets.pop(str(interaction.channel.id), None)
        open_tickets_db.set(interaction.guild.id, tickets)
        await interaction.channel.send("✅ Conferma ricevuta, chiusura in corso...")
        import asyncio
        await asyncio.sleep(3)
        await interaction.channel.delete(reason="Ticket chiuso con conferma reazione")


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Registra le view persistenti (i pulsanti funzionano anche dopo il riavvio del bot)
        bot.add_view(TicketOpenView())
        bot.add_view(TicketManageView())

    @commands.command(name="pannelloticket")
    @commands.has_permissions(manage_guild=True)
    async def pannelloticket(self, ctx, categoria: discord.CategoryChannel = None):
        """Invia il pannello ticket con i pulsanti configurati."""
        settings = get_settings(ctx.guild.id)
        if categoria:
            settings["category"] = categoria.id
            ticket_db.set(ctx.guild.id, settings)

        embed = discord.Embed(
            title="🎫 Centro Assistenza",
            description=(
                "Apri un ticket selezionando una delle categorie qui sotto:\n\n"
                "🤝 **Partnership** — proponi una collaborazione\n"
                "🎤 **Provino Staff** — candidati per lo staff\n"
                "🚨 **Segnala Utente** — segnala un comportamento scorretto\n"
                "🎉 **Riscatta Giveaway** — riscatta la tua vincita\n"
                "❓ **Aiuto Generale** — richiedi supporto"
            ),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=TicketOpenView())


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
