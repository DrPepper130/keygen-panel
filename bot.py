import os
import asyncio
import requests
import discord
from discord.ext import commands
import uuid  # for a run id

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))
PANEL_API = os.getenv("PANEL_API")
API_SECRET = os.getenv("API_SECRET")

# Lockr ad link
GENERATE_KEY_URL = "https://lockr.so/qTLYPVdiz"

# your Discord user ID for testing DMs
TEST_USER_ID = 1434249225432072344  # Lucas

# list of users the bot can DM (expand later / pull from DB later)
AUTHORIZED_IDS = [
    TEST_USER_ID,
    # add more IDs here
]

# unique id for THIS running bot process
RUN_ID = str(uuid.uuid4())[:8]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- KEY REDEEM FLOW ----------

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


class KeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Access VIP Content",
        style=discord.ButtonStyle.primary,
        custom_id="keygen_access",
    )
    async def access_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"🔗 Click below to generate your key:\n{GENERATE_KEY_URL}",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Redeem Key",
        style=discord.ButtonStyle.success,
        custom_id="keygen_redeem",
    )
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RedeemKeyModal(interaction.user)
        await interaction.response.send_modal(modal)


# ---------- BOT READY ----------

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})  run={RUN_ID}")
    bot.add_view(KeyView())
    print("Persistent view loaded and ready.")


# ---------- CHANNEL COMMAND TO POST THE KEY MESSAGE ----------

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


# ---------- DM HELPERS (plain message) ----------
# DO NOT TOUCH MESSAGE STYLE

def build_plain_dm_text(user: discord.User):
    return (
        f"**🎉 Congratulations {user.mention}, you have won Nitro! 🎉[.](https://i.imgur.com/5tGaJts.png)**"
    )


def build_button_view():
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="🎁 Claim",
            url=GENERATE_KEY_URL,
            style=discord.ButtonStyle.link,
        )
    )
    return view


# ---------- DM TEST: ONLY TO YOU ----------

@bot.command(name="dmtest")
@commands.has_permissions(administrator=True)
async def dmtest(ctx: commands.Context):
    """Send the plain Nitro-style message to just Lucas."""
    print(f"[dmtest] triggered by {ctx.author} run={RUN_ID}")
    try:
        user = await bot.fetch_user(TEST_USER_ID)
        text = build_plain_dm_text(user)
        view = build_button_view()
        await user.send(content=text, view=view)
        # channel confirmation WITH run id
        await ctx.send(f"✅ Sent DM to test user. run={RUN_ID}")
    except discord.Forbidden:
        await ctx.send(f"❌ Can't DM you (DMs closed or blocked). run={RUN_ID}")
    except Exception as e:
        await ctx.send(f"❌ Error sending DM: {e} run={RUN_ID}")


# ---------- DM BROADCAST: TO EVERYONE IN AUTHORIZED_IDS ----------

@bot.command(name="dmbroadcast")
@commands.has_permissions(administrator=True)
async def dmbroadcast(ctx: commands.Context):
    """Send the plain Nitro-style message to everyone in AUTHORIZED_IDS."""
    await ctx.send(f"📨 Starting broadcast to {len(AUTHORIZED_IDS)} users... run={RUN_ID}")
    success = 0
    failed = 0

    for uid in AUTHORIZED_IDS:
        try:
            user = await bot.fetch_user(uid)
            text = build_plain_dm_text(user)
            view = build_button_view()
            await user.send(content=text, view=view)
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(1.0)

    await ctx.send(f"✅ Broadcast complete. Sent: {success}, failed: {failed}. run={RUN_ID}")


bot.run(TOKEN)
