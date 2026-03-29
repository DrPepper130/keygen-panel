import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = "YOUR_BOT_TOKEN"
STRIPE_URL = "https://buy.stripe.com/YOUR_LINK"
IMAGE_URL = "https://i.imgur.com/4IHj6in.gif"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# -------------------------
# MODAL (popup input box)
# -------------------------
class RedeemModal(discord.ui.Modal, title="Redeem your key"):

    key_input = discord.ui.TextInput(
        label="Paste your key",
        placeholder="e.g. AbCdE123...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "This key does not exist.",
            ephemeral=True
        )


# -------------------------
# BUTTON VIEW
# -------------------------
class PanelButtons(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Access VIP Content",
        style=discord.ButtonStyle.link,
        url=STRIPE_URL
    )
    async def access_button(self, interaction, button):
        pass

    @discord.ui.button(
        label="Redeem Key",
        style=discord.ButtonStyle.success
    )
    async def redeem_button(self, interaction: discord.Interaction, button):

        await interaction.response.send_modal(RedeemModal())


# -------------------------
# PANEL COMMAND
# -------------------------
@bot.tree.command(name="vip-panel", description="Post the VIP panel")
async def vip_panel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="Redeem your VIP Access key here!",
        description=(
            "Follow the simple steps below to unlock your private vault!\n\n"
            "Click # VIP-ACCESS.\n"
            "Complete checkout to redeem your key.\n"
            "Press Redeem Key and enter the key.\n"
            "Done - enjoy your access!"
        ),
        color=0xff4d00
    )

    embed.set_image(url=IMAGE_URL)

    await interaction.response.send_message(
        embed=embed,
        view=PanelButtons()
    )


# -------------------------
# READY EVENT
# -------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


bot.run(TOKEN)
