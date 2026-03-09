#!/usr/bin/env python3
"""
Meme Miner - 10 Hour Continuous Runner
Runs meme collection continuously for 10 hours with multiple keywords.
"""

import asyncio
import sys
import time
import signal
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, 'src')

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from meme_miner.config import Config
from meme_miner.platforms.bilibili import BilibiliPlatform
from meme_miner.analysis.heuristics import HeuristicsDetector
from meme_miner.storage.writer import JsonlWriter

console = Console()

# Configuration
RUN_DURATION_HOURS = 10
VIDEOS_PER_BATCH = 3
REQUEST_DELAY_BETWEEN_BATCHES = 30  # seconds between batches
BATCHES_PER_KEYWORD = 10  # Process 10 batches per keyword before rotating

# Keywords to cycle through
KEYWORDS = [
    "新三国",
    "三国",
    "三国演义",
    "曹操",
    "刘备",
    "诸葛亮",
    "关羽",
    "吕布",
    "赵云",
    "张飞",
]

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    console.print("\n[yellow]Shutdown requested. Finishing current batch...[/yellow]")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class LongRunner:
    """Manages long-running meme collection."""
    
    def __init__(self):
        self.config = Config()
        self.platform = BilibiliPlatform(self.config)
        self.detector = HeuristicsDetector(self.config)
        self.writer = JsonlWriter(self.config)
        self.stats = {
            "start_time": datetime.now().isoformat(),
            "videos_processed": 0,
            "danmaku_collected": 0,
            "memes_found": 0,
            "batches_completed": 0,
            "errors": 0,
            "unique_videos": 0,
        }
        self.log_file = Path("data/runner_stats.json")
        # Track processed videos to avoid duplicates
        self.processed_bvids: set[str] = set()
        
    def save_stats(self):
        """Save current statistics to file."""
        self.stats["last_update"] = datetime.now().isoformat()
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
    
    def log_progress(self, message: str):
        """Log progress message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"[{timestamp}] {message}")
        
        # Also write to log file
        with open("data/runner.log", 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    async def process_batch(self, keyword: str, batch_num: int) -> dict:
        """Process one batch of videos."""
        results = {
            "videos": 0,
            "danmaku": 0,
            "memes": 0,
            "errors": 0,
        }
        
        self.log_progress(f"Batch {batch_num}: Processing keyword '{keyword}'")
        
        try:
            # Search for videos
            videos = []
            skipped_count = 0
            async for video in self.platform.search_videos(keyword, limit=VIDEOS_PER_BATCH * 2):  # Fetch more to account for duplicates
                if shutdown_requested:
                    break
                # Skip already processed videos
                if video.bvid in self.processed_bvids:
                    skipped_count += 1
                    continue
                videos.append(video)
                if len(videos) >= VIDEOS_PER_BATCH:
                    break
                
            if not videos:
                self.log_progress(f"  No videos found for '{keyword}'")
                return results
                
            if skipped_count > 0:
                self.log_progress(f"  Skipped {skipped_count} already processed videos")
            
            self.log_progress(f"  Processing {len(videos)} new videos")
            
            # Process each video
            all_memes = []
            for i, video in enumerate(videos):
                if shutdown_requested:
                    break
                    
                try:
                    # Get danmaku
                    danmaku_list = []
                    async for dm in self.platform.get_danmaku(video):
                        danmaku_list.append(dm)
                    
                    results["danmaku"] += len(danmaku_list)
                    
                    if danmaku_list:
                        # Detect memes
                        memes = list(self.detector.detect_memes(
                            iter(danmaku_list),
                            self.platform.get_platform_name(),
                            video.url
                        ))
                        results["memes"] += len(memes)
                        all_memes.extend(memes)
                        
                except Exception as e:
                    self.log_progress(f"  Error processing video {video.bvid}: {e}")
                    results["errors"] += 1
                finally:
                    # Mark video as processed regardless of success
                    self.processed_bvids.add(video.bvid)
            
            # Save memes
            if all_memes:
                ranked = self.detector.rank_memes(all_memes)
                saved = self.writer.write_batch(ranked)
                self.log_progress(f"  Saved {saved} memes")
            
            results["videos"] = len(videos)
            
        except Exception as e:
            self.log_progress(f"  Batch error: {e}")
            results["errors"] += 1
        
        return results
    
    async def run(self):
        """Run the long collection process."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=RUN_DURATION_HOURS)
        
        self.log_progress(f"=== Starting 10-hour meme collection ===")
        self.log_progress(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_progress(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_progress(f"Keywords: {', '.join(KEYWORDS)}")
        self.log_progress("")
        
        batch_count = 0
        keyword_index = 0
        
        try:
            while datetime.now() < end_time and not shutdown_requested:
                batch_count += 1
                keyword = KEYWORDS[keyword_index % len(KEYWORDS)]
                
                # Process batch
                results = await self.process_batch(keyword, batch_count)
                
                # Update stats
                self.stats["videos_processed"] += results["videos"]
                self.stats["unique_videos"] = len(self.processed_bvids)
                self.stats["danmaku_collected"] += results["danmaku"]
                self.stats["memes_found"] += results["memes"]
                self.stats["errors"] += results["errors"]
                self.stats["batches_completed"] += 1
                
                # Save stats
                self.save_stats()
                
                # Log summary
                elapsed = datetime.now() - start_time
                remaining = end_time - datetime.now()
                self.log_progress(f"Batch {batch_count} complete. Stats: {self.stats['videos_processed']} total videos ({self.stats['unique_videos']} unique), {self.stats['memes_found']} memes")
                self.log_progress(f"Elapsed: {elapsed}, Remaining: {remaining}")
                self.log_progress("")
                
                # Rotate keyword every BATCHES_PER_KEYWORD batches
                if batch_count % BATCHES_PER_KEYWORD == 0:
                    keyword_index += 1
                    self.log_progress(f"Rotating to next keyword: {KEYWORDS[keyword_index % len(KEYWORDS)]}")
                
                # Sleep between batches
                if not shutdown_requested:
                    self.log_progress(f"Sleeping {REQUEST_DELAY_BETWEEN_BATCHES}s before next batch...")
                    await asyncio.sleep(REQUEST_DELAY_BETWEEN_BATCHES)
                    
        except Exception as e:
            self.log_progress(f"Fatal error: {e}")
            import traceback
            self.log_progress(traceback.format_exc())
        
        finally:
            # Final summary
            end_time = datetime.now()
            total_duration = end_time - start_time
            
            self.log_progress("")
            self.log_progress("=== Collection Complete ===")
            self.log_progress(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_progress(f"Total duration: {total_duration}")
            self.log_progress(f"Final stats: {json.dumps(self.stats, indent=2, ensure_ascii=False)}")
            
            # Save final stats
            self.stats["end_time"] = end_time.isoformat()
            self.stats["total_duration_seconds"] = total_duration.total_seconds()
            self.save_stats()
            
            console.print(f"\n[green]Complete! Results saved to {self.config.storage.output_dir}[/green]")
            console.print(f"Stats saved to {self.log_file}")


async def main():
    runner = LongRunner()
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
