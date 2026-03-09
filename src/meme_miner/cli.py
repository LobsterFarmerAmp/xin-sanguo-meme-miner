"""CLI for meme_miner."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from meme_miner.config import Config
from meme_miner.platforms.bilibili import BilibiliPlatform
from meme_miner.analysis.heuristics import HeuristicsDetector
from meme_miner.storage.writer import JsonlWriter
from meme_miner.models import MemeHit

app = typer.Typer(help="Meme Miner - Mine memes from video platforms")
console = Console()


@app.command()
def collect(
    keyword: str = typer.Option(..., "-k", "--keyword", help="Search keyword"),
    platform: str = typer.Option("bilibili", "-p", "--platform", help="Platform to scrape"),
    limit: int = typer.Option(20, "-l", "--limit", help="Number of videos to process"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output file prefix"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
) -> None:
    """Collect memes from videos matching keyword."""
    config = Config()
    if output:
        config.storage.filename_prefix = output
    if verbose:
        config.log_level = "DEBUG"

    console.print(f"[bold green]Meme Miner[/bold green] - Collecting memes for: {keyword}")

    # Initialize components
    if platform == "bilibili":
        platform_scraper = BilibiliPlatform(config)
    else:
        console.print(f"[red]Unsupported platform: {platform}[/red]")
        raise typer.Exit(1)

    detector = HeuristicsDetector(config)
    writer = JsonlWriter(config)

    async def run_collection():
        all_memes: list[MemeHit] = []
        video_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Search for videos
            search_task = progress.add_task(f"Searching videos for '{keyword}'...", total=None)

            videos = []
            async for video in platform_scraper.search_videos(keyword, limit=limit):
                videos.append(video)
                video_count += 1

            progress.update(search_task, completed=True)

            console.print(f"[green]Found {video_count} videos[/green]")

            # Process each video
            for i, video in enumerate(videos):
                task = progress.add_task(
                    f"Processing video {i+1}/{video_count}: {video.title[:40]}...",
                    total=None
                )

                # Fetch danmaku
                danmaku_list = []
                async for danmaku in platform_scraper.get_danmaku(video):
                    danmaku_list.append(danmaku)

                console.print(f"  [dim]Got {len(danmaku_list)} danmaku[/dim]")

                # Detect memes
                memes = list(detector.detect_memes(
                    iter(danmaku_list),
                    platform_scraper.get_platform_name(),
                    video.url
                ))

                if memes:
                    all_memes.extend(memes)
                    console.print(f"  [cyan]Found {len(memes)} memes[/cyan]")

                progress.update(task, completed=True)

        # Rank and save
        ranked_memes = detector.rank_memes(all_memes)

        if ranked_memes:
            saved = writer.write_batch(ranked_memes)
            console.print(f"[green]Saved {saved} memes to {config.storage.output_dir}[/green]")

            # Show top memes
            console.print("\n[bold]Top memes:[/bold]")
            for i, meme in enumerate(ranked_memes[:10], 1):
                console.print(f"  {i}. {meme.quote[:50]}... (score: {meme.score:.1f})")
        else:
            console.print("[yellow]No memes found[/yellow]")

    asyncio.run(run_collection())


@app.command()
def stats(
    date: Optional[str] = typer.Option(None, "-d", "--date", help="Date to show stats (YYYYMMDD)"),
) -> None:
    """Show statistics about collected memes."""
    config = Config()
    writer = JsonlWriter(config)

    memes = writer.read(date)

    if not memes:
        console.print("[yellow]No memes found[/yellow]")
        return

    console.print(f"[bold]Total memes: {len(memes)}[/bold]")

    # Calculate stats
    scores = [m.score for m in memes]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)

    console.print(f"Average score: {avg_score:.2f}")
    console.print(f"Max score: {max_score:.2f}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
) -> None:
    """Start the API server (placeholder)."""
    console.print("[yellow]API server not implemented yet[/yellow]")
    raise typer.Exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
