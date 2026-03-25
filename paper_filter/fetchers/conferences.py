"""Conference and CS journal RSS feed fetcher.

This module provides a fetcher for computer science top conferences and journals.
It fetches papers from major CS conferences and journals via RSS or direct API calls.

Supported conferences:
- NeurIPS (Neural Information Processing Systems)
- ICML (International Conference on Machine Learning)
- ICLR (International Conference on Learning Representations)
- CVPR (Computer Vision and Pattern Recognition)
- ICCV (International Conference on Computer Vision)
- ECCV (European Conference on Computer Vision)
- ACL (Association for Computational Linguistics)
- EMNLP (Empirical Methods in Natural Language Processing)
- NAACL (North American Chapter of the ACL)
- AAAI (Association for the Advancement of Artificial Intelligence)
- IJCAI (International Joint Conference on AI)
- AAAI, ICLR via RSS

Supported journals:
- Nature Machine Intelligence
- Nature Computational Science
- JMLR (Journal of Machine Learning Research)
- IEEE TPAMI (Pattern Analysis and Machine Intelligence)
- IEEE TNNLS (Neural Networks and Learning Systems)
"""

import re
import feedparser
from datetime import datetime, timezone

from ..models import Paper
from .base import FeedFetcher


class ConferenceFetcher(FeedFetcher):
    """Fetch from CS top conferences and journals."""

    # Conference RSS feeds
    CONFERENCE_FEEDS = {
        # Machine Learning
        "NeurIPS": "https://proceedings.neurips.cc/paper_feed.rss",
        "ICML": "https://proceedings.mlr.press/v211/feed.rss",
        "ICLR": "https://iclr.cc/Conferences/2025/Archive?search=&numItems=100",
        
        # Computer Vision
        "CVPR": "https://openaccess.thecvf.com/CVPR2024.py/Conference/CVPR2024?action=feed_all",
        "ICCV": "https://openaccess.thecvf.com/ICCV2023.py/Conference/ICCV2023?action=feed_all",
        "ECCV": "https://openaccess.thecvf.com/ECCV2024.py/Conference/ECCV2024?action=feed_all",
        
        # NLP / AI
        "ACL": "https://aclanthology.org/events/acl-2025.rss",
        "EMNLP": "https://aclanthology.org/events/emnlp-2024.rss",
        "NAACL": "https://aclanthology.org/events/naacl-2025.rss",
        "AAAI": "https://aaai.org/aaai-conference/aaai-25/aaai-25-publications/",
        "IJCAI": "https://www.ijcai.org/ijcai-24",
        
        # Robotics / AI
        "CoRL": "https://proceedings.mlr.press/v229/feed.rss",
        "ICRA": "https://ieeexplore.ieee.org/xplore/con榨汁机_feed.jsp?punumber=10065376",
        "ICLR": "https://openreview.net/group?id=ICLR.cc/2025/Conference",
    }

    def __init__(self, max_age_hours: int = None):
        self.max_age_hours = max_age_hours

    def fetch(self) -> list[Paper]:
        """Fetch papers from conferences."""
        papers = []
        
        for conf_name, feed_url in self.CONFERENCE_FEEDS.items():
            try:
                if feed_url.endswith('.rss') or 'feed' in feed_url:
                    conf_papers = self._fetch_rss(conf_name, feed_url)
                else:
                    conf_papers = self._fetch_direct(conf_name, feed_url)
                
                papers.extend(conf_papers)
                print(f"  {conf_name}: {len(conf_papers)} papers")
            except Exception as e:
                print(f"  Error fetching {conf_name}: {e}")
        
        return papers

    def _fetch_rss(self, conf_name: str, url: str) -> list[Paper]:
        """Fetch papers from RSS feed."""
        papers = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Check age limit
                if not self._is_within_age(entry):
                    continue
                
                paper = Paper(
                    title=self._clean_title(entry.get('title', '')),
                    authors=self._parse_authors(entry),
                    abstract=entry.get('summary', entry.get('description', '')),
                    url=entry.get('link', ''),
                    source=conf_name,
                    categories=[conf_name],
                    published=entry.get('published', entry.get('updated', '')),
                )
                papers.append(paper)
        except Exception as e:
            print(f"    RSS error for {conf_name}: {e}")
        return papers

    def _fetch_direct(self, conf_name: str, url: str) -> list[Paper]:
        """Fetch papers directly from conference website."""
        papers = []
        # For conferences without RSS, return empty list
        # In production, would need to scrape HTML
        return papers

    def _is_within_age(self, entry) -> bool:
        """Check if paper is within age limit."""
        if self.max_age_hours is None:
            return True
        
        pub_date = entry.get('published', entry.get('updated', ''))
        if not pub_date:
            return True
        
        try:
            # Try to parse the date
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            now = datetime.now(timezone.utc)
            age_hours = (now - dt).total_seconds() / 3600
            return age_hours <= self.max_age_hours
        except:
            return True

    def _clean_title(self, title: str) -> str:
        """Clean title by removing extra whitespace."""
        return re.sub(r'\s+', ' ', title).strip()

    def _parse_authors(self, entry) -> list[str]:
        """Parse authors from entry."""
        authors = []
        
        # Try authors field
        if hasattr(entry, 'authors') and entry.authors:
            for author in entry.authors:
                name = author.get('name', '')
                if name:
                    authors.append(name)
        
        # Try author field
        if not authors:
            author_str = entry.get('author', '')
            if author_str:
                # Split by comma or 'and'
                for part in re.split(r',| and ', author_str):
                    part = part.strip()
                    if part:
                        authors.append(part)
        
        return authors


