import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
STRIPE_URL = os.getenv("PANEL_API") or "https://checkout.megafile.one/b/cNi00c9Ypf3g9aV28q33W05"
IMAGE_URL = "https://i.imgur.com/4EZX8AZ.gif"

if not TOKEN:
    raise Exception("Missing DISCORD_BOT_TOKEN environment variable")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


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


class RedeemButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Redeem Key",
            style=discord.ButtonStyle.success
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RedeemModal())


class PanelButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Access VIP Content",
                style=discord.ButtonStyle.link,
                url=STRIPE_URL
            )
        )

        self.add_item(RedeemButton())


@bot.tree.command(name="vip-panel", description="Post the VIP panel")
async def vip_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔞Redeem your VIP Access key here!🔞",
        description=(
            "### Follow the simple steps below to unlock your private vault!\n\n"
            "> Click https://discord.com/channels/1434255594579034175/1434256246306902088.\n"
            "> Complete checkout to redeem your key.\n"
            "> Press Redeem Key and enter the key.\n"
            "> Done - enjoy your access!"
        ),
        color=0xff5a00
    )

    embed.set_image(url=IMAGE_URL)

    await interaction.response.send_message(
        embed=embed,
        view=PanelButtons()
    )


@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()
    except Exception as e:
        print(f"Sync error: {e}")

    print(f"Logged in as {bot.user}")


bot.run(TOKEN)
