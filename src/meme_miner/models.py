"""Data models for meme_miner."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    """Information about a video."""
    bvid: str
    title: str
    uploader: str
    play_count: int = 0
    danmaku_count: int = 0
    url: str
    cid: Optional[int] = None


class Danmaku(BaseModel):
    """A single danmaku (bullet comment)."""
    text: str
    timestamp: float = 0  # seconds into video
    likes: int = 0
    publish_time: Optional[datetime] = None


class MemeHit(BaseModel):
    """A detected meme or quote."""
    quote: str
    context: str = ""  # surrounding text if available
    source_platform: str
    source_url: str
    evidence: list[dict] = Field(default_factory=list)  # list of danmaku dicts
    score: float = 0.0
    scraped_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "quote": self.quote,
            "context": self.context,
            "source_platform": self.source_platform,
            "source_url": self.source_url,
            "evidence": self.evidence,
            "score": self.score,
            "scraped_at": self.scraped_at.isoformat(),
        }
