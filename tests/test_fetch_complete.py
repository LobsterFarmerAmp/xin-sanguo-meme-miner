"""Fetch ALL videos from UP主 吃蛋挞的折棒 via comprehensive search.

Uses multiple search strategies to find all videos from the uploader.
"""

import asyncio
import pytest
from meme_miner.config import Config
from meme_miner.platforms.bilibili import BilibiliPlatform
from meme_miner.models import VideoInfo


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"


@pytest.mark.asyncio
async def test_fetch_all_by_comprehensive_search():
    """Fetch all '锐评新三国' videos using comprehensive search."""
    config = Config()
    platform = BilibiliPlatform(config)
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: 综合搜索 (关键词 + UP主过滤)")
    print(f"{'='*70}\n")
    
    all_matching = []
    seen_bvids = set()
    
    # Strategy 1: Search with different keywords
    search_terms = [
        "吃蛋挞的折棒",
        "三国杀up锐评新三国",
        "锐评新三国",
        "折棒 新三国",
    ]
    
    for term in search_terms:
        print(f"Searching: '{term}'...")
        count = 0
        async for video in platform.search_videos(term, limit=100):
            if UPLOADER_NAME in video.uploader and video.bvid not in seen_bvids:
                seen_bvids.add(video.bvid)
                all_matching.append(video)
                count += 1
        print(f"  Found {count} new videos (total: {len(all_matching)})")
        await asyncio.sleep(1.5)
    
    # Strategy 2: Search with episode numbers to find gaps
    print("\nSearching by episode numbers...")
    for ep in range(1, 300, 10):  # Search every 10 episodes
        term = f"新三国{ep}"
        async for video in platform.search_videos(term, limit=20):
            if UPLOADER_NAME in video.uploader and video.bvid not in seen_bvids:
                seen_bvids.add(video.bvid)
                all_matching.append(video)
        await asyncio.sleep(0.5)
    
    print(f"  After episode search: {len(all_matching)} videos")
    
    # Filter for series videos
    series_videos = [v for v in all_matching if "锐评新三国" in v.title]
    
    # Sort by episode
    def extract_ep(title: str) -> int:
        import re
        m = re.search(r'新三国(\d+)', title)
        return int(m.group(1)) if m else 9999
    
    series_videos.sort(key=lambda v: extract_ep(v.title))
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"统计结果")
    print(f"{'='*70}")
    print(f"UP主: {UPLOADER_NAME}")
    print(f"'锐评新三国'系列视频数: {len(series_videos)}")
    
    if series_videos:
        total_plays = sum(v.play_count for v in series_videos)
        total_dm = sum(v.danmaku_count for v in series_videos)
        episodes = [extract_ep(v.title) for v in series_videos]
        max_ep = max(episodes)
        all_eps = set(episodes)
        missing = [i for i in range(1, max_ep + 1) if i not in all_eps]
        
        print(f"期数范围: 第1期 ~ 第{max_ep}期")
        print(f"实际期数: {len(series_videos)} 期")
        print(f"系列总播放: {total_plays:,}")
        print(f"系列总弹幕: {total_dm:,}")
        print(f"平均播放: {total_plays // len(series_videos):,}")
        
        if missing:
            print(f"\n⚠️ 缺失期数 ({len(missing)} 个): {missing[:20]}{'...' if len(missing) > 20 else ''}")
        
        print(f"\n{'='*70}")
        print(f"完整列表")
        print(f"{'='*70}")
        for i, v in enumerate(series_videos, 1):
            ep = extract_ep(v.title)
            print(f"[{i:3}] 第{ep:3}期 | {v.title[:50]}... | {v.play_count:,} 播放")
    
    print(f"\n{'='*70}\n")
    
    # Also save full data
    import json
    from datetime import datetime
    output = {
        "uploader": UPLOADER_NAME,
        "uid": UPLOADER_UID,
        "series": "三国杀up锐评新三国",
        "count": len(series_videos),
        "total_plays": sum(v.play_count for v in series_videos),
        "total_danmaku": sum(v.danmaku_count for v in series_videos),
        "videos": [
            {
                "title": v.title,
                "bvid": v.bvid,
                "url": v.url,
                "play": v.play_count,
                "danmaku": v.danmaku_count,
                "episode": extract_ep(v.title),
            }
            for v in series_videos
        ],
        "fetched_at": datetime.now().isoformat(),
    }
    with open("data/zhebang_series_full.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✓ Data saved to data/zhebang_series_full.json")
    
    return series_videos


if __name__ == "__main__":
    asyncio.run(test_fetch_all_by_comprehensive_search())
