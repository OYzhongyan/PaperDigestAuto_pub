"""arXiv RSS feed fetcher.

This module provides a fetcher for arXiv papers by category.
It fetches papers from arXiv's RSS feeds, parses the entries, and converts them to Paper objects.

The ArxivFetcher class supports:
- Fetching papers from multiple arXiv categories
- Parsing author information from different formats
- Extracting paper versions from arXiv IDs
- Deduplicating papers by URL

Supported categories include machine learning, AI, computer vision, biomolecules, chemical physics, materials science, and quantitative methods.
"""

import re
from datetime import datetime, timezone

import feedparser

from ..models import Paper
from .base import FeedFetcher


class ArxivFetcher(FeedFetcher):
    """Fetch from arXiv RSS feeds by category."""

    # Categories relevant to quantum AI and related fields
    CATEGORIES = [
        "cs.LG",           # Machine Learning
        "cs.AI",           # Artificial Intelligence
        "cs.CV",           # Computer Vision
        "quant-ph",        # Quantum Physics
        "cs.ET",           # Emerging Technologies
        "cs.AR",           # Hardware Architecture
        "stat.ML",         # Machine Learning (stats)
        "math.OC",         # Optimization and Control
        "math.PR",         # Probability
        "physics.app-ph",  # Applied Physics
    ]

    def __init__(self, max_age_hours: int = None, max_num_papers: int = None):
        self.max_age_hours = max_age_hours
        self.max_num_papers = max_num_papers

    def fetch(self) -> list[Paper]:
        papers = []
        for category in self.CATEGORIES:
            url = f"https://rss.arxiv.org/rss/{category}"
            try:
                feed = feedparser.parse(url)
                if self.max_num_papers is None:
                    feed_entries = feed.entries
                else:
                    feed_entries = feed.entries[:self.max_num_papers]
                for entry in feed_entries:
                    # Check if paper is within age limit
                    if not self._is_within_age(entry):
                        continue
                        
                    cats = [tag.term for tag in entry.get("tags", [])]
                    paper_url = entry.get("link", "")

                    paper = Paper(
                        title=entry.get("title", "").replace("\n", " "),
                        authors=self._parse_authors(entry),
                        abstract=entry.get("summary", ""),
                        url=paper_url,
                        source="arXiv",
                        categories=cats if cats else [category],
                        published=entry.get("published", ""),
                        version=self._extract_version(entry.get("id", "")),
                    )
                    papers.append(paper)
            except Exception as e:
                print(f"Error fetching arXiv {category}: {e}")

        # Deduplicate by URL
        seen = set()
        unique = []
        for p in papers:
            if p.url not in seen:
                seen.add(p.url)
                unique.append(p)
        return unique

    def _is_within_age(self, entry) -> bool:
        """Check if paper is within age limit."""
        if self.max_age_hours is None:
            return True
        
        pub_date = entry.get("published", "")
        if not pub_date:
            return True
        
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            now = datetime.now(timezone.utc)
            age_hours = (now - dt).total_seconds() / 3600
            return age_hours <= self.max_age_hours
        except:
            return True

    def _parse_authors(self, entry) -> list[str]:
        authors = entry.get("authors", [])
        if authors:
            # Check if multiple authors in list vs single concatenated
            if len(authors) > 1:
                # Multiple separate author entries - extract each name
                return [a.get("name", str(a)) for a in authors if a.get("name")]
            else:
                # Single entry - may be concatenated, try splitting
                name = authors[0].get("name", str(authors[0]))
                return self._split_author_string(name)
        author = entry.get("author", "")
        if author:
            return self._split_author_string(author)
        return []

    def _split_author_string(self, author_str: str) -> list[str]:
        """Split a comma/and separated author string into list."""
        if not author_str:
            return []
        # Replace " and " with comma for uniform splitting
        author_str = author_str.replace(" and ", ", ")
        return [a.strip() for a in author_str.split(",") if a.strip()]

    def _extract_version(self, guid: str) -> int | None:
        """Extract version from arXiv guid (e.g., 'oai:arXiv.org:2602.00012v1')."""
        # Match arXiv paper ID pattern: YYMM.NNNNN followed by version
        match = re.search(r"\d{4}\.\d{4,5}v(\d+)", guid)
        if match:
            return int(match.group(1))
        return None
