#!/usr/bin/env python3
"""Entry point for the paper filter bot.

This script is the main entry point for the paper filtering pipeline.
It provides command-line options for running the pipeline, including dry-run mode,
test mode, and history synchronization.

Usage:
    python run.py [--dry-run] [--test] [--sync-history]

Options:
    --dry-run: Print results instead of posting to DingTalk
    --test: Test mode with limited papers for quick testing
    --sync-history: Mark all current papers as seen without filtering or posting
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from paper_filter import run_pipeline


def sync_history():
    """Mark all currently fetchable papers as 'seen' without LLM filtering or posting."""
    from datetime import datetime
    # from paper_filter.fetchers import (
    #     ArxivFetcher, BiorxivFetcher, ChemrxivFetcher,
    #     JournalRSSFetcher, SpringerNatureFetcher
    # )
    from paper_filter.fetchers import (
        ArxivFetcher,
        JournalRSSFetcher, 
        SpringerNatureFetcher
    )
    from paper_filter.pipeline import load_config

    config = load_config()
    min_if = config.get("min_impact_factor")
    max_age = config.get("max_age_hours")
    max_num_papers = config.get("max_num_papers")

    fetchers = [
        ArxivFetcher(max_age_hours=max_age, max_num_papers=max_num_papers),
        SpringerNatureFetcher(min_impact_factor=min_if, max_age_hours=max_age),
        JournalRSSFetcher(min_impact_factor=min_if, max_age_hours=max_age),
    ]

    print("Fetching papers to sync history...")
    all_papers = []
    for fetcher in fetchers:
        papers = fetcher.fetch()
        print(f"  {fetcher.__class__.__name__}: {len(papers)} papers")
        all_papers.extend(papers)

    # Load existing history
    history_file = Path("posted_papers.json")
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
    else:
        history = {}

    # Add all papers to history
    now = datetime.now().isoformat()
    added = 0
    for paper in all_papers:
        if paper.id not in history:
            history[paper.id] = now
            added += 1

    # Save
    with open(history_file, "w") as f:
        json.dump(history, f)

    print(f"Added {added} papers to history (total: {len(history)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and post relevant papers")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results instead of posting to DingTalk",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: limit to 50 papers for quick/cheap testing",
    )
    parser.add_argument(
        "--sync-history",
        action="store_true",
        help="Mark all current papers as seen without filtering or posting",
    )
    args = parser.parse_args()

    if args.sync_history:
        sync_history()
    else:
        run_pipeline(dry_run=args.dry_run, test_mode=args.test)
        
