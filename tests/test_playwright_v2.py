"""Fetch ALL videos from UP主 via Playwright with improved selectors."""

import asyncio
import json
import re
from datetime import datetime

import pytest
from playwright.async_api import async_playwright

from meme_miner.models import VideoInfo


UPLOADER_UID = 11732899
UPLOADER_NAME = "吃蛋挞的折棒"
SPACE_URL = f"https://space.bilibili.com/{UPLOADER_UID}/video"


async def fetch_space_playwright_v2(uid: int) -> list[VideoInfo]:
    """Use Playwright to fetch all videos with better handling."""
    videos = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"Loading {SPACE_URL}...")
            await page.goto(SPACE_URL, wait_until="domcontentloaded")
            
            # Wait for video list to appear
            print("Waiting for video list...")
            try:
                await page.wait_for_selector(".video-list-item, .small-item, [data-v-]", timeout=10000)
            except:
                print("Timeout waiting for selector, taking screenshot to debug...")
                await page.screenshot(path="data/debug_space.png")
                print("Screenshot saved to data/debug_space.png")
            
            # Additional wait for JS to render
            await asyncio.sleep(5)
            
            # Get page content for debugging
            content = await page.content()
            print(f"Page loaded, content length: {len(content)}")
            
            # Try to find video elements with various selectors
            selectors = [
                ".video-list-item",
                ".small-item", 
                ".video-list .list-item",
                "[class*='video-card']",
                "[class*='video-list'] > div",
            ]
            
            items = []
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if len(items) > 0:
                    print(f"Found {len(items)} items with selector: {selector}")
                    break
            
            # Scroll to load more
            if len(items) > 0:
                print("Scrolling to load more...")
                for scroll in range(10):
                    await page.evaluate("window.scrollBy(0, 800)")
                    await asyncio.sleep(1)
                    
                    # Check if new items loaded
                    new_items = await page.query_selector_all(selector)
                    if len(new_items) > len(items):
                        print(f"  Scroll {scroll+1}: {len(new_items)} items")
                        items = new_items
                    elif scroll > 5:
                        break
            
            # Extract data from items
            print(f"\nExtracting data from {len(items)} items...")
            for item in items:
                try:
                    # Try multiple ways to get title
                    title = ""
                    for title_sel in [".title", "a[title]", "h3", "a"]:
                        el = await item.query_selector(title_sel)
                        if el:
                            title = await el.get_attribute("title") or await el.inner_text()
                            if title:
                                break
                    
                    # Get link
                    link = ""
                    bvid = ""
                    for link_sel in ["a[href*='/video/']", "a"]:
                        el = await item.query_selector(link_sel)
                        if el:
                            href = await el.get_attribute("href") or ""
                            if "/video/" in href:
                                link = href if href.startswith("http") else f"https:{href}"
                                bvid = href.split("/video/")[-1].split("?")[0].replace("/", "")
                                break
                    
                    # Get play count
                    play_count = 0
                    for play_sel in [".play-text", ".view", ".play", "[class*='play']"]:
                        el = await item.query_selector(play_sel)
                        if el:
                            text = await el.inner_text()
                            play_count = parse_count(text)
                            break
                    
                    if title and bvid:
                        videos.append(VideoInfo(
                            bvid=bvid,
                            title=title.strip(),
                            uploader=UPLOADER_NAME,
                            play_count=play_count,
                            danmaku_count=0,
                            url=f"https://www.bilibili.com/video/{bvid}",
                        ))
                        
                except Exception as e:
                    continue
            
            # Save debug screenshot
            await page.screenshot(path="data/space_final.png")
            
        finally:
            await browser.close()
    
    return videos


def parse_count(text: str) -> int:
    """Parse view count."""
    text = text.strip().replace(",", "").replace(" ", "")
    if not text:
        return 0
    try:
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        return int(float(text))
    except:
        return 0


@pytest.mark.asyncio
async def test_fetch_with_playwright_v2():
    """Fetch videos using improved Playwright."""
    print(f"\n{'='*70}")
    print(f"UP主: {UPLOADER_NAME} (UID: {UPLOADER_UID})")
    print(f"方法: Playwright v2 (优化版)")
    print(f"{'='*70}\n")
    
    videos = await fetch_space_playwright_v2(UPLOADER_UID)
    
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
        print(f"总播放量: {total_plays:,}")
        
        if missing:
            print(f"缺失期数: {len(missing)} 个")
        
        # Save
        output = {
            "uploader": UPLOADER_NAME,
            "uid": UPLOADER_UID,
            "series": "三国杀up锐评新三国",
            "total_episodes": len(series_videos),
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
        
        with open("data/zhebang_series_playwright_v2.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved")
        
        # Show list
        for i, v in enumerate(series_videos[:20], 1):
            ep = extract_ep(v.title)
            print(f"[{i}] 第{ep}期 | {v.title[:40]}... | {v.play_count:,}")
    
    print(f"\n{'='*70}\n")
    return series_videos


if __name__ == "__main__":
    asyncio.run(test_fetch_with_playwright_v2())
