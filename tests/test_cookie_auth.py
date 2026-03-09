"""Fetch ALL videos from UP主 using login Cookie.

Uses SESSDATA and bili_jct to access authenticated API endpoints.
"""

import asyncio
import json
import re
from datetime import datetime

import httpx
import pytest

from meme_miner.models import VideoInfo


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"

# Your Bilibili Cookies
COOKIES = {
    "SESSDATA": "ad19c9b8%2C1788454343%2C58420%2A31CjCxOitygWZCzOTDUTaW54OjSYy1uVoHOoqk4WGv2v2A5O0zMlIkmal1CkoFX5g1nD4SVjAzNUV3QmlSeDd6SGNGLS1ESzFlYzBFR2ZOM2h4ajRNVXFpLTlrZVE4ZzU4cTc5aUZpdzVCeTV3SnFYUTJ4TWtsQm9FbWtIdEdiQURlbzZveW1pRHdRIIEC",
    "bili_jct": "de55746c13d23c556f0d23d252371dd6",
}


async def fetch_space_with_cookie(uid: int, client: httpx.AsyncClient) -> list[VideoInfo]:
    """Fetch all videos from space using authenticated cookies."""
    
    all_videos = []
    page = 1
    page_size = 50
    
    while True:
        url = "https://api.bilibili.com/x/space/arc/search"
        params = {
            "mid": str(uid),
            "ps": str(page_size),
            "pn": str(page),
            "order": "pubdate",
        }
        
        resp = await client.get(url, params=params)
        
        try:
            data = resp.json()
        except:
            print(f"Parse error: {resp.text[:500]}")
            break
        
        if data.get("code") != 0:
            print(f"API Error: {data.get('message')} (code: {data.get('code')})")
            break
        
        vlist = data.get("data", {}).get("list", {}).get("vlist", [])
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
        
        print(f"Page {page}: {len(vlist)} videos (total: {len(all_videos)})")
        
        if len(vlist) < page_size:
            break
        
        page += 1
        await asyncio.sleep(0.5)
    
    return all_videos


@pytest.mark.asyncio
async def test_fetch_with_cookie():
    """Fetch videos using login cookie."""
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: 登录 Cookie 认证")
    print(f"{'='*70}\n")
    
    # Create client with cookies
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://space.bilibili.com/{UPLOADER_UID}",
    }
    
    cookies = httpx.Cookies()
    for name, value in COOKIES.items():
        cookies.set(name, value, domain=".bilibili.com")
    
    async with httpx.AsyncClient(
        timeout=30.0,
        headers=headers,
        cookies=cookies,
    ) as client:
        all_videos = await fetch_space_with_cookie(UPLOADER_UID, client)
    
    print(f"\n{'='*70}")
    print(f"总视频数: {len(all_videos)}")
    print(f"{'='*70}")
    
    # Filter for series
    series_videos = [v for v in all_videos if "锐评新三国" in v.title]
    
    # Sort by episode
    def extract_ep(title: str) -> int:
        m = re.search(r'新三国(\d+)', title)
        return int(m.group(1)) if m else 9999
    
    series_videos.sort(key=lambda v: extract_ep(v.title))
    
    print(f"\n'锐评新三国'系列: {len(series_videos)} 期")
    
    if series_videos:
        episodes = [extract_ep(v.title) for v in series_videos]
        max_ep = max(episodes)
        all_eps = set(episodes)
        missing = [i for i in range(1, max_ep + 1) if i not in all_eps]
        
        total_plays = sum(v.play_count for v in series_videos)
        total_dm = sum(v.danmaku_count for v in series_videos)
        
        print(f"期数范围: 第1期 ~ 第{max_ep}期")
        print(f"总播放量: {total_plays:,}")
        print(f"总弹幕数: {total_dm:,}")
        print(f"平均播放: {total_plays // len(series_videos):,}")
        
        if missing:
            print(f"\n⚠️ 缺失期数 ({len(missing)} 个): {missing[:20]}{'...' if len(missing) > 20 else ''}")
        else:
            print(f"\n✓ 完整系列！")
        
        # Save
        output = {
            "uploader": UPLOADER_NAME,
            "uid": UPLOADER_UID,
            "series": "三国杀up锐评新三国",
            "fetch_method": "authenticated_cookie",
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
        
        with open("data/zhebang_series_cookie.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved to data/zhebang_series_cookie.json")
        
        # Print list
        print(f"\n{'='*70}")
        print(f"完整视频列表 ({len(series_videos)} 期)")
        print(f"{'='*70}")
        for i, v in enumerate(series_videos, 1):
            ep = extract_ep(v.title)
            print(f"[{i:3}] 第{ep:3}期 | {v.title[:45]}... | {v.play_count:,}")
    
    print(f"\n{'='*70}\n")
    return series_videos


if __name__ == "__main__":
    asyncio.run(test_fetch_with_cookie())
