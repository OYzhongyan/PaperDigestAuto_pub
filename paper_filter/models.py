"""Data models for the paper filter.

This module defines the data model for academic papers in the filtering pipeline.

The Paper dataclass represents an academic paper with the following fields:
- title: Paper title
- authors: List of author names
- abstract: Paper abstract
- url: Paper URL
- source: Source (e.g., arXiv, bioRxiv, journal name)
- categories: List of categories or tags
- published: Publication date string
- version: Paper version (for preprints)

The class also includes a property for generating a unique ID based on the URL hash.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class Paper:
    """Represents an academic paper."""

    title: str
    authors: list[str]
    abstract: str
    url: str
    source: str
    categories: list[str]
    published: str
    version: int | None = None

    @property
    def id(self) -> str:
        """Generate a unique ID based on URL hash."""
        return hashlib.md5(self.url.encode()).hexdigest()[:12]
