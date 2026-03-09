"""Test Bilibili search API functionality."""

import asyncio
import pytest
from meme_miner.config import Config
from meme_miner.platforms.bilibili import BilibiliPlatform


@pytest.mark.asyncio
async def test_bilibili_search_new_sanguo_by_time():
    """Test searching '新三国' sorted by time (newest first), return top 20 results."""
    config = Config()
    platform = BilibiliPlatform(config)
    
    keyword = "新三国"
    limit = 20
    order = "pubdate"  # Sort by publish date (newest first)
    
    print(f"\n{'='*60}")
    print(f"Testing Bilibili Search API")
    print(f"Keyword: {keyword}")
    print(f"Order: {order} (pubdate = newest first)")
    print(f"Limit: {limit}")
    print(f"{'='*60}\n")
    
    results = []
    async for video in platform.search_videos(keyword, limit=limit, order=order):
        results.append(video)
        print(f"{len(results):2}. {video.title}")
        print(f"    BV号: {video.bvid}")
        print(f"    链接: {video.url}")
        print(f"    UP主: {video.uploader}")
        print(f"    播放: {video.play_count} | 弹幕: {video.danmaku_count}")
        print()
    
    # Assertions
    assert len(results) > 0, "Should return at least one video"
    assert len(results) <= limit, f"Should not exceed {limit} videos"
    
    # Check all results have required fields
    for video in results:
        assert video.bvid, "Video should have bvid"
        assert video.title, "Video should have title"
        assert video.url, "Video should have url"
        assert "bilibili.com" in video.url, "URL should be bilibili link"
    
    print(f"\n{'='*60}")
    print(f"✓ Test passed! Found {len(results)} videos")
    print(f"{'='*60}")
    
    return results


if __name__ == "__main__":
    # Run directly without pytest for quick testing
    results = asyncio.run(test_bilibili_search_new_sanguo_by_time())
