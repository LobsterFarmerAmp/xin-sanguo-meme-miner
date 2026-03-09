"""Bilibili platform scraper."""

import asyncio
import re
import xml.etree.ElementTree as ET
from typing import AsyncIterator, Optional
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from meme_miner.platforms.base import BasePlatform
from meme_miner.models import VideoInfo, Danmaku
from meme_miner.config import Config


class BilibiliPlatform(BasePlatform):
    """Bilibili video platform scraper."""

    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.base_url = self.config.bilibili.search_url
        self.headers = self.config.bilibili.headers
        self.request_delay = self.config.bilibili.request_delay

    def get_platform_name(self) -> str:
        return "bilibili"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))
    )
    async def _search_videos_request(self, keyword: str, page: int = 1) -> dict:
        """Make API request to search videos."""
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": 20,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.base_url,
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0:
                raise Exception(f"Bilibili API error: {data.get('message', 'unknown')}")
            return data.get("data", {}).get("result", [])

    async def search_videos(self, keyword: str, limit: int = 20) -> AsyncIterator[VideoInfo]:
        """Search for videos by keyword."""
        page = 1
        collected = 0

        while collected < limit:
            try:
                results = await self._search_videos_request(keyword, page)
                if not results:
                    break

                for item in results:
                    if collected >= limit:
                        break

                    video = VideoInfo(
                        bvid=item.get("bvid", ""),
                        title=item.get("title", ""),
                        uploader=item.get("author", ""),
                        play_count=item.get("play", 0) or 0,
                        danmaku_count=item.get("danmaku", 0) or 0,
                        url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    )
                    yield video
                    collected += 1

                page += 1
                await asyncio.sleep(self.request_delay)

            except Exception as e:
                break

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))
    )
    async def _get_cid(self, bvid: str) -> Optional[int]:
        """Get cid for a video using the pagelist API."""
        url = self.config.bilibili.video_info_url
        params = {"bvid": bvid}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0:
                return None
            # The data field is a list directly, not a dict with "list" key
            pages = data.get("data", [])
            if pages and isinstance(pages, list):
                return pages[0].get("cid")
            return None

    async def get_danmaku(self, video: VideoInfo) -> AsyncIterator[Danmaku]:
        """Fetch danmaku for a video."""
        # Get cid if not already present
        cid = video.cid
        if cid is None:
            cid = await self._get_cid(video.bvid)
            if cid is None:
                return

        # Fetch danmaku XML
        url = self.config.bilibili.danmaku_url.format(cid=cid)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()

                # Parse XML
                root = ET.fromstring(response.content)

                for d in root.findall("d"):
                    p = d.get("p", "")
                    text = d.text or ""

                    if not text:
                        continue

                    # Parse timestamp from p attribute (format: timestamp,mode,...)
                    try:
                        timestamp = float(p.split(",")[0])
                    except (ValueError, IndexError):
                        timestamp = 0.0

                    # Parse other attributes
                    attrs = p.split(",")
                    likes = 0
                    if len(attrs) >= 6:
                        try:
                            likes = int(attrs[4])
                        except (ValueError, IndexError):
                            pass

                    yield Danmaku(
                        text=text,
                        timestamp=timestamp,
                        likes=likes,
                    )

            except Exception:
                pass

        await asyncio.sleep(self.request_delay)
