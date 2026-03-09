"""Base platform interface for scrapers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from meme_miner.models import VideoInfo, Danmaku, MemeHit
from meme_miner.config import Config


class BasePlatform(ABC):
    """Abstract base class for platform scrapers."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    @abstractmethod
    async def search_videos(self, keyword: str, limit: int = 20) -> AsyncIterator[VideoInfo]:
        """Search for videos by keyword."""
        pass

    @abstractmethod
    async def get_danmaku(self, video: VideoInfo) -> AsyncIterator[Danmaku]:
        """Fetch danmaku for a video."""
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name."""
        pass
