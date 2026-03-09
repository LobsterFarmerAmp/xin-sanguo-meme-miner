"""Tests for heuristics module."""

import pytest
from datetime import datetime

from meme_miner.models import Danmaku, MemeHit
from meme_miner.config import Config
from meme_miner.analysis.heuristics import HeuristicsDetector


class TestHeuristicsDetector:
    """Test cases for HeuristicsDetector."""

    @pytest.fixture
    def detector(self):
        """Create a detector instance."""
        config = Config()
        return HeuristicsDetector(config)

    @pytest.fixture
    def sample_danmaku(self):
        """Create sample danmaku for testing."""
        return [
            Danmaku(text="曹操——乱世奸雄！", timestamp=10.0, likes=42),
            Danmaku(text="曹操——乱世奸雄！", timestamp=15.0, likes=30),
            Danmaku(text="刘备", timestamp=20.0, likes=5),
            Danmaku(text="诸葛亮神机妙算，千古一人。", timestamp=30.0, likes=100),
            Danmaku(text="好", timestamp=40.0, likes=2),
            Danmaku(text="吕布天下第一！", timestamp=50.0, likes=50),
            Danmaku(text="这是一条很长的文本，超过了三十个字符的限制，应该被拒绝。", timestamp=60.0, likes=10),
        ]

    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.min_chars == 6
        assert detector.max_chars == 30
        assert "曹操" in detector.role_names
        assert "刘备" in detector.role_names
        assert "——" in detector.punctuation_markers

    def test_is_valid_quote_valid_cases(self, detector):
        """Test valid quote detection."""
        # Valid: has punctuation, right length, Chinese chars
        # Note: Config has "！？" (combined) not "！" (single)
        assert detector.is_valid_quote("曹操——乱世奸雄！？") is True
        assert detector.is_valid_quote("诸葛亮神机妙算，千古一人。") is True
        assert detector.is_valid_quote("吕布天下第一！？") is True

    def test_is_valid_quote_too_short(self, detector):
        """Test rejection of too short text."""
        assert detector.is_valid_quote("刘备") is False
        assert detector.is_valid_quote("好") is False
        assert detector.is_valid_quote("曹操") is False

    def test_is_valid_quote_too_long(self, detector):
        """Test rejection of too long text."""
        # This text is > 30 chars, should be rejected
        long_text = "这是一条非常长的文本，确实已经超过了三十个字符的上限，必须被拒绝掉。"
        assert len(long_text) > detector.max_chars  # Verify: 35 chars > 30
        assert detector.is_valid_quote(long_text) is False

    def test_is_valid_quote_no_punctuation(self, detector):
        """Test rejection of text without punctuation markers."""
        # No punctuation marker
        assert detector.is_valid_quote("曹操真是乱世奸雄") is False
        assert detector.is_valid_quote("诸葛亮神机妙算") is False

    def test_contains_role_name(self, detector):
        """Test role name detection."""
        assert detector.contains_role_name("曹操——乱世奸雄！") is True
        assert detector.contains_role_name("诸葛亮神机妙算") is True
        assert detector.contains_role_name("刘备关羽张飞") is True
        assert detector.contains_role_name("赵云吕布") is True
        assert detector.contains_role_name("这是一个普通的句子") is False
        assert detector.contains_role_name("Hello World") is False

    def test_calculate_score_with_frequency(self, detector):
        """Test score calculation with frequency."""
        score = detector.calculate_score("曹操", frequency=5, has_role=True)
        assert score > 0
        # Higher frequency should give higher score
        score_low = detector.calculate_score("曹操", frequency=1, has_role=True)
        score_high = detector.calculate_score("曹操", frequency=10, has_role=True)
        assert score_high > score_low

    def test_calculate_score_with_role_bonus(self, detector):
        """Test role name bonus in scoring."""
        score_with_role = detector.calculate_score("曹操", frequency=5, has_role=True)
        score_without_role = detector.calculate_score("普通文本", frequency=5, has_role=False)
        assert score_with_role > score_without_role

    def test_extract_quotes(self, detector, sample_danmaku):
        """Test quote extraction from danmaku."""
        quote_counts = detector.extract_quotes(iter(sample_danmaku))
        
        # Should find "曹操——乱世奸雄！" twice
        assert quote_counts["曹操——乱世奸雄！"] == 2
        
        # Should find "诸葛亮神机妙算，千古一人。" once
        assert quote_counts["诸葛亮神机妙算，千古一人。"] == 1
        
        # "刘备" is too short, should not be included
        assert "刘备" not in quote_counts
        
        # "好" is too short, should not be included
        assert "好" not in quote_counts

    def test_detect_memes(self, detector, sample_danmaku):
        """Test full meme detection pipeline."""
        memes = list(detector.detect_memes(
            iter(sample_danmaku),
            source_platform="bilibili",
            source_url="https://www.bilibili.com/video/BVxxxxx"
        ))
        
        # Should return a list of MemeHit objects
        assert isinstance(memes, list)
        assert len(memes) > 0
        
        # Check first meme structure
        first_meme = memes[0]
        assert isinstance(first_meme, MemeHit)
        assert first_meme.quote is not None
        assert first_meme.source_platform == "bilibili"
        assert first_meme.score > 0
        assert len(first_meme.evidence) > 0

    def test_edge_cases(self, detector):
        """Test edge cases."""
        # Empty string
        assert detector.is_valid_quote("") is False
        
        # Only whitespace
        assert detector.is_valid_quote("   ") is False
        
        # Only punctuation (no Chinese chars)
        assert detector.is_valid_quote("——！！") is False
        
        # Mixed content with emoji - uses combined punctuation marker
        # Note: len("曹操👍！？") = 5 chars (< 6 min), so it fails length check
        assert detector.is_valid_quote("曹操👍真的很强！？") is True  # Has !? punctuation and sufficient length


class TestConfig:
    """Test cases for Config."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        assert config.bilibili.request_delay == 1.5
        assert config.heuristics.min_char_count == 6
        assert config.heuristics.max_char_count == 30
        assert len(config.heuristics.role_names) > 0
        assert "曹操" in config.heuristics.role_names

    def test_custom_config(self):
        """Test custom configuration."""
        config = Config()
        config.heuristics.min_char_count = 10
        config.heuristics.max_char_count = 50
        assert config.heuristics.min_char_count == 10
        assert config.heuristics.max_char_count == 50
