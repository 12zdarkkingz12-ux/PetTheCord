from os import getenv
from pathlib import Path


class Config:
    HOST: str       = getenv("HOST", "0.0.0.0")
    PORT: int       = int(getenv("PORT", "8000"))
    ORIGIN: str     = getenv("ORIGIN", "http://localhost:8000")
    SHARDS: int     = int(getenv("SHARDS", "1"))

    class Cache:
        ENABLED:  bool = getenv("CACHE_ENABLED", "true").lower() != "false"
        PATH:     str  = getenv("CACHE_PATH", "/tmp/petbot_cache")
        LIFETIME: int  = int(getenv("CACHE_LIFETIME", "86400"))   # 24h
        GC_DELAY: int  = int(getenv("CACHE_GC_DELAY", "14400"))   # 4h

    class RateLimit:
        ENABLED:     bool = getenv("RATE_LIMIT", "true").lower() != "false"
        MAX_REQUESTS: int = int(getenv("RATE_LIMIT_MAX", "15"))
        WINDOW:       int = int(getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

    @staticmethod
    def get_token() -> str:
        if token := getenv("PETTHECORD_TOKEN"):
            return token
        if path := getenv("PETTHECORD_TOKEN_FILE"):
            return Path(path).read_text().strip()
        return ""
