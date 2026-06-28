from io import BytesIO
from logging import getLogger

import discord
from discord import Client, User
from petpetgif import petpet

logger = getLogger(__name__)


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class PetterError(Exception):
    pass

class UserNotFound(PetterError):
    pass

class AvatarNotFound(PetterError):
    pass

class APIError(PetterError):
    pass


# ── Core Petter ────────────────────────────────────────────────────────────────

class Petter:
    def __init__(self) -> None:
        self._client: Client | None = None
        self._stats = {"total": 0}

    def setup(self, client: Client) -> None:
        """Called once the Discord client is ready."""
        self._client = client

    @property
    def stats(self) -> dict:
        return self._stats.copy()

    async def _fetch_user(self, uid: int) -> User:
        if not self._client:
            raise APIError("Discord client not ready")
        try:
            return await self._client.fetch_user(uid)
        except discord.NotFound:
            raise UserNotFound(f"User {uid} not found")
        except discord.HTTPException as exc:
            raise APIError(f"Discord API error: {exc}") from exc

    async def _get_avatar_bytes(self, user: User) -> bytes:
        """Returns avatar bytes; falls back to default avatar if none set."""
        avatar = user.avatar or user.default_avatar
        if not avatar:
            raise AvatarNotFound(f"No avatar for {user.id}")
        return await avatar.read()

    @staticmethod
    def _build_gif(avatar_bytes: bytes) -> bytes:
        with BytesIO(avatar_bytes) as src, BytesIO() as dst:
            petpet.make(src, dst)
            dst.seek(0)
            return dst.read()

    async def make(self, target: int | User) -> bytes:
        """Generate a petpet GIF for the given user ID or User object."""
        user = target if isinstance(target, User) else await self._fetch_user(target)
        avatar_bytes = await self._get_avatar_bytes(user)
        gif = self._build_gif(avatar_bytes)
        self._stats["total"] += 1
        logger.debug("Generated petpet for %s (total: %d)", user.id, self._stats["total"])
        return gif
