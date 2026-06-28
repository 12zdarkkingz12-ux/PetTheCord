from io import BytesIO
from logging import getLogger

from discord import File, Interaction, User, app_commands
from discord.ext import commands

from config import Config
from petter import APIError, AvatarNotFound, Petter, UserNotFound

logger = getLogger(__name__)


class PetCog(commands.Cog):
    def __init__(self, petter: Petter, origin: str = Config.ORIGIN) -> None:
        self._petter = petter
        self._origin = origin
        super().__init__()

    # ── /petpet ───────────────────────────────────────────────────────────────

    @app_commands.allowed_installs(users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="petpet", description="Pet a user and send the GIF directly")
    @app_commands.describe(user="The user you want to pet")
    async def petpet(self, interaction: Interaction, user: User) -> None:
        await interaction.response.defer()
        logger.info("petpet: %s requested for %s", interaction.user.id, user.id)
        try:
            gif = await self._petter.make(user)
            await interaction.followup.send(
                file=File(BytesIO(gif), filename=f"{user.id}.gif")
            )
        except UserNotFound:
            await interaction.followup.send("❌ User not found.", ephemeral=True)
        except AvatarNotFound:
            await interaction.followup.send("❌ This user has no avatar.", ephemeral=True)
        except APIError:
            await interaction.followup.send("❌ Discord API error, try again later.", ephemeral=True)

    # ── /petpetlink ───────────────────────────────────────────────────────────

    @app_commands.allowed_installs(users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="petpetlink", description="Get a shareable link to a petpet GIF")
    @app_commands.describe(
        user="The user you want to pet",
        r="Cache-bust suffix (optional — use if avatar looks outdated)",
    )
    async def petpetlink(self, interaction: Interaction, user: User, r: str = "") -> None:
        logger.info("petpetlink: %s requested for %s", interaction.user.id, user.id)
        suffix = f".{r}" if r else ""
        await interaction.response.send_message(
            f"{self._origin}/{user.id}{suffix}.gif"
        )
