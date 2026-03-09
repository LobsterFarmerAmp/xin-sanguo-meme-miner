"""Fetch ALL videos from UP主 吃蛋挞的折棒 via WBI-signed space API.

This uses Bilibili's space/video API with WBI signature to get complete video list.
"""

import asyncio
import json
import time
import httpx
import pytest
from datetime import datetime

from meme_miner.config import Config
from meme_miner.models import VideoInfo
from meme_miner.utils.wbi import get_mixin_key, md5_hash


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"


async def fetch_wbi_keys(client: httpx.AsyncClient, headers: dict) -> tuple[str, str]:
    """Fetch fresh WBI keys from Bilibili nav API."""
    url = "https://api.bilibili.com/x/web-interface/nav"
    
    resp = await client.get(url, headers=headers)
    data = resp.json()
    
    if data.get("code") != 0:
        raise Exception(f"Failed to fetch WBI keys: {data.get('message')}")
    
    # Extract keys from wbi_img URL
    # Format: https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png
    wbi_img = data["data"]["wbi_img"]
    img_url = wbi_img["img_url"]
    sub_url = wbi_img["sub_url"]
    
    # Extract key from URL (filename without extension)
    img_key = img_url.split("/")[-1].split(".")[0]
    sub_key = sub_url.split("/")[-1].split(".")[0]
    
    return img_key, sub_key


async def fetch_space_videos_wbi(
    uid: int, 
    client: httpx.AsyncClient,
    headers: dict,
    img_key: str,
    sub_key: str,
    page: int = 1,
    page_size: int = 50
) -> list[dict]:
    """Fetch videos from space using WBI-signed API."""
    
    # Base params
    params = {
        "mid": str(uid),
        "ps": str(page_size),
        "pn": str(page),
        "order": "pubdate",
        "order_avoided": "true",
        "platform": "web",
    }
    
    # Add timestamp
    params['wts'] = str(int(time.time()))
    
    # Sort and build query
    sorted_params = dict(sorted(params.items()))
    from urllib.parse import urlencode
    query = urlencode(sorted_params)
    
    # Generate mixin key and sign
    mixin_key = get_mixin_key(img_key + sub_key)
    w_rid = md5_hash(query + mixin_key)
    
    params['w_rid'] = w_rid
    
    # Make request
    url = "https://api.bilibili.com/x/space/wbi/arc/search"
    resp = await client.get(url, params=params, headers=headers)
    
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"API Error: {data.get('message')}")
    
    vlist = data.get("data", {}).get("list", {}).get("vlist", [])
    return vlist


@pytest.mark.asyncio
async def test_fetch_all_with_wbi():
    """Fetch ALL videos using WBI-signed API."""
    config = Config()
    headers = config.bilibili.headers.copy()
    # Update referer for space API
    headers["Referer"] = f"https://space.bilibili.com/{UPLOADER_UID}"
    
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: WBI签名 + 空间API")
    print(f"{'='*70}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get WBI keys
        print("Fetching WBI keys...")
        img_key, sub_key = await fetch_wbi_keys(client, headers)
        print(f"  img_key: {img_key[:10]}...")
        print(f"  sub_key: {sub_key[:10]}...")
        
        # Step 2: Fetch all videos
        all_videos = []
        page = 1
        
        while True:
            try:
                print(f"Fetching page {page}...")
                vlist = await fetch_space_videos_wbi(
                    UPLOADER_UID, client, headers, img_key, sub_key, page
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
                await asyncio.sleep(0.5)
                
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
            print(f"\n⚠️ 缺失期数 ({len(missing)} 个): {missing[:30]}{'...' if len(missing) > 30 else ''}")
        else:
            print(f"\n✓ 完整系列！无缺失期数")
        
        # Save full data
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
        
        with open("data/zhebang_series_complete.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Data saved to data/zhebang_series_complete.json")
        
        # Print list
        print(f"\n{'='*70}")
        print(f"视频列表 (按期数排序)")
        print(f"{'='*70}")
        for i, v in enumerate(series_videos[:20], 1):
            ep = extract_ep(v.title)
            print(f"[{i:3}] 第{ep:3}期 | {v.title[:45]}... | {v.play_count:,}")
        if len(series_videos) > 20:
            print(f"... and {len(series_videos) - 20} more")
    
    print(f"\n{'='*70}\n")
    return series_videos


if __name__ == "__main__":
    asyncio.run(test_fetch_all_with_wbi())
