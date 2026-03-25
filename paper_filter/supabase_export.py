"""Export papers to Supabase database.

This module provides a function for exporting papers to a Supabase database.
It allows the web frontend to display the papers with ratings and comments.

The save_papers_to_supabase function supports:
- Checking for Supabase credentials
- Creating a Supabase client
- Preparing paper data for insertion
- Upserting papers to handle duplicates
- Logging success or failure

The function exports paper metadata including title, authors, abstract, URL, source, categories, publication date, category, relevance score, and key authors.

Failures are logged but do not raise exceptions, allowing the pipeline to continue regardless of database export success.
"""

import os
from datetime import datetime

from .key_authors import get_key_authors_on_paper, load_key_authors


def save_papers_to_supabase(categorized_papers: dict) -> bool:
    """
    Export papers to Supabase database.

    Args:
        categorized_papers: Dict of {category: [(Paper, score, reason), ...]}

    Returns:
        True on success, False on failure.
        Failures are logged but never raise - pipeline continues regardless.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("  Supabase credentials not set, skipping database export")
        return False

    try:
        from supabase import create_client
        client = create_client(url, key)
    except ImportError:
        print("  supabase package not installed, skipping database export")
        return False
    except Exception as e:
        print(f"  Failed to create Supabase client: {e}")
        return False

    today = datetime.now().date().isoformat()
    papers_to_insert = []

    # Load key authors for marking
    key_authors = load_key_authors()

    for category, papers in categorized_papers.items():
        for paper, score, reason in papers:
            # Find key authors on this paper
            paper_key_authors = get_key_authors_on_paper(paper, key_authors)

            papers_to_insert.append({
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "url": paper.url,
                "source": paper.source,
                "arxiv_categories": paper.categories,
                "published": paper.published if paper.published else None,
                "added_date": today,
                "category": category,
                "relevance_score": score,
                "relevance_reason": reason,
                "key_authors": paper_key_authors if paper_key_authors else None,
            })

    if not papers_to_insert:
        print("  No papers to export to Supabase")
        return True

    try:
        # Upsert to handle duplicates gracefully
        client.table("papers").upsert(
            papers_to_insert,
            on_conflict="id"
        ).execute()
        print(f"  Exported {len(papers_to_insert)} papers to Supabase")
        return True
    except Exception as e:
        print(f"  Failed to export papers to Supabase: {e}")
        return False
