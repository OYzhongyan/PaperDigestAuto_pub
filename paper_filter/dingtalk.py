"""DingTalk webhook integration.

This module provides a class for posting papers to DingTalk via webhook.
It handles message formatting, chunking for large messages, and signature verification.

The DingTalkPoster class supports:
- Posting categorized papers to DingTalk
- Handling message length limits by splitting large messages
- Supporting signature verification for secure webhook calls
- Dry-run mode for testing without actual posting
"""

from datetime import datetime
import hashlib
import hmac
import base64
import time

import requests

from .filters.categorizer import CATEGORIES
from .key_authors import is_key_author, load_key_authors
from .models import Paper


class DingTalkPoster:
    """Post papers to DingTalk via webhook."""

    def __init__(self, webhook_url: str, secret: str = "", dry_run: bool = False):
        self.webhook_url = webhook_url
        self.secret = secret
        self.dry_run = dry_run
        self.key_authors = load_key_authors()

    def post_papers(self, categorized_papers: dict[str, list[tuple[Paper, float, str]]], credits_exhausted: bool = False):
        """Post categorized papers to DingTalk."""

        # Count total papers
        total = sum(len(papers) for papers in categorized_papers.values())

        if total == 0 and not credits_exhausted:
            self._post_message(
                {"msgtype": "markdown", "markdown": {"title": "Daily Paper Digest", "text": "# Daily Paper Digest\nNo relevant papers found today."}}
            )
            return

        if total == 0 and credits_exhausted:
            self._post_message(
                {"msgtype": "markdown", "markdown": {"title": "Daily Paper Digest", "text": "# Daily Paper Digest\n⚠️ API credits exhausted - could not filter papers today. Please top up credits."}}
            )
            return

        # Build message content
        overflow_messages = []  # Additional messages for categories that overflow
        content = f"# Daily Paper Digest - {datetime.now().strftime('%B %d, %Y')}\n\n"
        content += f"Found *{total}* relevant papers in the last 24 hours\n\n"

        # Add warning if credits exhausted
        if credits_exhausted:
            content += "⚠️ *API credits exhausted* - only showing key author papers. Regular filtering was skipped.\n\n"

        # Add each category with papers
        for category in CATEGORIES:
            papers = categorized_papers.get(category, [])
            if not papers:
                continue

            # Category header
            content += f"## {category} ({len(papers)})\n"

            # Paper list - sort by score descending
            papers_sorted = sorted(papers, key=lambda x: x[1], reverse=True)
            paper_lines = []
            for paper, score, reason in papers_sorted:
                # Format title
                title = paper.title
                # Append version for arXiv papers
                if paper.version is not None:
                    title = f"{title} (v{paper.version})"
                # Format authors
                authors_str = self._format_authors(paper.authors)
                if authors_str:
                    paper_lines.append(f"- [{title}]({paper.url}) - {authors_str} ({paper.source})")
                else:
                    paper_lines.append(f"- [{title}]({paper.url}) ({paper.source})")

            # Split paper lines into chunks respecting DingTalk's limit
            chunks = self._chunk_lines(paper_lines, max_chars=2000)

            # First chunk goes in main message
            content += "\n".join(chunks[0]) + "\n\n"

            # Additional chunks get posted as overflow messages later
            for i, chunk in enumerate(chunks[1:], start=2):
                overflow_content = f"# think ## {category} (continued {i}/{len(chunks)})\n\n"
                overflow_content += "\n".join(chunk) + "\n"
                overflow_messages.append({
                    "msgtype": "markdown",
                    "markdown": {
                        "title": f"{category} (continued)",
                        "text": overflow_content
                    }
                })

        # Post main message
        self._post_message({"msgtype": "markdown", "markdown": {"title": "Daily Paper Digest", "text": content}})

        # Post any overflow messages
        for overflow in overflow_messages:
            self._post_message(overflow)

    def _chunk_lines(self, lines: list[str], max_chars: int = 2000) -> list[list[str]]:
        """Split lines into chunks that fit within DingTalk's character limit."""
        if not lines:
            return [["_No papers_"]]

        chunks = []
        current_chunk = []
        current_length = 0

        for line in lines:
            line_length = len(line)
            if current_chunk and current_length + line_length + 1 > max_chars:
                # Start a new chunk
                chunks.append(current_chunk)
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length + 1  # +1 for newline

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _format_authors(self, authors: list[str], max_authors: int = 10) -> str:
        """
        Format author list for DingTalk display.

        - Bold key authors
        - If more than max_authors, truncate with ellipsis but keep final author
        - Key authors are NEVER truncated - they're always shown even if in the
          middle of a long list
          e.g., "A1, A2, ..., **KeyAuthor**, ..., LastAuthor"
        """
        if not authors:
            return ""

        # Format each author, bolding key authors
        def format_author(name: str) -> str:
            if is_key_author(name, self.key_authors):
                return f"**{name}**"
            return name

        if len(authors) <= max_authors:
            return ", ".join(format_author(a) for a in authors)

        # Determine which author indices to show:
        # 1. First (max_authors - 1) authors
        # 2. Last author
        # 3. Any key authors that would otherwise be hidden
        shown_indices = set(range(max_authors - 1))  # First N-1 (e.g., 0-8)
        shown_indices.add(len(authors) - 1)  # Last author

        # Add any key authors that would be truncated
        for i, author in enumerate(authors):
            if is_key_author(author, self.key_authors):
                shown_indices.add(i)

        # Build the formatted string, inserting ellipses where there are gaps
        sorted_indices = sorted(shown_indices)
        parts = []
        prev_idx = -1

        for idx in sorted_indices:
            if prev_idx >= 0 and idx > prev_idx + 1:
                # There's a gap - authors were skipped
                parts.append("...")
            parts.append(format_author(authors[idx]))
            prev_idx = idx

        return ", ".join(parts)

    def _post_message(self, payload: dict):
        """Send a message to DingTalk (or print if dry_run)."""
        # Always save payload for debugging/reuse
        import json
        with open("dingtalk_payload.json", "w") as f:
            json.dump(payload, f, indent=2)

        if self.dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN - Would post to DingTalk:")
            print("=" * 60)
            if "markdown" in payload:
                print(payload["markdown"]["text"])
            print("=" * 60 + "\n")
            return

        # Sign the request if secret is provided
        url = self.webhook_url
        if self.secret:
            timestamp = str(int(time.time() * 1000))
            secret_enc = self.secret.encode('utf-8')
            string_to_sign = f"{timestamp}\n{self.secret}"
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = base64.b64encode(hmac_code).decode('utf-8')
            # 确保URL格式正确，避免重复添加参数
            if "?" in url:
                url = f"{url}&timestamp={timestamp}&sign={sign}"
            else:
                url = f"{url}?timestamp={timestamp}&sign={sign}"

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            print(f"DingTalk response: {response.text}")
        except Exception as e:
            print(f"Error posting to DingTalk: {e}")
