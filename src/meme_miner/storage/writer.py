"""JSONL writer for storing meme hits."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from meme_miner.models import MemeHit
from meme_miner.config import Config


class JsonlWriter:
    """Write meme hits to JSONL format."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.output_dir = self.config.storage.output_dir
        self.prefix = self.config.storage.filename_prefix
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_output_path(self, timestamp: Optional[datetime] = None) -> Path:
        """Generate output file path based on timestamp."""
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime("%Y%m%d")
        filename = f"{self.prefix}_{date_str}.jsonl"
        return self.output_dir / filename

    def write(self, meme: MemeHit) -> None:
        """Write a single meme hit to the JSONL file."""
        output_path = self._get_output_path(meme.scraped_at)

        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meme.to_dict(), ensure_ascii=False) + "\n")

    def write_batch(self, memes: list[MemeHit]) -> int:
        """Write multiple meme hits to the JSONL file."""
        if not memes:
            return 0

        output_path = self._get_output_path(memes[0].scraped_at)

        with open(output_path, "a", encoding="utf-8") as f:
            for meme in memes:
                f.write(json.dumps(meme.to_dict(), ensure_ascii=False) + "\n")

        return len(memes)

    def read(self, date: Optional[str] = None) -> list[MemeHit]:
        """Read meme hits from JSONL file."""
        if date:
            filename = f"{self.prefix}_{date}.jsonl"
            filepath = self.output_dir / filename
            if not filepath.exists():
                return []
            files = [filepath]
        else:
            files = self.output_dir.glob(f"{self.prefix}_*.jsonl")

        memes = []
        for filepath in sorted(files):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        memes.append(MemeHit(**data))
        return memes
