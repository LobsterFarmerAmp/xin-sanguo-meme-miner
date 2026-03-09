"""Fetch ALL videos from UP主 via exhaustive search strategy.

Uses multiple search patterns to find as many videos as possible.
"""

import asyncio
import json
import re
from datetime import datetime

import httpx
import pytest

from meme_miner.config import Config
from meme_miner.platforms.bilibili import BilibiliPlatform
from meme_miner.models import VideoInfo


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"


@pytest.mark.asyncio
async def test_fetch_all_exhaustive_search():
    """Use exhaustive search to find all videos."""
    config = Config()
    platform = BilibiliPlatform(config)
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: 穷尽搜索 (多关键词组合)")
    print(f"{'='*70}\n")
    
    seen_bvids = set()
    all_videos = []
    
    # Search strategies
    search_strategies = [
        # Strategy 1: UP主名
        ["吃蛋挞的折棒"],
        # Strategy 2: Series name variations
        ["三国杀up锐评新三国"],
        # Strategy 3: Episode ranges (search every 10 episodes)
        [f"新三国{i}" for i in range(1, 260, 5)],
        # Strategy 4: Popular phrases from the series
        [
            "龙可是帝王之征",
            "恭喜主公你爹殡天",
            "袁公路鲜美无比",
            "不可能我二弟天下无敌",
            "这曹操是哪来的变态",
            "孔明在火中安睡",
        ],
        # Strategy 5: Character names + 新三国
        [f"{char} 新三国" for char in ["刘备", "关羽", "张飞", "曹操", "诸葛亮", "赵云", "吕布"]],
    ]
    
    for i, keywords in enumerate(search_strategies, 1):
        print(f"\n策略 {i}: {len(keywords)} 个关键词")
        
        for keyword in keywords:
            try:
                count_before = len(all_videos)
                async for video in platform.search_videos(keyword, limit=50):
                    if video.bvid not in seen_bvids:
                        seen_bvids.add(video.bvid)
                        all_videos.append(video)
                
                new_found = len(all_videos) - count_before
                if new_found > 0:
                    print(f"  '{keyword[:20]}...': +{new_found} (total: {len(all_videos)})")
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                continue
    
    # Filter for target uploader and series
    uploader_videos = [v for v in all_videos if UPLOADER_NAME in v.uploader]
    series_videos = [v for v in uploader_videos if "锐评新三国" in v.title]
    
    print(f"\n{'='*70}")
    print(f"搜索结果汇总")
    print(f"{'='*70}")
    print(f"总视频(去重): {len(all_videos)}")
    print(f"该UP主视频: {len(uploader_videos)}")
    print(f"'锐评新三国'系列: {len(series_videos)}")
    
    # Sort by episode
    def extract_ep(title: str) -> int:
        m = re.search(r'新三国(\d+)', title)
        return int(m.group(1)) if m else 9999
    
    series_videos.sort(key=lambda v: extract_ep(v.title))
    
    if series_videos:
        episodes = [extract_ep(v.title) for v in series_videos]
        max_ep = max(episodes)
        all_eps = set(episodes)
        missing = [i for i in range(1, max_ep + 1) if i not in all_eps]
        
        total_plays = sum(v.play_count for v in series_videos)
        total_dm = sum(v.danmaku_count for v in series_videos)
        
        print(f"\n{'='*70}")
        print(f"系列统计")
        print(f"{'='*70}")
        print(f"期数范围: 第1期 ~ 第{max_ep}期")
        print(f"实际期数: {len(series_videos)} 期")
        print(f"总播放量: {total_plays:,}")
        print(f"总弹幕数: {total_dm:,}")
        print(f"平均播放: {total_plays // len(series_videos):,}")
        
        if missing:
            print(f"\n⚠️ 缺失期数 ({len(missing)} 个):")
            # Group consecutive missing
            ranges = []
            start = missing[0]
            prev = missing[0]
            for n in missing[1:]:
                if n == prev + 1:
                    prev = n
                else:
                    ranges.append(f"{start}-{prev}" if start != prev else str(start))
                    start = prev = n
            ranges.append(f"{start}-{prev}" if start != prev else str(start))
            print(f"   {', '.join(ranges)}")
        else:
            print(f"\n✓ 完整系列！")
        
        # Save
        output = {
            "uploader": UPLOADER_NAME,
            "uid": UPLOADER_UID,
            "series": "三国杀up锐评新三国",
            "fetch_method": "exhaustive_search",
            "total_episodes": len(series_videos),
            "episode_range": f"1-{max_ep}",
            "missing_episodes": missing,
            "missing_count": len(missing),
            "total_plays": total_plays,
            "total_danmaku": total_dm,
            "avg_plays": total_plays // len(series_videos),
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
        
        with open("data/zhebang_series_exhaustive.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved to data/zhebang_series_exhaustive.json")
        
        # Show all episodes
        print(f"\n{'='*70}")
        print(f"完整视频列表 ({len(series_videos)} 期)")
        print(f"{'='*70}")
        for i, v in enumerate(series_videos, 1):
            ep = extract_ep(v.title)
            print(f"[{i:3}] 第{ep:3}期 | {v.title[:45]}... | {v.play_count:,}")
    
    print(f"\n{'='*70}\n")
    
    return {
        "total": len(series_videos),
        "episodes": series_videos,
        "missing": missing if series_videos else [],
    }


if __name__ == "__main__":
    asyncio.run(test_fetch_all_exhaustive_search())
