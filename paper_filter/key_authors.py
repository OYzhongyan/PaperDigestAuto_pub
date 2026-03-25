"""Key authors module for highlighting and bypass logic.

This module provides functions for handling key authors in the paper filtering pipeline.
It supports identifying papers by key authors and allowing them to bypass normal filtering.

Key functions:
- _normalize_name: Normalizes author names for comparison (case-insensitive, accent-insensitive)
- load_key_authors: Loads key authors from key_authors.json
- is_key_author: Checks if an author is in the key authors list
- paper_has_key_author: Checks if a paper has at least one key author
- get_key_authors_on_paper: Returns list of key authors found on a paper
- filter_papers_by_key_authors: Splits papers into those with and without key authors

Key authors are defined in key_authors.json and their papers bypass all filtering and are always included in the digest.
"""

import json
import unicodedata
from pathlib import Path

from .models import Paper


def _normalize_name(name: str) -> str:
    """
    Normalize a name for comparison: lowercase, strip accents, keep only letters.

    "Frank Noé" -> "franknoe"
    "Günter Klambauer" -> "gunterklambauer"
    "Jean-Louis Reymond" -> "jeanlouisreymond"
    "Pietro Liò" -> "pietrolio"
    "Al\\'an Aspuru-Guzik" -> "alanaspuruguzik"
    """
    # NFKD decomposition splits accented chars into base + combining mark
    normalized = unicodedata.normalize("NFKD", name.lower())
    # Keep only alphabetic characters (strips accents, spaces, hyphens, LaTeX crud, etc.)
    return "".join(c for c in normalized if c.isalpha())


def load_key_authors() -> set[str]:
    """Load key authors from key_authors.json. Returns set of normalized names."""
    config_path = Path(__file__).parent.parent / "key_authors.json"
    try:
        with open(config_path) as f:
            data = json.load(f)
            return {_normalize_name(name) for name in data.get("authors", [])}
    except FileNotFoundError:
        return set()


def is_key_author(author_name: str, key_authors: set[str]) -> bool:
    """Check if an author is in the key authors list (accent and case insensitive)."""
    return _normalize_name(author_name) in key_authors


def paper_has_key_author(paper: Paper, key_authors: set[str]) -> bool:
    """Check if a paper has at least one key author."""
    for author in paper.authors:
        if is_key_author(author, key_authors):
            return True
    return False


def get_key_authors_on_paper(paper: Paper, key_authors: set[str]) -> list[str]:
    """Return list of key authors found on a paper (preserving original case)."""
    return [author for author in paper.authors if is_key_author(author, key_authors)]


def filter_papers_by_key_authors(
    papers: list[Paper], key_authors: set[str]
) -> tuple[list[Paper], list[Paper]]:
    """
    Split papers into those with key authors and those without.

    Returns:
        (papers_with_key_authors, papers_without_key_authors)
    """
    with_key = []
    without_key = []
    for paper in papers:
        if paper_has_key_author(paper, key_authors):
            with_key.append(paper)
        else:
            without_key.append(paper)
    return with_key, without_key
