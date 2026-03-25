"""ChemRxiv API fetcher.

This module provides a fetcher for ChemRxiv papers using their public API.
It fetches papers from ChemRxiv within a recent date window, handles pagination, and converts results to Paper objects.

The ChemrxivFetcher class supports:
- Fetching papers from the last 2 days to handle timezone issues
- Handling API pagination (50 papers per page)
- Parsing author information from structured author data
- Building URLs from DOIs or item IDs
- Extracting categories from structured category data

The fetcher uses a 2-day window to ensure it captures papers across different timezones and avoids missing recent submissions.
"""

from datetime import datetime, timedelta

import requests

from ..models import Paper
from .base import FeedFetcher


class ChemrxivFetcher(FeedFetcher):
    """Fetch from ChemRxiv public API."""

    API_URL = "https://chemrxiv.org/engage/chemrxiv/public-api/v1/items"

    def fetch(self) -> list[Paper]:
        """Fetch all papers from the last 2 days (handles timezone issues)."""
        papers = []
        skip = 0
        limit = 50

        # Use 2-day window to handle timezone edge cases
        date_from = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        print(f"  ChemRxiv: fetching papers from {date_from} to {date_to}")

        while True:
            try:
                response = requests.get(
                    self.API_URL,
                    params={
                        "searchDateFrom": date_from,
                        "searchDateTo": date_to,
                        "limit": 10,  # 限制每页获取10篇论文
                        "skip": skip,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                items = data.get("itemHits", [])
                if not items:
                    break

                # 限制只获取10篇论文，避免token使用过多
                for item in items[:10]:
                    item_data = item.get("item", item)

                    # Extract authors
                    authors = []
                    for author in item_data.get("authors", []):
                        name = f"{author.get('firstName', '')} {author.get('lastName', '')}".strip()
                        if name:
                            authors.append(name)

                    # Build URL from DOI or ID
                    doi = item_data.get("doi", "")
                    item_id = item_data.get("id", "")
                    url = f"https://doi.org/{doi}" if doi else f"https://chemrxiv.org/engage/chemrxiv/article-details/{item_id}"

                    paper = Paper(
                        title=item_data.get("title", "").replace("\n", " "),
                        authors=authors,
                        abstract=item_data.get("abstract", ""),
                        url=url,
                        source="ChemRxiv",
                        categories=[cat.get("name", "") for cat in item_data.get("categories", [])],
                        published=item_data.get("publishedDate", ""),
                    )
                    papers.append(paper)

                # 限制总论文数量为10篇
                if len(papers) >= 10:
                    break
                
                # Check if more pages
                if len(items) < 10:
                    break
                skip += 10

            except Exception as e:
                print(f"Error fetching ChemRxiv: {e}")
                break

        return papers
