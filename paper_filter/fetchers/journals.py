"""Journal fetchers using RSS feeds.

This module provides fetchers for papers from various journal RSS feeds.
It includes utilities for parsing and cleaning journal RSS feed data, filtering journals by impact factor, and fetching papers from specific journal feeds.

Key components:
- clean_html_abstract: Cleans HTML content from RSS abstracts
- parse_pub_date: Parses publication dates from RSS feed entries
- is_within_hours: Checks if a paper is within the specified age limit
- IMPACT_FACTORS: Dictionary of journal impact factors for filtering
- get_impact_factor: Gets the impact factor for a journal
- filter_journals_by_impact: Filters journals by minimum impact factor
- SpringerNatureFetcher: Fetches papers from Springer Nature journals
- JournalRSSFetcher: Fetches papers from other journal RSS feeds

The module supports fetching papers from major journals including Nature, Science, ACS journals, RSC journals, Wiley journals, and Cell Press journals.
"""

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser


def clean_html_abstract(raw_text: str) -> str:
    """Clean HTML from RSS abstract/summary content.

    RSC and ACS feeds return HTML-formatted summaries. This extracts
    the actual abstract text by stripping HTML tags and cleaning up
    the result.
    """
    if not raw_text:
        return ""

    # Unescape HTML entities first
    text = html.unescape(raw_text)

    # Remove script and style elements entirely
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove image tags (TOC graphics, license badges, etc.)
    text = re.sub(r'<img[^>]*>', '', text, flags=re.IGNORECASE)

    # Remove anchor tags but keep their text content
    text = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)

    # Replace <br> and </div> with newlines for better text extraction
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)

    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n', text)  # Remove empty lines
    text = re.sub(r'[ \t]+', ' ', text)     # Collapse spaces
    text = '\n'.join(line.strip() for line in text.split('\n'))  # Strip each line
    text = text.strip()

    # Filter out metadata lines that aren't the actual abstract
    # RSC feeds include journal name, DOI, license info, author list
    # ACS feeds include journal name and DOI but no abstract
    lines = text.split('\n')
    filtered_lines = []
    skip_patterns = [
        r'^Digital Discovery,?\s*\d{4}',
        r'^Chemical Science,?\s*\d{4}',
        r'^DOI:\s*10\.',
        r'^Open Access$',
        r'Creative Commons',
        r'^This article is licensed',
        r'^The content of this RSS Feed',
        r'^To cite this article',
        r'^Advance Article$',
        r'^Tutorial Review$',
        # ACS journal names (these appear as metadata, not abstracts)
        r'^Journal of Chemical Information',
        r'^Journal of Chemical Theory',
        r'^Journal of the American Chemical Society$',
        r'^ACS Central Science$',
        r'^ACS Catalysis$',
        r'^Journal of Medicinal Chemistry$',
        r'^The Journal of Organic Chemistry$',
        r'^Organic Letters$',
        r'^J\.\s*(Am\.|Med\.|Org\.)\s*Chem\.',
    ]
    for line in lines:
        if not line:
            continue
        # Skip metadata lines
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
            continue
        filtered_lines.append(line)

    return '\n'.join(filtered_lines).strip()

from ..models import Paper
from .base import FeedFetcher


