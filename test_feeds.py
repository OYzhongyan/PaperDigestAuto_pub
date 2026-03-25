#!/usr/bin/env python3
"""Test individual RSS feeds."""

import argparse
from paper_filter.fetchers import (
    ArxivFetcher,
    BiorxivFetcher,
    ChemrxivFetcher,
    JournalRSSFetcher,
    SpringerNatureFetcher,
)


def test_fetcher(name: str, fetcher, limit: int = 5):
    """Test a single fetcher and print results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)

    try:
        papers = fetcher.fetch()
        print(f"Found {len(papers)} papers\n")

        for paper in papers[:limit]:
            print(f"Title: {paper.title[:80]}...")
            print(f"  URL: {paper.url}")
            print(f"  Source: {paper.source}")
            print(f"  Authors: {', '.join(paper.authors[:3])}")
            print()

    except Exception as e:
        print(f"ERROR: {e}")


def test_journals_by_source(limit: int = 5, include_springer: bool = True):
    """Test journals and group results by source."""
    papers = []

    if include_springer:
        springer = SpringerNatureFetcher()
        papers.extend(springer.fetch())

    rss = JournalRSSFetcher()
    papers.extend(rss.fetch())

    # Group by source
    by_source = {}
    for paper in papers:
        if paper.source not in by_source:
            by_source[paper.source] = []
        by_source[paper.source].append(paper)

    for source, source_papers in sorted(by_source.items()):
        print(f"\n{'='*60}")
        print(f"{source}: {len(source_papers)} papers")
        print('='*60)

        for paper in source_papers[:limit]:
            print(f"  • {paper.title[:70]}...")
            print(f"    {paper.url}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Test RSS feed fetchers")
    parser.add_argument(
        "source",
        nargs="?",
        choices=["arxiv", "biorxiv", "chemrxiv", "springer", "journals", "all"],
        default="all",
        help="Which source to test (default: all)",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=5,
        help="Number of papers to show per source (default: 5)",
    )
    parser.add_argument(
        "--by-journal",
        action="store_true",
        help="For journals, show results grouped by journal",
    )
    args = parser.parse_args()

    fetchers = {
        "arxiv": ("arXiv", ArxivFetcher()),
        "biorxiv": ("bioRxiv", BiorxivFetcher()),
        "chemrxiv": ("ChemRxiv", ChemrxivFetcher()),
        "springer": ("Springer Nature", SpringerNatureFetcher()),
        "journals": ("Other Journals (RSS)", JournalRSSFetcher()),
    }

    if args.source in ["journals", "springer"] and args.by_journal:
        test_journals_by_source(args.limit, include_springer=(args.source != "journals"))
    elif args.source == "all":
        for name, fetcher in fetchers.values():
            test_fetcher(name, fetcher, args.limit)
    else:
        name, fetcher = fetchers[args.source]
        test_fetcher(name, fetcher, args.limit)


if __name__ == "__main__":
    main()
