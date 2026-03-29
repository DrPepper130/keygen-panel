import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

DEFAULT_URL = os.getenv("PANEL_API") or "https://checkout.megafile.one/b/cNi00c9Ypf3g9aV28q33W05"
DEFAULT_IMAGE_URL = "https://i.imgur.com/4EZX8AZ.gif"

if not TOKEN:
    raise Exception("Missing DISCORD_BOT_TOKEN environment variable")

intents = discord.Intents.default()
intents.message_content = True  # REQUIRED for prefix commands like !vip

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

    def __init__(self, access_url):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Access VIP Content",
                style=discord.ButtonStyle.link,
                url=access_url
            )
        )

        self.add_item(RedeemButton())


@bot.command()
@commands.has_permissions(manage_messages=True)
async def vip(ctx, channel: discord.TextChannel = None, image_url=None, access_url=None):

    channel = channel or ctx.channel
    image_url = image_url or DEFAULT_IMAGE_URL
    access_url = access_url or DEFAULT_URL

    embed = discord.Embed(
        title="🔞Redeem your VIP Access key here!🔞",
        description=(
            "#### Follow the simple steps below to unlock your private vault!\n\n"
            f"> Click {channel.mention}.\n"
            "> Complete checkout to redeem your key.\n"
            "> Press Redeem Key and enter the key.\n"
            "> Done - enjoy your access!"
        ),
        color=0x00ff00
    )

    embed.set_image(url=image_url)

    await ctx.send(
        embed=embed,
        view=PanelButtons(access_url)
    )

    # delete the !vip command message
    try:
        await ctx.message.delete()
    except:
        pass


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


bot.run(TOKEN)
