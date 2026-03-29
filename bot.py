import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEFAULT_URL = os.getenv("PANEL_API") or "https://checkout.megafile.one/b/cNi00c9Ypf3g9aV28q33W05"
DEFAULT_IMAGE_URL = "https://i.imgur.com/4lhj6in.gif"

if not TOKEN:
    raise Exception("Missing DISCORD_BOT_TOKEN environment variable")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

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


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    print(f"SAW MESSAGE: {message.content} | from {message.author} in #{message.channel}")

    await bot.process_commands(message)


@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("pong")


@bot.command(name="vip")
@commands.has_permissions(manage_messages=True)
async def vip(ctx, channel: discord.TextChannel = None, image_url: str = None, access_url: str = None):
    channel = channel or ctx.channel
    image_url = image_url or DEFAULT_IMAGE_URL
    access_url = access_url or DEFAULT_URL

    embed = discord.Embed(
        title="🔞Redeem your VIP Access key here!🔞",
        description=(
            "### Follow the simple steps below to unlock your private vault!\n\n"
            f"> Click {channel.mention}.\n"
            "> Complete checkout to redeem your key.\n"
            "> Press Redeem Key and enter the key.\n"
            "> Done - enjoy your access!"
        ),
        color=0x00ff00
    )

    embed.set_image(url=image_url)

    await ctx.send(embed=embed, view=PanelButtons(access_url))

    try:
        await ctx.message.delete()
    except Exception as e:
        print(f"Could not delete command message: {e}")


@vip.error
async def vip_error(ctx, error):
    print(f"VIP ERROR: {error}")
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You need Manage Messages permission to use this command.", delete_after=5)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid channel or command format.", delete_after=5)
    else:
        await ctx.send(f"Error: {error}", delete_after=5)


bot.run(TOKEN)
