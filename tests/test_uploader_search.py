"""Test searching videos by specific UP主 (uploader)."""

import asyncio
import pytest
from meme_miner.config import Config
from meme_miner.platforms.bilibili import BilibiliPlatform


@pytest.mark.asyncio
async def test_search_by_uploader():
    """Search for '新三国' videos from specific uploader: 吃蛋挞的折棒."""
    config = Config()
    platform = BilibiliPlatform(config)
    
    keyword = "新三国"
    target_uploader = "吃蛋挞的折棒"
    
    print(f"\n{'='*70}")
    print(f"搜索 UP主: {target_uploader}")
    print(f"关键词: {keyword}")
    print(f"{'='*70}\n")
    
    # Search in batches to find all videos
    all_matching = []
    total_checked = 0
    
    # Multiple search passes with different offsets via page iteration
    async for video in platform.search_videos(keyword, limit=200):
        total_checked += 1
        if target_uploader in video.uploader:
            all_matching.append(video)
            print(f"[{len(all_matching)}] {video.title}")
            print(f"    BV: {video.bvid}")
            print(f"    播放: {video.play_count:,} | 弹幕: {video.danmaku_count:,}")
            print()
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"统计结果")
    print(f"{'='*70}")
    print(f"UP主: {target_uploader}")
    print(f"总检查视频数: {total_checked}")
    print(f"匹配视频数: {len(all_matching)}")
    
    if all_matching:
        total_plays = sum(v.play_count for v in all_matching)
        total_danmaku = sum(v.danmaku_count for v in all_matching)
        avg_plays = total_plays // len(all_matching) if all_matching else 0
        
        print(f"总播放量: {total_plays:,}")
        print(f"总弹幕数: {total_danmaku:,}")
        print(f"平均播放量: {avg_plays:,}")
        
        # Sort by play count
        sorted_by_plays = sorted(all_matching, key=lambda v: v.play_count, reverse=True)
        print(f"\n视频列表 (按播放量排序):")
        for i, v in enumerate(sorted_by_plays, 1):
            print(f"\n  [{i}] {v.title}")
            print(f"      BV: {v.bvid}")
            print(f"      播放: {v.play_count:,} | 弹幕: {v.danmaku_count:,}")
    
    print(f"\n{'='*70}\n")
    
    return {
        "uploader": target_uploader,
        "keyword": keyword,
        "total_checked": total_checked,
        "matching_count": len(all_matching),
        "videos": all_matching,
    }


if __name__ == "__main__":
    results = asyncio.run(test_search_by_uploader())
