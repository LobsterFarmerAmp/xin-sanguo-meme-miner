"""Configuration settings for meme_miner."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class BilibiliConfig(BaseModel):
    """Bilibili API configuration."""
    search_url: str = "https://api.bilibili.com/x/web-interface/search/type"
    video_info_url: str = "https://api.bilibili.com/x/player/pagelist"
    danmaku_url: str = "https://comment.bilibili.com/{cid}.xml"
    headers: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
    }
    request_delay: float = 1.5  # seconds between requests


class StorageConfig(BaseModel):
    """Storage configuration."""
    output_dir: Path = Path("data")
    filename_prefix: str = "xin_sanguo"


class HeuristicsConfig(BaseModel):
    """Heuristics configuration for meme detection."""
    min_char_count: int = 6
    max_char_count: int = 30
    min_frequency: int = 2
    role_names: list[str] = [
        "刘备", "关羽", "张飞", "诸葛亮", "曹操", "孙权", "周瑜", "黄忠",
        "赵云", "马超", "张辽", "徐晃", "张郃", "魏延", "姜维", "邓艾",
        "钟会", "吕蒙", "陆逊", "鲁肃", "太史慈", "甘宁", "周泰", "曹仁",
        "曹洪", "夏侯惇", "夏侯渊", "张飞", "关羽", "赵云", "诸葛亮", "庞统",
        "郭嘉", "荀彧", "荀攸", "贾诩", "程昱", "刘表", "袁绍", "袁术",
        "吕布", "貂蝉", "董卓", "王允", "华佗", "左慈", "于吉", "张角"
    ]
    punctuation_markers: list[str] = ["——", "！？", "！？", "，", "。", "...", "…"]


class Config(BaseModel):
    """Main configuration."""
    bilibili: BilibiliConfig = BilibiliConfig()
    storage: StorageConfig = StorageConfig()
    heuristics: HeuristicsConfig = HeuristicsConfig()
    log_level: str = "INFO"

    @classmethod
    def from_file(cls, path: Optional[Path] = None) -> "Config":
        """Load config from file if it exists, otherwise return defaults."""
        if path and path.exists():
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f)
            return cls(**data)
        return cls()
