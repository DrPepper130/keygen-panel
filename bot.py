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
USER_IDS_FILE = "user_ids.txt"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- load user IDs from file ----------
def load_user_ids(path: str):
    ids = []
    if not os.path.exists(path):
        print(f"[warn] {path} not found, using empty list")
        return ids
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                ids.append(int(line))
            except ValueError:
                print(f"[warn] skipping invalid id in {path!r}: {line!r}")
    print(f"[info] loaded {len(ids)} user IDs from {path}")
    return ids


AUTHORIZED_IDS = load_user_ids(USER_IDS_FILE)


# ---------- key redeem stuff ----------
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


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    # add the persistent view ONCE
    if not hasattr(bot, "key_view_added"):
        bot.add_view(KeyView())
        bot.key_view_added = True
        print("Persistent view loaded and ready.")


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


# ---------- DM helpers ----------
def build_plain_dm_text(user: discord.User):
    # DO NOT change message style
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


# ---------- export authorized ----------
@bot.command(name="exportauthorized")
@commands.has_permissions(administrator=True)
async def exportauthorized(ctx: commands.Context):
    """Dump all known (non-bot) users to user_ids.txt and reload."""
    users = [u for u in bot.users if not u.bot]
    ids = [str(u.id) for u in users]

    with open(USER_IDS_FILE, "w") as f:
        f.write("\n".join(ids))

    # reload
    global AUTHORIZED_IDS
    AUTHORIZED_IDS = [int(x) for x in ids]

    await ctx.send(f"✅ Exported {len(AUTHORIZED_IDS)} user IDs to {USER_IDS_FILE} and reloaded.")


# ---------- dmtest ----------
@bot.command(name="dmtest")
@commands.has_permissions(administrator=True)
async def dmtest(ctx: commands.Context):
    """Send DM to the first ID in user_ids.txt (after export)."""
    if not AUTHORIZED_IDS:
        await ctx.send("❌ No user IDs loaded from user_ids.txt")
        return

    uid = AUTHORIZED_IDS[0]
    try:
        user = await bot.fetch_user(uid)
        text = build_plain_dm_text(user)
        view = build_button_view()
        await user.send(content=text, view=view)
        await ctx.send(f"✅ Sent DM to test user {uid}.")
    except Exception as e:
        await ctx.send(f"❌ Error sending DM: {e}")


# ---------- dmbroadcast with progress ----------
@bot.command(name="dmbroadcast")
@commands.has_permissions(administrator=True)
async def dmbroadcast(ctx: commands.Context):
    total = len(AUTHORIZED_IDS)
    await ctx.send(f"📨 Starting broadcast to {total} users...")
    success = 0
    failed = 0

    for idx, uid in enumerate(AUTHORIZED_IDS, start=1):
        try:
            user = await bot.fetch_user(uid)
            text = build_plain_dm_text(user)
            view = build_button_view()
            await user.send(content=text, view=view)
            success += 1
            print(f"[broadcast] sent to {uid} ({idx}/{total})")
        except Exception as e:
            failed += 1
            print(f"[broadcast] FAILED to {uid}: {e}")

        if idx % 100 == 0:
            await ctx.send(f"⏳ Progress: {idx}/{total} done (ok: {success}, failed: {failed})")

        await asyncio.sleep(1.0)

    await ctx.send(f"✅ Broadcast complete. Sent: {success}, failed: {failed}.")


bot.run(TOKEN)
