"""Main pipeline orchestration.

This module orchestrates the full paper filtering pipeline.
It integrates all components to fetch, filter, score, categorize, and post papers.

The run_pipeline function performs the following steps:
1. Validates required environment variables
2. Loads configuration from config.json
3. Initializes fetchers, filters, categorizer, and poster
4. Fetches papers from all sources
5. Deduplicates papers using history
6. Separates papers by key authors (bypass filtering)
7. Applies keyword filter to non-key-author papers
8. Applies LLM relevance scoring to filtered papers
9. Adds key author papers back with high scores
10. Categorizes papers by research area
11. Posts results to DingTalk
12. Exports papers to Supabase (optional)
13. Marks papers as posted in history

The module also includes a load_config function to load configuration from config.json.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from .fetchers import ArxivFetcher, JournalRSSFetcher, SpringerNatureFetcher, ConferenceFetcher, CSJournalFetcher
from .filters import KeywordFilter, LLMFilter, PaperCategorizer
from .filters.llm import InsufficientCreditsError
from .history import PaperHistory
from .key_authors import filter_papers_by_key_authors, get_key_authors_on_paper, load_key_authors
from .dingtalk import DingTalkPoster
from .supabase_export import save_papers_to_supabase


def load_config() -> dict:
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        return json.load(f)


def run_pipeline(dry_run: bool = False, test_mode: bool = False):
    """Run the full paper filtering pipeline."""

    print(f"Starting paper filter pipeline at {datetime.now()}")
    if dry_run:
        print("DRY RUN MODE - will not post to DingTalk")
    if test_mode:
        print("TEST MODE - limiting to 50 papers after keyword filter")

    # Validate required environment variables
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")

    webhook_url = os.environ.get("DINGTALK_WEBHOOK_URL", "")
    dingtalk_secret = os.environ.get("DINGTALK_SECRET", "")
    if not webhook_url and not dry_run:
        raise ValueError("DINGTALK_WEBHOOK_URL environment variable is required")

    # Load config
    config = load_config()
    min_if = config.get("min_impact_factor")
    max_age = config.get("max_age_hours")

    # Initialize components
    fetchers = [
        ArxivFetcher(max_age_hours=max_age),
        # ConferenceFetcher(max_age_hours=max_age),
        # CSJournalFetcher(min_impact_factor=min_if, max_age_hours=max_age),
        # SpringerNatureFetcher(min_impact_factor=min_if, max_age_hours=max_age),
        # JournalRSSFetcher(min_impact_factor=min_if, max_age_hours=max_age),
    ]

    keyword_filter = KeywordFilter(config["keywords"])

    llm_filter = LLMFilter(
        api_key=api_key,
        lab_description=config["lab_description"],
        threshold=config.get("relevance_threshold", 0.6),
        model=config.get("model"),
    )

    categorizer = PaperCategorizer(api_key=api_key, model=config.get("model"))

    dingtalk_poster = DingTalkPoster(webhook_url, secret=dingtalk_secret, dry_run=dry_run)

    history = PaperHistory()

    # Load key authors
    key_authors = load_key_authors()
    print(f"Loaded {len(key_authors)} key authors")

    # Fetch all papers
    print("Fetching papers from all sources...")
    all_papers = []
    for fetcher in fetchers:
        papers = fetcher.fetch()
        print(f"  {fetcher.__class__.__name__}: {len(papers)} papers")
        all_papers.extend(papers)

    print(f"Total fetched: {len(all_papers)} papers")

    # Remove already-posted papers
    new_papers = history.filter_new(all_papers)
    print(f"After deduplication: {len(new_papers)} new papers")

    # Separate papers by key authors (these bypass all filtering)
    key_author_papers, other_papers = filter_papers_by_key_authors(new_papers, key_authors)
    if key_author_papers:
        print(f"Papers from key authors (bypass filtering): {len(key_author_papers)}")
        for paper in key_author_papers:
            authors_found = get_key_authors_on_paper(paper, key_authors)
            print(f"  - {paper.title[:60]}... ({', '.join(authors_found)})")

    # First-pass: keyword filter (only for non-key-author papers)
    keyword_matches = keyword_filter.filter(other_papers)
    print(f"After keyword filter: {len(keyword_matches)} papers")

    # Limit papers in test mode
    if test_mode and len(keyword_matches) > 50:
        keyword_matches = keyword_matches[:50]
        print(f"TEST MODE: limited to {len(keyword_matches)} papers")

    # Second-pass: LLM relevance scoring (only for non-key-author papers)
    credits_exhausted = False
    if keyword_matches:
        print("Running LLM relevance scoring...")
        try:
            relevant_papers = llm_filter.filter(keyword_matches)
            print(f"After LLM filter: {len(relevant_papers)} papers")
        except InsufficientCreditsError:
            print("ERROR: API credits exhausted during LLM scoring")
            relevant_papers = []
            credits_exhausted = True
    else:
        relevant_papers = []

    # Add key author papers with a high score (they bypass filtering)
    # Score of 1.0 and reason indicating key author bypass
    for paper in key_author_papers:
        authors_found = get_key_authors_on_paper(paper, key_authors)
        reason = f"Key author: {', '.join(authors_found)}"
        relevant_papers.append((paper, 1.0, reason))

    if key_author_papers:
        print(f"Total relevant papers (including key authors): {len(relevant_papers)}")

    # Categorize papers by research area
    if relevant_papers:
        print("Categorizing papers by research area...")
        try:
            categorized_papers = categorizer.categorize(relevant_papers)
            for cat, papers in categorized_papers.items():
                if papers:
                    print(f"  {cat}: {len(papers)} papers")
        except InsufficientCreditsError:
            # If categorization fails, put all papers in "Other"
            print("ERROR: API credits exhausted during categorization")
            categorized_papers = {"Other (Self-Driving Labs, Materials, etc.)": relevant_papers}
            credits_exhausted = True
    else:
        categorized_papers = {}

    # Post to DingTalk
    print("Posting to DingTalk...")
    dingtalk_poster.post_papers(categorized_papers, credits_exhausted=credits_exhausted)

    # Export to Supabase for web frontend (non-blocking, failures are logged)
    print("Exporting papers to Supabase...")
    save_papers_to_supabase(categorized_papers)

    # Mark as posted
    if not dry_run:
        history.mark_posted([p for p, _, _ in relevant_papers])


    print("Pipeline complete!")
