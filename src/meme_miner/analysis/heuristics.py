"""Heuristics for meme and quote detection."""

import re
from collections import Counter
from typing import Iterator

from meme_miner.models import Danmaku, MemeHit
from meme_miner.config import Config


class HeuristicsDetector:
    """Detect memes and quotes from danmaku text using heuristics."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.min_chars = self.config.heuristics.min_char_count
        self.max_chars = self.config.heuristics.max_char_count
        self.min_freq = self.config.heuristics.min_frequency
        self.role_names = set(self.config.heuristics.role_names)
        self.punctuation_markers = self.config.heuristics.punctuation_markers

    def is_valid_quote(self, text: str) -> bool:
        """Check if text matches meme/quote criteria."""
        # Remove whitespace
        cleaned = text.strip()

        # Check length
        char_count = len(cleaned)
        if char_count < self.min_chars or char_count > self.max_chars:
            return False

        # Must contain Chinese characters
        if not re.search(r"[\u4e00-\u9fff]", cleaned):
            return False

        # Check for punctuation markers (should contain at least one)
        has_marker = any(marker in cleaned for marker in self.punctuation_markers)
        if not has_marker:
            return False

        return True

    def contains_role_name(self, text: str) -> bool:
        """Check if text contains a Three Kingdoms role name."""
        return any(role in text for role in self.role_names)

    def extract_quotes(self, danmaku_iterator: Iterator[Danmaku]) -> Counter[str]:
        """Extract candidate quotes from danmaku stream."""
        quote_counts: Counter[str] = Counter()

        for danmaku in danmaku_iterator:
            text = danmaku.text.strip()
            if self.is_valid_quote(text):
                quote_counts[text] += 1

        return quote_counts

    def calculate_score(self, quote: str, frequency: int, has_role: bool = False) -> float:
        """Calculate meme score based on frequency and other factors."""
        # Base score from frequency
        score = frequency * 1.0

        # Bonus for role names (indicates character-specific quotes)
        if has_role:
            score *= 1.5

        # Bonus for longer quotes (more likely to be actual quotes)
        if len(quote) >= 10:
            score *= 1.2

        # Bonus for multiple punctuation markers
        marker_count = sum(1 for m in self.punctuation_markers if m in quote)
        if marker_count > 1:
            score *= 1.1

        return score

    def detect_memes(
        self,
        danmaku_iterator: Iterator[Danmaku],
        source_platform: str,
        source_url: str,
    ) -> Iterator[MemeHit]:
        """Detect memes from danmaku stream and yield MemeHit objects."""
        # Extract and count quotes
        quote_counts = self.extract_quotes(danmaku_iterator)

        # Filter by minimum frequency
        filtered_quotes = {
            quote: count
            for quote, count in quote_counts.items()
            if count >= self.min_freq
        }

        # Calculate scores and create MemeHits
        for quote, frequency in filtered_quotes.items():
            has_role = self.contains_role_name(quote)
            score = self.calculate_score(quote, frequency, has_role)

            yield MemeHit(
                quote=quote,
                source_platform=source_platform,
                source_url=source_url,
                evidence=[{"text": quote, "frequency": frequency}],
                score=score,
            )

    def rank_memes(self, memes: list[MemeHit]) -> list[MemeHit]:
        """Rank memes by score (descending)."""
        return sorted(memes, key=lambda m: m.score, reverse=True)
