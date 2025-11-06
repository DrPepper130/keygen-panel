import os
import asyncio
import requests
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))
PANEL_API = os.getenv("PANEL_API")
API_SECRET = os.getenv("API_SECRET")

# Lockr ad link
GENERATE_KEY_URL = "https://lockr.so/qTLYPVdiz"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

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
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        key = str(self.key_input.value).strip()

        try:
            resp = requests.post(
                f"{PANEL_API}/api/redeem",
                json={"key": key, "discord_id": str(self.member.id)},
                headers={"X-API-KEY": API_SECRET},
                timeout=5,
            )
            data = resp.json()
        except Exception:
            await interaction.response.send_message(
                "There was an error contacting the key server.", ephemeral=True
            )
            return

        if not data.get("ok"):
            await interaction.response.send_message(
                f"Key error: {data.get('message')}", ephemeral=True
            )
            return

        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(self.member.id) or await guild.fetch_member(self.member.id)
        role = guild.get_role(ROLE_ID)
        await member.add_roles(role, reason="Key redeemed")

        await interaction.response.send_message(
            "✅ VIP role granted for 1 hour.", ephemeral=True
        )

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
        super().__init__(timeout=None)

    # Blue "Access VIP Content" button
    @discord.ui.button(
        label="Access VIP Content",
        style=discord.ButtonStyle.primary,
        custom_id="keygen_access"
    )
    async def access_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"🔗 Click below to generate your key:\n{GENERATE_KEY_URL}",
            ephemeral=True
        )

    # Green "Redeem Key" button
    @discord.ui.button(
        label="Redeem Key",
        style=discord.ButtonStyle.success,
        custom_id="keygen_redeem"
    )
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RedeemKeyModal(interaction.user)
        await interaction.response.send_modal(modal)


# ---- Bot Ready ----
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    bot.add_view(KeyView())
    print("Persistent view loaded and ready.")


# ---- Post Embed Command ----
@bot.command(name="postkeymsg")
@commands.has_permissions(administrator=True)
async def postkeymsg(ctx: commands.Context):
    embed = discord.Embed(
        title="🔞 Get Your FREE NSFW Content!",
        description=(
            "**Follow the simple steps below to unlock your NSFW content!**\n\n"
            "> Click on the **Access VIP Content** button.\n"
            "> Watch the ads & copy the generated key.\n"
            "> Press **Redeem Key** and enter the key.\n"
            "> Done — enjoy your access for **1 hour!**"
        ),
        color=discord.Color.purple(),
    )
    embed.set_image(url="https://i.imgur.com/OUH4pIk.gif")
    embed.set_footer(text="Powered by KeyGen")

    await ctx.send(embed=embed, view=KeyView())


bot.run(TOKEN)
