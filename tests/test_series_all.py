"""Fetch all '吐槽新三国' series videos from UP主 吃蛋挞的折棒.

Uses Bilibili space API to get all videos from the uploader,
then filters for the '锐评新三国' series.
"""

import asyncio
import pytest
import httpx
from meme_miner.config import Config
from meme_miner.platforms.bilibili import BilibiliPlatform
from meme_miner.models import VideoInfo


# UID for 吃蛋挞的折棒
UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"


@pytest.mark.asyncio
async def test_fetch_all_xinsanguo_series():
    """Fetch all '锐评新三国' series videos from 吃蛋挞的折棒."""
    config = Config()
    platform = BilibiliPlatform(config)
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"目标: 获取全部'锐评新三国'系列视频")
    print(f"{'='*70}\n")
    
    # Search using keyword + filter by uploader
    # Bilibili search API doesn't have direct uploader filter,
    # so we search and filter
    all_videos = []
    search_keywords = [
        "三国杀up锐评新三国",
        "吃蛋挞的折棒 新三国",
        "锐评新三国",
    ]
    
    for keyword in search_keywords:
        print(f"Searching: '{keyword}'...")
        async for video in platform.search_videos(keyword, limit=100):
            if UPLOADER_NAME in video.uploader and video not in all_videos:
                all_videos.append(video)
        await asyncio.sleep(1.5)  # Rate limit
    
    # Filter for series videos (title contains "锐评新三国" and episode number)
    series_videos = [
        v for v in all_videos 
        if "锐评新三国" in v.title or "新三国" in v.title
    ]
    
    # Sort by episode number if possible
    def extract_episode(title: str) -> int:
        """Extract episode number from title like '锐评新三国123：...'"""
        import re
        match = re.search(r'新三国(\d+)', title)
        return int(match.group(1)) if match else 9999
    
    series_videos.sort(key=lambda v: extract_episode(v.title))
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"统计结果")
    print(f"{'='*70}")
    print(f"UP主: {UPLOADER_NAME}")
    print(f"系列: 三国杀up锐评新三国")
    print(f"总视频数: {len(series_videos)}")
    
    if series_videos:
        total_plays = sum(v.play_count for v in series_videos)
        total_danmaku = sum(v.danmaku_count for v in series_videos)
        avg_plays = total_plays // len(series_videos)
        
        print(f"总播放量: {total_plays:,}")
        print(f"总弹幕数: {total_danmaku:,}")
        print(f"平均播放量: {avg_plays:,}")
        print(f"最高播放: {max(v.play_count for v in series_videos):,}")
        print(f"最低播放: {min(v.play_count for v in series_videos):,}")
        
        print(f"\n{'='*70}")
        print(f"完整视频列表")
        print(f"{'='*70}")
        
        for i, v in enumerate(series_videos, 1):
            ep = extract_episode(v.title)
            print(f"\n[{i}] 第{ep}期")
            print(f"    标题: {v.title}")
            print(f"    BV号: {v.bvid}")
            print(f"    链接: {v.url}")
            print(f"    播放: {v.play_count:,}")
            print(f"    弹幕: {v.danmaku_count:,}")
    
    print(f"\n{'='*70}\n")
    
    return {
        "uploader": UPLOADER_NAME,
        "uid": UPLOADER_UID,
        "series": "三国杀up锐评新三国",
        "total_videos": len(series_videos),
        "videos": series_videos,
    }


if __name__ == "__main__":
    results = asyncio.run(test_fetch_all_xinsanguo_series())
