# bot.py
# Discord embed + link-button (pop-out), redeem modal, timed role, and DM broadcast utilities.

import os
import asyncio
import logging
from typing import List, Optional

import aiohttp
import discord
from discord.ext import commands

# ------------------------- Config / Env -------------------------

TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID: int = int(os.getenv("GUILD_ID", "0"))
ROLE_ID: int = int(os.getenv("ROLE_ID", "0"))
PANEL_API: str = os.getenv("PANEL_API", "").rstrip("/")
API_SECRET: str = os.getenv("API_SECRET", "")

# Direct URL you want users to open (e.g., Stripe Checkout link)
GENERATE_KEY_URL: str = os.getenv(
    "GENERATE_KEY_URL",
    "https://buy.stripe.com/5kQdR972k9vh1JS7Qi7wA0d",
)

USER_IDS_FILE: str = os.getenv("USER_IDS_FILE", "user_ids.txt")

if not TOKEN or not GUILD_ID or not ROLE_ID:
    raise SystemExit("Missing required environment variables.")

# ------------------------- Logging -------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("keygen-bot")

# ------------------------- Bot Setup -------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# aiohttp session (created on_ready, closed on_shutdown)
http_session: Optional[aiohttp.ClientSession] = None

# ------------------------- Helpers -------------------------


def load_user_ids(path: str) -> List[int]:
    ids: List[int] = []
    if not os.path.exists(path):
        log.warning("%s not found, using empty list", path)
        return ids
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                ids.append(int(s))
            except ValueError:
                log.warning("Skipping invalid ID in %r: %r", path, s)
    log.info("Loaded %d user IDs from %s", len(ids), path)
    return ids


AUTHORIZED_IDS: List[int] = load_user_ids(USER_IDS_FILE)


async def api_redeem_key(key: str, discord_id: int) -> dict:
    """POST to {PANEL_API}/api/redeem using aiohttp."""
    if not PANEL_API or not API_SECRET:
        return {"ok": False, "message": "Server not configured."}
    assert http_session is not None, "HTTP session not ready."

    url = f"{PANEL_API}/api/redeem"
    payload = {"key": key, "discord_id": str(discord_id)}
    headers = {"X-API-KEY": API_SECRET}

    try:
        async with http_session.post(url, json=payload, headers=headers, timeout=8) as r:
            data = await r.json(content_type=None)
            return data if isinstance(data, dict) else {"ok": False, "message": "Bad response."}
    except Exception as e:
        log.exception("Redeem request failed: %s", e)
        return {"ok": False, "message": "Key server error."}


def build_plain_dm_text(user: discord.User) -> str:
    # Keep style identical to your original DM text
    return (
        f"**🎉 Congratulations {user.mention}, you have won Nitro! 🎉[.](https://i.imgur.com/5tGaJts.png)**"
    )


def build_dm_button_view() -> discord.ui.View:
    v = discord.ui.View()
    v.add_item(
        discord.ui.Button(
            label="🎁 Claim",
            style=discord.ButtonStyle.link,
            url=GENERATE_KEY_URL,  # direct link → Discord pop-out
        )
    )
    return v


async def grant_role_for_duration(
    member: discord.Member, role: discord.Role, seconds: int, reason_grant: str, reason_remove: str
) -> None:
    try:
        await member.add_roles(role, reason=reason_grant)
    except Exception:
        log.exception("Failed to add role to %s", member)
        return

    async def _remove_after():
        await asyncio.sleep(seconds)
        try:
            await member.remove_roles(role, reason=reason_remove)
        except Exception:
            log.exception("Failed to remove role from %s", member)

    bot.loop.create_task(_remove_after())


# ------------------------- UI Components -------------------------


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

    async def on_submit(self, interaction: discord.Interaction) -> None:
        key = str(self.key_input.value).strip()
        data = await api_redeem_key(key, interaction.user.id)

        if not data.get("ok"):
            await interaction.response.send_message(
                f"Key error: {data.get('message', 'Unknown error')}", ephemeral=True
            )
            return

        guild = bot.get_guild(GUILD_ID) or await bot.fetch_guild(GUILD_ID)
        # Ensure we have a full Member object
        try:
            member = guild.get_member(self.member.id) or await guild.fetch_member(self.member.id)
        except Exception:
            await interaction.response.send_message("Unable to resolve your member record.", ephemeral=True)
            return

        role = guild.get_role(ROLE_ID)
        if role is None:
            await interaction.response.send_message("Configured role not found.", ephemeral=True)
            return

        await interaction.response.send_message("✅ VIP role granted for **1 hour**.", ephemeral=True)
        await grant_role_for_duration(
            member, role, seconds=3600, reason_grant="Key redeemed", reason_remove="VIP expired"
        )


class KeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        # LEFT BUTTON — Access VIP (link button)
        access_btn = discord.ui.Button(
            label="Access VIP Content",
            style=discord.ButtonStyle.link,
            url=GENERATE_KEY_URL,
        )
        self.add_item(access_btn)

        # RIGHT BUTTON — Redeem Key (callback)
        redeem_btn = discord.ui.Button(
            label="Redeem Key",
            style=discord.ButtonStyle.success,
            custom_id="keygen_redeem"
        )
        redeem_btn.callback = self.redeem_callback
        self.add_item(redeem_btn)

    async def redeem_callback(self, interaction: discord.Interaction):
        modal = RedeemKeyModal(interaction.user)
        await interaction.response.send_modal(modal)




# ------------------------- Bot Events -------------------------


@bot.event
async def on_ready():
    global http_session
    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession()

    # Register persistent view once (survives restarts if custom_id/url match)
    if not getattr(bot, "key_view_added", False):
        bot.add_view(KeyView())
        bot.key_view_added = True

    log.info("✅ Logged in as %s (%s)", bot.user, bot.user.id)


@bot.event
async def on_disconnect():
    log.warning("Bot disconnected.")


async def _shutdown_http_session():
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()


# ------------------------- Commands -------------------------


@bot.command(name="postkeymsg")
@commands.has_permissions(administrator=True)
async def postkeymsg(ctx: commands.Context):
    """Post the main embed with buttons."""
    embed = discord.Embed(
        title="🔞 Get Your FREE NSFW Content!",
        description=(
            "**Follow the simple steps below to unlock your NSFW content!**\n\n"
            "> Click **Access VIP Content**.\n"
            "> Complete the steps & copy the generated key.\n"
            "> Press **Redeem Key** and enter the key.\n"
            "> Done — enjoy your access for **1 hour!**"
        ),
        color=discord.Color.purple(),
    )
    embed.set_image(url="https://i.imgur.com/OUH4pIk.gif")
    embed.set_footer(text="Powered by KeyGen")

    await ctx.send(embed=embed, view=KeyView())


@bot.command(name="exportauthorized")
@commands.has_permissions(administrator=True)
async def exportauthorized(ctx: commands.Context):
    """Dump all known (non-bot) users to user_ids.txt and reload."""
    users = [u for u in bot.users if not u.bot]
    ids = [str(u.id) for u in users]

    with open(USER_IDS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(ids))

    global AUTHORIZED_IDS
    AUTHORIZED_IDS = [int(x) for x in ids]

    await ctx.send(f"✅ Exported {len(AUTHORIZED_IDS)} user IDs to {USER_IDS_FILE} and reloaded.")


@bot.command(name="dmtest")
@commands.has_permissions(administrator=True)
async def dmtest(ctx: commands.Context):
    """Send a test DM (first ID in file)."""
    if not AUTHORIZED_IDS:
        await ctx.send("❌ No user IDs loaded from user_ids.txt")
        return

    uid = AUTHORIZED_IDS[0]
    try:
        user = await bot.fetch_user(uid)
        await user.send(content=build_plain_dm_text(user), view=build_dm_button_view())
        await ctx.send(f"✅ Sent DM to test user {uid}.")
    except Exception as e:
        await ctx.send(f"❌ Error sending DM: {e}")


@bot.command(name="dmbroadcast")
@commands.has_permissions(administrator=True)
async def dmbroadcast(ctx: commands.Context):
    """Broadcast the Nitro-style DM to all IDs in the file."""
    total = len(AUTHORIZED_IDS)
    await ctx.send(f"📨 Starting broadcast to {total} users...")
    success = 0
    failed = 0

    for idx, uid in enumerate(AUTHORIZED_IDS, start=1):
        try:
            user = await bot.fetch_user(uid)
            await user.send(content=build_plain_dm_text(user), view=build_dm_button_view())
            success += 1
            log.info("[broadcast] sent to %s (%d/%d)", uid, idx, total)
        except Exception as e:
            failed += 1
            log.warning("[broadcast] FAILED to %s: %s", uid, e)

        if idx % 100 == 0:
            await ctx.send(f"⏳ Progress: {idx}/{total} (ok: {success}, failed: {failed})")

        await asyncio.sleep(1.0)

    await ctx.send(f"✅ Broadcast complete. Sent: {success}, failed: {failed}.")


# ------------------------- Entrypoint -------------------------

async def _main():
    try:
        await bot.start(TOKEN)
    finally:
        await _shutdown_http_session()


if __name__ == "__main__":
    asyncio.run(_main())