def parse_pub_date(date_str: str) -> datetime | None:
    """Parse publication date from RSS feed entry."""
    if not date_str:
        return None
    try:
        # Try RFC 2822 format (common in RSS)
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        pass
    # Try ISO format
    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(date_str[:len(fmt)+5], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def is_within_hours(date_str: str, max_hours: int | None) -> bool:
    """Check if a date string is within the last max_hours. None means no limit."""
    if max_hours is None:
        return True
    pub_date = parse_pub_date(date_str)
    if pub_date is None:
        return True  # Include if we can't parse the date
    now = datetime.now(timezone.utc)
    age_hours = (now - pub_date).total_seconds() / 3600
    return age_hours <= max_hours

# 2023 Impact Factors (approximate)
# Preprints use None and are always included
IMPACT_FACTORS = {
    # Springer Nature
    "Nature": 64.8,
    "Nature Communications": 16.6,
    "Nature Computational Science": 12.0,
    "Nature Machine Intelligence": 23.8,
    "Nature Chemistry": 24.5,
    "Nature Chemical Biology": 14.8,
    "Nature Methods": 48.0,
    "Nature Biotechnology": 46.9,
    "npj Computational Materials": 9.7,
    # AAAS
    "Science": 56.9,
    "Science Advances": 13.6,
    # ACS
    "JACS": 15.0,
    "JCIM": 5.6,
    "JCTC": 5.5,
    "ACS Central Science": 18.2,
    "J. Med. Chem.": 7.3,
    "ACS Catalysis": 13.7,
    "Analytical Chemistry": 7.4,
    "J. Org. Chem.": 3.6,
    "Org. Lett.": 5.2,
    # RSC
    "Digital Discovery": 6.2,
    "Chemical Science": 9.0,
    "Chem. Commun.": 4.4,
    "Reaction Chem. Eng.": 3.6,
    "Green Chemistry": 9.8,
    "RSC Medicinal Chemistry": 3.4,
    "Catalysis Sci. Technol.": 5.0,
    "PCCP": 2.9,
    "Lab Chip": 6.1,
    "RSC Chem. Biol.": 5.4,
    "Nanoscale": 5.8,
    # Wiley
    "Angew. Chem.": 16.6,
    # Cell Press
    "Cell": 64.5,
    "Chem": 23.5,
    "Cell Chemical Biology": 8.6,
    "Patterns": 6.7,
    "iScience": 5.8,
    # Preprints (always included)
    "arXiv": None,
    "bioRxiv": None,
    "chemRxiv": None,
}


def get_impact_factor(journal_name: str) -> float | None:
    """Get impact factor for a journal. Returns None for preprints."""
    return IMPACT_FACTORS.get(journal_name)


def filter_journals_by_impact(
    journals: dict[str, str], min_impact_factor: float | None
) -> dict[str, str]:
    """Filter journals by minimum impact factor. None threshold includes all."""
    if min_impact_factor is None:
        return journals
    return {
        name: url
        for name, url in journals.items()
        if IMPACT_FACTORS.get(name) is None  # Always include preprints
        or IMPACT_FACTORS.get(name, 0) >= min_impact_factor
    }


class SpringerNatureFetcher(FeedFetcher):
    """Fetch from Springer Nature journals via RSS."""

    RSS_FEEDS = {
        "Nature": "https://www.nature.com/nature.rss",
        "Nature Communications": "https://www.nature.com/ncomms.rss",
        "Nature Computational Science": "https://www.nature.com/natcomputsci.rss",
        "Nature Machine Intelligence": "https://www.nature.com/natmachintell.rss",
        "Nature Chemistry": "https://www.nature.com/nchem.rss",
        "Nature Chemical Biology": "https://www.nature.com/nchembio.rss",
        "Nature Methods": "https://www.nature.com/nmeth.rss",
        "Nature Biotechnology": "https://www.nature.com/nbt.rss",
        "npj Computational Materials": "https://www.nature.com/npjcompumats.rss",
    }

    def __init__(self, min_impact_factor: float | None = None, max_age_hours: int | None = None):
        self.min_impact_factor = min_impact_factor
        self.max_age_hours = max_age_hours

    def fetch(self) -> list[Paper]:
        papers = []
        feeds = filter_journals_by_impact(self.RSS_FEEDS, self.min_impact_factor)
        for journal_name, rss_url in feeds.items():
            try:
                feed = feedparser.parse(rss_url)
                count = 0
                for entry in feed.entries:
                    pub_date = entry.get("published", entry.get("updated", ""))
                    if not is_within_hours(pub_date, self.max_age_hours):
                        continue
                    raw_abstract = entry.get("summary", entry.get("description", ""))
                    paper = Paper(
                        title=entry.get("title", "").replace("\n", " "),
                        authors=self._parse_authors(entry),
                        abstract=clean_html_abstract(raw_abstract),
                        url=entry.get("link", ""),
                        source=journal_name,
                        categories=[],
                        published=pub_date,
                    )
                    papers.append(paper)
                    count += 1
                print(f"  {journal_name}: {count} papers")
            except Exception as e:
                print(f"  Error fetching {journal_name}: {e}")
        return papers

    def _parse_authors(self, entry) -> list[str]:
        authors = entry.get("authors", [])
        if authors:
            # Check if multiple authors in list (Nature) vs single concatenated (ACS)
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


class JournalRSSFetcher(FeedFetcher):
    """Fetch from CS and AI-related journal RSS feeds."""

    FEEDS = {
        # Science family
        "Science": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
        "Science Advances": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv",
        # PNAS
        "PNAS": "https://www.pnas.org/rss/featured_research.xml",
        # Nature family (CS/AI related)
        "Nature": "https://www.nature.com/nature.rss",
        "Nature Communications": "https://www.nature.com/ncomms.rss",
        "Nature Computational Science": "https://www.nature.com/natcomputsci.rss",
        "Nature Machine Intelligence": "https://www.nature.com/natmachintell.rss",
        # Wiley AI/Nature
        "Wiley AI": "https://onlinelibrary.wiley.com/journal/2696987x",
    }

    def __init__(self, min_impact_factor: float | None = None, max_age_hours: int | None = None):
        self.min_impact_factor = min_impact_factor
        self.max_age_hours = max_age_hours

    def fetch(self) -> list[Paper]:
        papers = []
        feeds = filter_journals_by_impact(self.FEEDS, self.min_impact_factor)
        for journal_name, url in feeds.items():
            try:
                feed = feedparser.parse(url)
                count = 0
                for entry in feed.entries:
                    pub_date = entry.get("published", entry.get("updated", ""))
                    if not is_within_hours(pub_date, self.max_age_hours):
                        continue
                    raw_abstract = entry.get("summary", entry.get("description", ""))
                    paper = Paper(
                        title=entry.get("title", "").replace("\n", " "),
                        authors=self._parse_authors(entry),
                        abstract=clean_html_abstract(raw_abstract),
                        url=entry.get("link", ""),
                        source=journal_name,
                        categories=[],
                        published=pub_date,
                    )
                    papers.append(paper)
                    count += 1
                print(f"  {journal_name}: {count} papers")
            except Exception as e:
                print(f"  Error fetching {journal_name}: {e}")
        return papers

    def _parse_authors(self, entry) -> list[str]:
        authors = entry.get("authors", [])
        if authors:
            # Check if multiple authors in list (Nature) vs single concatenated (ACS)
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
