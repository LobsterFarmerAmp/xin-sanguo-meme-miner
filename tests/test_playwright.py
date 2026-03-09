"""Fetch ALL videos from UP主 吃蛋挞的折棒 via Playwright browser automation.

Uses Playwright to navigate to the space page and extract video list.
"""

import asyncio
import json
import re
from datetime import datetime

import httpx
import pytest

from meme_miner.config import Config
from meme_miner.models import VideoInfo


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"
SPACE_URL = f"https://space.bilibili.com/{UPLOADER_UID}/video"


async def fetch_space_with_playwright(uid: int) -> list[VideoInfo]:
    """Use Playwright to fetch all videos from space page."""
    from playwright.async_api import async_playwright
    
    videos = []
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            # Navigate to space
            print(f"Navigating to {SPACE_URL}...")
            await page.goto(SPACE_URL, wait_until="networkidle")
            await asyncio.sleep(3)  # Wait for JS to load
            
            # Scroll to load more videos (if there's pagination/infinite scroll)
            previous_count = 0
            max_scrolls = 20
            
            for i in range(max_scrolls):
                # Get current video count
                cards = await page.query_selector_all(".video-list-item, .small-item")
                current_count = len(cards)
                
                if current_count == previous_count and i > 0:
                    print(f"No more videos loading after {i} scrolls")
                    break
                
                print(f"Scroll {i+1}: Found {current_count} videos")
                previous_count = current_count
                
                # Scroll down
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1.5)
            
            # Extract video data
            print("\nExtracting video data...")
            
            # Try different selectors
            selectors = [
                ".video-list-item",
                ".small-item",
                "[class*='video']",
                "[class*='item']",
            ]
            
            items = []
            for sel in selectors:
                items = await page.query_selector_all(sel)
                if len(items) > 5:
                    print(f"Using selector: {sel} ({len(items)} items)")
                    break
            
            for item in items:
                try:
                    # Extract title
                    title_el = await item.query_selector(".title, .content-title, a[title]")
                    title = await title_el.get_attribute("title") if title_el else ""
                    if not title:
                        title_el = await item.query_selector("a")
                        title = await title_el.inner_text() if title_el else ""
                    
                    # Extract link/BV
                    link_el = await item.query_selector("a[href*='/video/']")
                    href = await link_el.get_attribute("href") if link_el else ""
                    bvid = href.split("/video/")[-1].split("?")[0] if "/video/" in href else ""
                    url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
                    
                    # Extract play count
                    play_el = await item.query_selector(".play-text, .view-text, .play")
                    play_text = await play_el.inner_text() if play_el else "0"
                    play_count = parse_count(play_text)
                    
                    # Only add if it has required data
                    if title and bvid:
                        videos.append(VideoInfo(
                            bvid=bvid,
                            title=title.strip(),
                            uploader=UPLOADER_NAME,
                            play_count=play_count,
                            danmaku_count=0,  # Not easily available on list page
                            url=url,
                        ))
                        
                except Exception as e:
                    continue
            
        finally:
            await browser.close()
    
    return videos


def parse_count(text: str) -> int:
    """Parse view count like '1.2万' to number."""
    text = text.strip()
    if not text:
        return 0
    
    # Remove non-numeric characters except . and 万
    text = text.replace(",", "").replace(" ", "")
    
    try:
        if "万" in text:
            num = float(text.replace("万", ""))
            return int(num * 10000)
        return int(float(text))
    except:
        return 0


@pytest.mark.asyncio
async def test_fetch_with_playwright():
    """Fetch videos using Playwright browser."""
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: Playwright 浏览器自动化")
    print(f"{'='*70}\n")
    
    videos = await fetch_space_with_playwright(UPLOADER_UID)
    
    print(f"\nTotal fetched: {len(videos)}")
    
    # Filter for series
    series_videos = [v for v in videos if "锐评新三国" in v.title]
    
    # Sort by episode
    def extract_ep(title: str) -> int:
        m = re.search(r'新三国(\d+)', title)
        return int(m.group(1)) if m else 9999
    
    series_videos.sort(key=lambda v: extract_ep(v.title))
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"统计结果")
    print(f"{'='*70}")
    print(f"UP主总视频数: {len(videos)}")
    print(f"'锐评新三国'系列: {len(series_videos)} 期")
    
    if series_videos:
        episodes = [extract_ep(v.title) for v in series_videos]
        max_ep = max(episodes)
        all_eps = set(episodes)
        missing = [i for i in range(1, max_ep + 1) if i not in all_eps]
        
        total_plays = sum(v.play_count for v in series_videos)
        
        print(f"期数范围: 第1期 ~ 第{max_ep}期")
        print(f"系列总播放: {total_plays:,}")
        
        if missing:
            print(f"\n⚠️ 缺失期数: {missing[:20]}{'...' if len(missing) > 20 else ''}")
        
        # Save
        output = {
            "uploader": UPLOADER_NAME,
            "uid": UPLOADER_UID,
            "series": "三国杀up锐评新三国",
            "total_episodes": len(series_videos),
            "episode_range": f"1-{max_ep}",
            "missing_episodes": missing,
            "total_plays": total_plays,
            "videos": [
                {
                    "title": v.title,
                    "bvid": v.bvid,
                    "url": v.url,
                    "play": v.play_count,
                    "episode": extract_ep(v.title),
                }
                for v in series_videos
            ],
            "fetched_at": datetime.now().isoformat(),
        }
        
        with open("data/zhebang_series_playwright.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved to data/zhebang_series_playwright.json")
        
        # Show list
        print(f"\n视频列表:")
        for i, v in enumerate(series_videos[:15], 1):
            ep = extract_ep(v.title)
            print(f"[{i:3}] 第{ep:3}期 | {v.title[:40]}... | {v.play_count:,}")
    
    print(f"\n{'='*70}\n")
    return series_videos


if __name__ == "__main__":
    asyncio.run(test_fetch_with_playwright())