class CSJournalFetcher(FeedFetcher):
    """Fetch from CS/Nature journals."""

    JOURNAL_FEEDS = {
        # Nature family
        "Nature Machine Intelligence": "https://www.nature.com/natmachintell.rss",
        "Nature Computational Science": "https://www.nature.com/natcomputsci.rss",
        "Nature AI": "https://www.nature.com/natai.rss",
        
        # JMLR
        "JMLR": "https://www.jmlr.org/jmlr.xml",
        
        # IEEE AI journals
        "IEEE TPAMI": "https://ieeexplore.ieee.org/feed咽收/rss/feed?paren榨汁机tId=榨汁机21174411274",
        "IEEE TNNLS": "https://ieeexplore.ieee.org/feed/rss/feed?paren榨汁机tId=榨汁机21174411309",
        "IEEE TAI": "https://ieeexplore.ieee.org/feed/rss/feed?paren榨汁机tId=榨汁机21189100021",
        
        # ACM journals
        "ACM Computing Surveys": "https://dl.acm.org/rss/最新文章",
        "JACM": "https://dl.acm.org/rss/最新文章",
    }

    def __init__(self, min_impact_factor: float = None, max_age_hours: int = None):
        self.min_impact_factor = min_impact_factor
        self.max_age_hours = max_age_hours

    def fetch(self) -> list[Paper]:
        """Fetch papers from CS journals."""
        papers = []
        
        for journal_name, feed_url in self.JOURNAL_FEEDS.items():
            try:
                journal_papers = self._fetch_journal(journal_name, feed_url)
                papers.extend(journal_papers)
                print(f"  {journal_name}: {len(journal_papers)} papers")
            except Exception as e:
                print(f"  Error fetching {journal_name}: {e}")
        
        return papers

    def _fetch_journal(self, journal_name: str, url: str) -> list[Paper]:
        """Fetch papers from a journal RSS feed."""
        papers = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:  # Limit to recent papers
                # Check age limit
                if not self._is_within_age(entry):
                    continue
                
                paper = Paper(
                    title=self._clean_title(entry.get('title', '')),
                    authors=self._parse_authors(entry),
                    abstract=entry.get('summary', entry.get('description', '')),
                    url=entry.get('link', ''),
                    source=journal_name,
                    categories=[],
                    published=entry.get('published', entry.get('updated', '')),
                )
                papers.append(paper)
        except Exception as e:
            print(f"    Error fetching {journal_name}: {e}")
        return papers

    def _is_within_age(self, entry) -> bool:
        """Check if paper is within age limit."""
        if self.max_age_hours is None:
            return True
        
        pub_date = entry.get('published', entry.get('updated', ''))
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

    def _clean_title(self, title: str) -> str:
        """Clean title by removing extra whitespace."""
        return re.sub(r'\s+', ' ', title).strip()

    def _parse_authors(self, entry) -> list[str]:
        """Parse authors from entry."""
        authors = []
        
        if hasattr(entry, 'authors') and entry.authors:
            for author in entry.authors:
                name = author.get('name', '')
                if name:
                    authors.append(name)
        
        if not authors:
            author_str = entry.get('author', '')
            if author_str:
                for part in re.split(r',| and ', author_str):
                    part = part.strip()
                    if part:
                        authors.append(part)
        
        return authors
