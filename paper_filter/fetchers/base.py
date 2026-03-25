"""Base class for feed fetchers."""

from ..models import Paper


class FeedFetcher:
    """Base class for fetching papers from RSS feeds."""

    def fetch(self) -> list[Paper]:
        """Fetch papers from the source. Override in subclasses."""
        raise NotImplementedError
