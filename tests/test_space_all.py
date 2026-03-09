"""Fetch ALL videos from UP主 吃蛋挞的折棒 via space API.

Uses Bilibili space/video API to get complete video list from uploader.
"""

import asyncio
import pytest
import httpx
from meme_miner.config import Config
from meme_miner.models import VideoInfo


# UID for 吃蛋挞的折棒
UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"


async def fetch_uploader_all_videos(uid: int, config: Config = None) -> list[VideoInfo]:
    """Fetch all videos from a uploader's space using Bilibili API.
    
    API: https://api.bilibili.com/x/space/wbi/arc/search
    """
    config = config or Config()
    headers = config.bilibili.headers
    
    all_videos = []
    page = 1
    page_size = 50  # Max per page
    
    while True:
        url = "https://api.bilibili.com/x/space/wbi/arc/search"
        params = {
            "mid": uid,
            "pn": page,
            "ps": page_size,
            "order": "pubdate",  # Sort by publish date
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") != 0:
                    print(f"API Error: {data.get('message')}")
                    break
                
                result = data.get("data", {}).get("list", {}).get("vlist", [])
                if not result:
                    break
                
                for item in result:
                    video = VideoInfo(
                        bvid=item.get("bvid", ""),
                        title=item.get("title", ""),
                        uploader=item.get("author", ""),
                        play_count=item.get("play", 0) or 0,
                        danmaku_count=item.get("video_review", 0) or 0,  # video_review is danmaku count
                        url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    )
                    all_videos.append(video)
                
                print(f"Page {page}: Fetched {len(result)} videos, total: {len(all_videos)}")
                
                # Check if we've reached the end
                if len(result) < page_size:
                    break
                
                page += 1
                await asyncio.sleep(1.0)  # Rate limit
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
    
    return all_videos


@pytest.mark.asyncio
async def test_fetch_uploader_space_all():
    """Fetch ALL videos from 吃蛋挞的折棒 space, filter for 新三国 series."""
    config = Config()
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: 用户空间 API (获取全部视频)")
    print(f"{'='*70}\n")
    
    # Fetch all videos from space
    all_videos = await fetch_uploader_all_videos(UPLOADER_UID, config)
    
    print(f"\nTotal videos from space: {len(all_videos)}")
    
    # Filter for 新三国 series
    series_videos = [
        v for v in all_videos 
        if "锐评新三国" in v.title
    ]
    
    # Sort by episode number
    def extract_episode(title: str) -> int:
        import re
        match = re.search(r'新三国(\d+)', title)
        return int(match.group(1)) if match else 9999
    
    series_videos.sort(key=lambda v: extract_episode(v.title))
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"统计结果")
    print(f"{'='*70}")
    print(f"UP主: {UPLOADER_NAME}")
    print(f"UP主总视频数: {len(all_videos)}")
    print(f"'锐评新三国'系列视频数: {len(series_videos)}")
    
    if series_videos:
        total_plays = sum(v.play_count for v in series_videos)
        total_danmaku = sum(v.danmaku_count for v in series_videos)
        avg_plays = total_plays // len(series_videos)
        
        print(f"\n系列总播放量: {total_plays:,}")
        print(f"系列总弹幕数: {total_danmaku:,}")
        print(f"系列平均播放量: {avg_plays:,}")
        print(f"单期最高播放: {max(v.play_count for v in series_videos):,}")
        print(f"单期最低播放: {min(v.play_count for v in series_videos):,}")
        
        # Find missing episodes
        episodes = [extract_episode(v.title) for v in series_videos]
        all_episodes = set(episodes)
        max_ep = max(episodes) if episodes else 0
        missing = [i for i in range(1, max_ep + 1) if i not in all_episodes]
        
        print(f"\n期数范围: 第1期 ~ 第{max_ep}期")
        print(f"实际期数: {len(series_videos)} 期")
        if missing:
            print(f"缺失期数: {missing}")
        
        print(f"\n{'='*70}")
        print(f"完整视频列表")
        print(f"{'='*70}")
        
        for i, v in enumerate(series_videos, 1):
            ep = extract_episode(v.title)
            print(f"\n[{i:3}] 第{ep:3}期 | {v.title}")
            print(f"      BV: {v.bvid} | 播放: {v.play_count:,} | 弹幕: {v.danmaku_count:,}")
    
    print(f"\n{'='*70}\n")
    
    return {
        "uploader": UPLOADER_NAME,
        "uid": UPLOADER_UID,
        "total_videos": len(all_videos),
        "series_count": len(series_videos),
        "videos": series_videos,
    }


if __name__ == "__main__":
    results = asyncio.run(test_fetch_uploader_space_all())
