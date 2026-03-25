"""Paper history tracking to avoid duplicate posts.

This module provides a class for tracking papers that have already been posted.
It helps avoid duplicate posts by maintaining a history of posted paper IDs.

The PaperHistory class supports:
- Loading existing history from a JSON file
- Filtering out already posted papers
- Marking papers as posted
- Automatically pruning old entries (older than 30 days)
- Saving history back to the JSON file

The history is stored in a JSON file with paper IDs as keys and timestamps as values.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from .models import Paper


class PaperHistory:
    """Track papers we've already posted to avoid duplicates."""

    def __init__(self, history_file: str = "posted_papers.json"):
        self.history_file = Path(history_file)
        self.posted_ids = self._load_history()

    def _load_history(self) -> set:
        if self.history_file.exists():
            with open(self.history_file) as f:
                data = json.load(f)
                # Keep only last 30 days
                cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                return {pid for pid, date in data.items() if date > cutoff}
        return set()

    def _save_history(self):
        # Load existing to preserve dates
        existing = {}
        if self.history_file.exists():
            with open(self.history_file) as f:
                existing = json.load(f)

        # Update with new IDs
        today = datetime.now().isoformat()
        for pid in self.posted_ids:
            if pid not in existing:
                existing[pid] = today

        # Prune old entries
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        existing = {k: v for k, v in existing.items() if v > cutoff}

        with open(self.history_file, "w") as f:
            json.dump(existing, f)

    def filter_new(self, papers: list[Paper]) -> list[Paper]:
        """Return only papers we haven't posted before."""
        return [p for p in papers if p.id not in self.posted_ids]

    def mark_posted(self, papers: list[Paper]):
        """Mark papers as posted."""
        for p in papers:
            self.posted_ids.add(p.id)
        self._save_history()
