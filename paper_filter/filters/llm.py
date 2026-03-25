"""LLM-based relevance scoring filter.

This module provides an LLM-based filter for scoring paper relevance.
It uses DeepSeek API to score papers based on their relevance to the lab's research focus.

The LLMFilter class supports:
- Initialization with API key, lab description, and threshold
- Scoring papers in batches to reduce API calls
- Filtering papers by relevance score
- Handling API errors and credit balance issues

The module processes papers in batches of 10 to optimize API usage and includes error handling for API credit exhaustion.
"""

import json
import re
import requests
from tqdm import tqdm

from ..models import Paper

# Journals that don't include abstracts in their RSS feeds
NO_ABSTRACT_JOURNALS = {
    'JACS', 'JCIM', 'JCTC', 'ACS Central Science',
    'J. Med. Chem.', 'ACS Catalysis', 'J. Org. Chem.', 'Org. Lett.'
}


class InsufficientCreditsError(Exception):
    """Raised when API credits are depleted."""
    pass


class LLMFilter:
    """Second-pass LLM-based relevance scoring."""

    # Default model - can be overridden via config
    DEFAULT_MODEL = "deepseek-chat"

    def __init__(
        self,
        api_key: str,
        lab_description: str,
        threshold: float = 0.6,
        model: str = None,
    ):
        self.api_key = api_key
        self.lab_description = lab_description
        self.threshold = threshold
        self.model = model or self.DEFAULT_MODEL

    def score_papers(self, papers: list[Paper]) -> list[tuple[Paper, float, str]]:
        """Score papers for relevance. Returns (paper, score, reason) tuples."""
        if not papers:
            return []

        results = []

        # Process in batches to reduce API calls
        batch_size = 10

        with tqdm(total=len(papers), desc="Scoring papers", unit="paper") as pbar:
            for i in range(0, len(papers), batch_size):
                batch = papers[i : i + batch_size]
                batch_results = self._score_batch(batch)
                results.extend(batch_results)
                pbar.update(len(batch))

        return results

    def _score_batch(self, papers: list[Paper]) -> list[tuple[Paper, float, str]]:
        """Score a batch of papers."""

        # Format papers for the prompt
        papers_text = ""
        has_no_abstract_papers = False
        for idx, paper in enumerate(papers):
            abstract = paper.abstract[:1500] if paper.abstract else ""
            if paper.source in NO_ABSTRACT_JOURNALS and not abstract:
                has_no_abstract_papers = True
            papers_text += f"""
---
Paper {idx + 1}:
Title: {paper.title}
Source: {paper.source}
Abstract: {abstract if abstract else "(not available)"}
---
"""

        # Add note about journals without abstracts if applicable
        no_abstract_note = ""
        if has_no_abstract_papers:
            no_abstract_note = """
IMPORTANT: Some papers are from peer-reviewed journals (JACS, JCIM, JCTC, etc.) whose RSS feeds do not include abstracts. For these papers, evaluate relevance based on the title alone. Since these are established, peer-reviewed journals, give the benefit of the doubt if the title suggests relevance to the lab's research areas - a relevant-sounding title from these journals should score similarly to a paper with a matching abstract.
"""

        prompt = f"""You are a research assistant helping a lab filter academic papers for relevance.

Lab Focus: {self.lab_description}
{no_abstract_note}
Below are {len(papers)} papers. For each paper, assess its relevance to the lab's research focus.

{papers_text}

For each paper, provide:
1. A relevance score from 0.0 to 1.0 (where 1.0 = highly relevant, 0.0 = not relevant)
2. A brief one-sentence reason for the score

Respond in JSON format:
{{
    "scores": [
        {{"paper": 1, "score": 0.8, "reason": "..."}},
        {{"paper": 2, "score": 0.3, "reason": "..."}},
        ...
    ]
}}

Be selective - only give high scores (>0.6) to papers that are genuinely relevant to the lab's research focus as described above."""

        try:
            # DeepSeek API endpoint
            url = "https://api.deepseek.com/v1/chat/completions"
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.0
            }
            
            # Send request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            response_text = response_data["choices"][0]["message"]["content"]

            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                data = json.loads(json_match.group())
                scores = data.get("scores", [])

                results = []
                for score_data in scores:
                    idx = score_data["paper"] - 1
                    if 0 <= idx < len(papers):
                        results.append(
                            (
                                papers[idx],
                                score_data["score"],
                                score_data.get("reason", ""),
                            )
                        )
                return results

        except Exception as e:
            error_str = str(e)
            # Check for credit balance error - this should stop the whole pipeline
            if "credit balance" in error_str.lower() or "insufficient balance" in error_str.lower():
                raise InsufficientCreditsError("API credit balance is too low to continue scoring")
            print(f"Error scoring batch: {e}")

        # Fallback for other errors: return all papers with neutral score
        return [(p, 0.5, "Error during scoring") for p in papers]

    def filter(self, papers: list[Paper]) -> list[tuple[Paper, float, str]]:
        """Filter papers above threshold."""
        scored = self.score_papers(papers)
        return [(p, s, r) for p, s, r in scored if s >= self.threshold]
