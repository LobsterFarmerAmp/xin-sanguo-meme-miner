"""Fetch ALL videos from UP主 via Bilibili mobile API.

Uses the mobile app API which has less restrictions.
"""

import asyncio
import json
import re
import time
from datetime import datetime

import httpx
import pytest

from meme_miner.config import Config
from meme_miner.models import VideoInfo


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"


async def fetch_space_mobile(
    uid: int,
    client: httpx.AsyncClient,
    headers: dict,
    page: int = 1,
    page_size: int = 30
) -> list[dict]:
    """Fetch videos using mobile app API."""
    
    # Mobile app API endpoint
    url = "https://app.bilibili.com/x/v2/space/archive/cursor"
    
    params = {
        "vmid": str(uid),
        "ps": str(page_size),
        "pn": str(page),
    }
    
    # Mobile app headers
    mobile_headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
        "Accept": "application/json",
        "Referer": f"https://space.bilibili.com/{uid}",
    }
    
    resp = await client.get(url, params=params, headers=mobile_headers)
    
    try:
        data = resp.json()
    except:
        print(f"Response: {resp.text[:500]}")
        return []
    
    if data.get("code") != 0:
        print(f"API Error: {data.get('message')}")
        return []
    
    # Mobile API returns data in 'item' list
    items = data.get("data", {}).get("item", [])
    return items


async def fetch_space_web_anonymous(
    uid: int,
    client: httpx.AsyncClient,
    page: int = 1,
    page_size: int = 50
) -> list[dict]:
    """Try web API without authentication."""
    
    url = "https://api.bilibili.com/x/space/arc/search"
    
    params = {
        "mid": str(uid),
        "ps": str(page_size),
        "pn": str(page),
        "tid": "0",
        "order": "pubdate",
        "keyword": "",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"https://space.bilibili.com/{uid}/video",
        "Accept": "application/json, text/plain, */*",
    }
    
    resp = await client.get(url, params=params, headers=headers)
    
    try:
        data = resp.json()
    except:
        return []
    
    if data.get("code") != 0:
        return []
    
    vlist = data.get("data", {}).get("list", {}).get("vlist", [])
    return vlist


@pytest.mark.asyncio
async def test_fetch_all_mobile_api():
    """Fetch videos using mobile API."""
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: 移动端 API")
    print(f"{'='*70}\n")
    
    all_videos = []
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Try mobile API
        print("Trying mobile API...")
        page = 1
        while True:
            items = await fetch_space_mobile(UPLOADER_UID, client, {}, page)
            if not items:
                break
            
            for item in items:
                video = VideoInfo(
                    bvid=item.get("bvid", ""),
                    title=item.get("title", ""),
                    uploader=item.get("author", UPLOADER_NAME),
                    play_count=item.get("stat", {}).get("view", 0),
                    danmaku_count=item.get("stat", {}).get("danmaku", 0),
                    url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                )
                all_videos.append(video)
            
            print(f"  Page {page}: {len(items)} videos (total: {len(all_videos)})")
            
            if len(items) < 30:
                break
            
            page += 1
            await asyncio.sleep(0.5)
        
        # If mobile didn't work well, try web API
        if len(all_videos) < 10:
            print("\nTrying web API...")
            page = 1
            while True:
                items = await fetch_space_web_anonymous(UPLOADER_UID, client, page)
                if not items:
                    break
                
                for item in items:
                    video = VideoInfo(
                        bvid=item.get("bvid", ""),
                        title=item.get("title", ""),
                        uploader=item.get("author", UPLOADER_NAME),
                        play_count=item.get("play", 0) or 0,
                        danmaku_count=item.get("video_review", 0) or 0,
                        url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    )
                    all_videos.append(video)
                
                print(f"  Page {page}: {len(items)} videos (total: {len(all_videos)})")
                
                if len(items) < 50:
                    break
                
                page += 1
                await asyncio.sleep(0.8)
    
    print(f"\nTotal videos: {len(all_videos)}")
    
    # Filter for series
    series_videos = [v for v in all_videos if "锐评新三国" in v.title]
    
    # Sort by episode
    def extract_ep(title: str) -> int:
        m = re.search(r'新三国(\d+)', title)
        return int(m.group(1)) if m else 9999
    
    series_videos.sort(key=lambda v: extract_ep(v.title))
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"统计结果")
    print(f"{'='*70}")
    print(f"UP主总视频数: {len(all_videos)}")
    print(f"'锐评新三国'系列: {len(series_videos)} 期")
    
    if series_videos:
        episodes = [extract_ep(v.title) for v in series_videos]
        max_ep = max(episodes)
        all_eps = set(episodes)
        missing = [i for i in range(1, max_ep + 1) if i not in all_eps]
        
        total_plays = sum(v.play_count for v in series_videos)
        total_dm = sum(v.danmaku_count for v in series_videos)
        
        print(f"期数范围: 第1期 ~ 第{max_ep}期")
        print(f"系列总播放: {total_plays:,}")
        print(f"系列总弹幕: {total_dm:,}")
        
        if missing:
            print(f"\n⚠️ 缺失期数 ({len(missing)} 个): {missing[:30]}{'...' if len(missing) > 30 else ''}")
        else:
            print(f"\n✓ 完整系列！")
        
        # Save
        output = {
            "uploader": UPLOADER_NAME,
            "uid": UPLOADER_UID,
            "series": "三国杀up锐评新三国",
            "total_episodes": len(series_videos),
            "episode_range": f"1-{max_ep}",
            "missing_episodes": missing,
            "total_plays": total_plays,
            "total_danmaku": total_dm,
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
        
        with open("data/zhebang_series_mobile.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved to data/zhebang_series_mobile.json")
    
    print(f"\n{'='*70}\n")
    return series_videos


if __name__ == "__main__":
    asyncio.run(test_fetch_all_mobile_api())
