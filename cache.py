import asyncio
from json import dump, load
from logging import getLogger
from os import listdir, makedirs, remove
from os.path import getmtime
from pathlib import Path
from time import time

from discord import User

from config import Config
from petter import AvatarNotFound, Petter

logger = getLogger(__name__)


class CachedPetter(Petter):
    def __init__(
        self,
        path: str     = Config.Cache.PATH,
        lifetime: int = Config.Cache.LIFETIME,
        gc_delay: int = Config.Cache.GC_DELAY,
    ) -> None:
        super().__init__()
        self._path     = Path(path)
        self._lifetime = lifetime
        self._gc_delay = gc_delay
        # FIX: always str keys — JSON loading converts int keys to str anyway
        self._index: dict[str, str] = {}
        self._setup()

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _setup(self) -> None:
        makedirs(self._path, mode=0o755, exist_ok=True)
        index_file = self._path / "index.json"
        if index_file.exists():
            with open(index_file) as f:
                raw = load(f)
            # FIX: normalize all keys to str on load
            self._index = {str(k): str(v) for k, v in raw.items()}
            logger.debug("Loaded cache index (%d entries)", len(self._index))
        else:
            self._flush_index()

    def _flush_index(self) -> None:
        with open(self._path / "index.json", "w") as f:
            dump(self._index, f)

    # ── make ───────────────────────────────────────────────────────────────────

    async def make(self, target: int | User) -> bytes:
        user = target if isinstance(target, User) else await self._fetch_user(
            target if isinstance(target, int) else target.id
        )

        if not user.avatar and not user.default_avatar:
            raise AvatarNotFound(f"No avatar for {user.id}")

        uid_key   = str(user.id)                                    # FIX: str key
        avatar_key = user.avatar.key if user.avatar else "default"
        gif_path   = self._path / f"{user.id}_{avatar_key}.gif"

        cached = self._index.get(uid_key)
        if cached != str(gif_path):
            # Avatar changed → remove old file
            if cached:
                try:
                    remove(cached)
                except OSError:
                    pass
            self._index[uid_key] = str(gif_path)
            self._flush_index()

        if not gif_path.exists():
            logger.debug("Generating new cached gif for %s", user.id)
            gif_path.write_bytes(await super().make(user))
        else:
            gif_path.touch()          # refresh mtime (LRU)
            self._stats["total"] += 1 # count cache hits too

        return gif_path.read_bytes()

    # ── Garbage Collector ──────────────────────────────────────────────────────

    async def gc_loop(self) -> None:
        """Runs forever; evicts GIFs older than `lifetime` seconds."""
        while True:
            await asyncio.sleep(self._gc_delay)
            logger.info("Cache GC started")
            now = time()
            changed = False
            for filename in listdir(self._path):
                fp = self._path / filename
                if fp.is_file() and filename != "index.json":
                    if now - getmtime(fp) > self._lifetime:
                        uid_key = filename.split("_")[0]   # str key
                        self._index.pop(uid_key, None)
                        try:
                            remove(fp)
                            changed = True
                            logger.debug("Evicted %s", filename)
                        except OSError as exc:
                            logger.warning("Could not remove %s: %s", filename, exc)
            if changed:
                self._flush_index()
            logger.info("Cache GC done")
