"""Fetch ALL videos from UP主 吃蛋挞的折棒 via legacy space API (no WBI required).

Uses the older x/space/arc/search endpoint which doesn't require WBI signature.
"""

import asyncio
import json
import httpx
import pytest
from datetime import datetime

from meme_miner.config import Config
from meme_miner.models import VideoInfo


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"


async def fetch_space_videos_legacy(
    uid: int,
    client: httpx.AsyncClient,
    headers: dict,
    page: int = 1,
    page_size: int = 50
) -> list[dict]:
    """Fetch videos using legacy space API (no WBI required)."""
    
    # Try multiple endpoints
    urls_to_try = [
        # New WBI endpoint (may work without signature for some IPs)
        "https://api.bilibili.com/x/space/wbi/arc/search",
        # Legacy endpoint
        "https://api.bilibili.com/x/space/arc/search",
        # Alternative endpoint
        "https://api.bilibili.com/x/space/acc/search",
    ]
    
    params = {
        "mid": str(uid),
        "ps": str(page_size),
        "pn": str(page),
        "order": "pubdate",
        "jsonp": "jsonp",
    }
    
    last_error = None
    for url in urls_to_try:
        try:
            resp = await client.get(url, params=params, headers=headers)
            data = resp.json()
            
            if data.get("code") == 0:
                vlist = data.get("data", {}).get("list", {}).get("vlist", [])
                return vlist
            
            last_error = data.get("message", "Unknown error")
            
        except Exception as e:
            last_error = str(e)
            continue
    
    raise Exception(f"All endpoints failed. Last error: {last_error}")


@pytest.mark.asyncio
async def test_fetch_all_legacy():
    """Fetch ALL videos using legacy API."""
    config = Config()
    headers = config.bilibili.headers.copy()
    headers["Referer"] = f"https://space.bilibili.com/{UPLOADER_UID}"
    # Add some browser-like headers
    headers["Origin"] = "https://space.bilibili.com"
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: 多端点尝试 (兼容模式)")
    print(f"{'='*70}\n")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        all_videos = []
        page = 1
        
        while True:
            try:
                print(f"Fetching page {page}...")
                vlist = await fetch_space_videos_legacy(
                    UPLOADER_UID, client, headers, page
                )
                
                if not vlist:
                    break
                
                for item in vlist:
                    video = VideoInfo(
                        bvid=item.get("bvid", ""),
                        title=item.get("title", ""),
                        uploader=item.get("author", ""),
                        play_count=item.get("play", 0) or 0,
                        danmaku_count=item.get("video_review", 0) or 0,
                        url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    )
                    all_videos.append(video)
                
                print(f"  Got {len(vlist)} videos (total: {len(all_videos)})")
                
                if len(vlist) < 50:
                    break
                
                page += 1
                await asyncio.sleep(0.8)
                
            except Exception as e:
                print(f"  Error: {e}")
                break
    
    # Filter for series
    series_videos = [v for v in all_videos if "锐评新三国" in v.title]
    
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
            print(f"\n⚠️ 缺失期数 ({len(missing)} 个): {missing}")
        else:
            print(f"\n✓ 完整系列！无缺失期数")
        
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
        
        with open("data/zhebang_series_final.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved to data/zhebang_series_final.json")
    
    print(f"\n{'='*70}\n")
    return series_videos


if __name__ == "__main__":
    asyncio.run(test_fetch_all_legacy())
