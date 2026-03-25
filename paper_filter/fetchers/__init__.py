"""Paper fetchers for various academic sources."""

from .base import FeedFetcher
from .arxiv import ArxivFetcher
from .journals import JournalRSSFetcher, SpringerNatureFetcher
from .conferences import ConferenceFetcher, CSJournalFetcher

__all__ = [
    "FeedFetcher",
    "ArxivFetcher",
    "JournalRSSFetcher",
    "SpringerNatureFetcher",
    "ConferenceFetcher",
    "CSJournalFetcher",
]
