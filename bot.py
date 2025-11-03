import os
import asyncio
import requests
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))
PANEL_API = os.getenv("PANEL_API")  # e.g. https://keygen-panel.onrender.com
API_SECRET = os.getenv("API_SECRET")  # must match Flask

# this is the page you want users to be sent to to GENERATE the key
GENERATE_KEY_URL = os.getenv("GENERATE_KEY_URL", "https://your-lockr-page.com")

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ---- Modal for key input ----
class RedeemKeyModal(discord.ui.Modal, title="Redeem your key"):
    key_input = discord.ui.TextInput(
        label="Paste your key",
        placeholder="e.g. AbCdE123...",
        required=True,
        max_length=100,
    )

    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member  # the user who opened the modal

    async def on_submit(self, interaction: discord.Interaction):
        key = str(self.key_input.value).strip()

        # call panel API
        try:
            resp = requests.post(
                f"{PANEL_API}/api/redeem",
                json={"key": key, "discord_id": str(self.member.id)},
                headers={"X-API-KEY": API_SECRET},
                timeout=5,
            )
            data = resp.json()
        except Exception as e:
            await interaction.response.send_message(
                "There was an error contacting the key server.", ephemeral=True
            )
            return

        if not data.get("ok"):
            await interaction.response.send_message(
                f"Key error: {data.get('message')}", ephemeral=True
            )
            return

        # give role
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(self.member.id) or await guild.fetch_member(self.member.id)
        role = guild.get_role(ROLE_ID)
        await member.add_roles(role, reason="Key redeemed")

        await interaction.response.send_message(
            "✅ VIP role granted for 1 hour.", ephemeral=True
        )

        # schedule removal
        async def remove_later():
            await asyncio.sleep(3600)
            try:
                await member.remove_roles(role, reason="VIP expired")
            except Exception:
                pass

        bot.loop.create_task(remove_later())


# ---- View with buttons ----
class KeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent view

    # blue button -> open URL (generate key)
    @discord.ui.button(label="Generate Key", style=discord.ButtonStyle.blurple)
    async def generate_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        # better UX is a URL button, but we can just send the link
        await interaction.response.send_message(
            f"Go here to generate your key:\n{GENERATE_KEY_URL}", ephemeral=True
        )

    # green button -> open modal
    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.success)
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RedeemKeyModal(interaction.user)
        await interaction.response.send_modal(modal)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    # register persistent view so buttons keep working after restart
    bot.add_view(KeyView())


# command to post the embed once
@bot.command(name="postkeymsg")
@commands.has_permissions(administrator=True)
async def postkeymsg(ctx: commands.Context):
    embed = discord.Embed(
        title="/vita 🍑 18+ Key System",
        description=(
            "**Here is a tutorial for access**\n"
            "1. Click the **Generate Key** button.\n"
            "2. Wait to be redirected to the ad page.\n"
            "3. Watch the ads & copy your key.\n"
            "4. Press **Redeem Key** and complete the steps.\n"
            "**Done!** Enjoy your access for **1 hour**! 🔐"
        ),
        color=discord.Color.purple(),
    )
    embed.set_image(url="https://your-cdn-or-image-url.com/vip.png")
    embed.set_footer(text="KeyGen – your gateway to exclusive access")

    await ctx.send(embed=embed, view=KeyView())


bot.run(TOKEN)
