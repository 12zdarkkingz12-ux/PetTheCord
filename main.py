import asyncio
import logging
from logging import getLogger

from aiohttp.web import AppRunner, TCPSite
from discord import Intents
from discord.ext import commands

from bot import PetCog
from cache import CachedPetter
from config import Config
from petter import Petter
from server import PetServer

logger = getLogger(__name__)


class PetBot(commands.AutoShardedBot):
    def __init__(self, petter: Petter) -> None:
        super().__init__(
            command_prefix="!",
            intents=Intents.default(),
            shard_count=Config.SHARDS,
        )
        self._petter = petter
        self._petter.setup(self)   # give petter a reference to the discord client

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (id: %s)", self.user, self.user.id)

        # Register slash commands
        await self.add_cog(PetCog(self._petter, Config.ORIGIN))
        await self.tree.sync()
        logger.info("Slash commands synced")

        # Start web server
        runner = AppRunner(PetServer(self._petter))
        await runner.setup()
        site = TCPSite(runner, Config.HOST, Config.PORT)
        await site.start()
        logger.info("Web server running on %s:%s", Config.HOST, Config.PORT)

        # Start cache GC if applicable
        if isinstance(self._petter, CachedPetter):
            asyncio.create_task(self._petter.gc_loop())
            logger.info("Cache GC loop started")

    async def on_error(self, event: str, *args, **kwargs) -> None:
        logger.exception("Unhandled error in event: %s", event)


def build_petter() -> Petter:
    if Config.Cache.ENABLED:
        try:
            return CachedPetter(
                path=Config.Cache.PATH,
                lifetime=Config.Cache.LIFETIME,
                gc_delay=Config.Cache.GC_DELAY,
            )
        except OSError:
            logger.warning("Cache setup failed — falling back to no-cache mode")
    return Petter()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    token = Config.get_token()
    if not token:
        raise SystemExit(
            "ERROR: Set PETTHECORD_TOKEN or PETTHECORD_TOKEN_FILE env var"
        )

    petter = build_petter()
    bot    = PetBot(petter)
    bot.run(token, root_logger=True)


if __name__ == "__main__":
    main()
