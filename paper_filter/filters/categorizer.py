"""LLM-based paper categorization.

This module provides an LLM-based categorizer for papers.
It uses DeepSeek API to categorize papers into predefined research areas.

The PaperCategorizer class supports:
- Initialization with API key and model
- Categorizing papers into research areas
- Handling API errors and credit balance issues

Predefined categories include:
- Quantum Machine Learning & Architecture
- Quantum Error Correction & Mitigation
- Quantum Generative Models
- Quantum Networking & Cryptography
- PDE Solving & Deep Learning Theory

The module uses LLM to classify papers based on their titles and sources.
"""

import json
import re
import requests
from tqdm import tqdm

from ..models import Paper
from .llm import InsufficientCreditsError

CATEGORIES = [
    "Quantum Machine Learning & Architecture",
    "Quantum Error Correction & Mitigation",
    "Quantum Generative Models",
    "Quantum Networking & Cryptography",
    "PDE Solving & Deep Learning Theory",
]


class PaperCategorizer:
    """Categorize papers into research areas using LLM."""

    DEFAULT_MODEL = "deepseek-chat"

    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    def categorize(
        self, papers: list[tuple[Paper, float, str]]
    ) -> dict[str, list[tuple[Paper, float, str]]]:
        """Categorize papers into research areas. Returns dict of category -> papers."""
        if not papers:
            return {cat: [] for cat in CATEGORIES}

        # Get categories for all papers
        paper_categories = self._categorize_batch(papers)

        # Group by category
        result = {cat: [] for cat in CATEGORIES}
        for (paper, score, reason), category in zip(papers, paper_categories):
            if category in result:
                result[category].append((paper, score, reason))
            else:
                result["Other (Self-Driving Labs, Materials, etc.)"].append((paper, score, reason))

        return result

    def _categorize_batch(
        self, papers: list[tuple[Paper, float, str]]
    ) -> list[str]:
        """Categorize a batch of papers."""
        categories_list = "\n".join(f"- {cat}" for cat in CATEGORIES)

        # Format papers
        papers_text = ""
        for idx, (paper, score, reason) in enumerate(papers):
            papers_text += f"{idx + 1}. {paper.title} ({paper.source})\n"

        prompt = f"""Categorize each paper into exactly one of these research areas:

{categories_list}

Papers to categorize:
{papers_text}

Guidelines:
- "Quantum Machine Learning & Architecture": quantum machine learning, quantum neural networks, quantum architecture search, quantum circuit compilation, quantum circuit generation, quantum circuit optimization, neutral atoms, quantum agent
- "Quantum Error Correction & Mitigation": quantum error correction, quantum error mitigation, quantum noise suppression
- "Quantum Generative Models": quantum generative model, generative model, diffusion model, flow matching
- "Quantum Networking & Cryptography": quantum networking, post-quantum cryptography
- "PDE Solving & Deep Learning Theory": PDE solving, PDE, partial differential equations, deep learning theory

Respond with a JSON array of category names in the same order as the papers:
{{"categories": ["Category1", "Category2", ...]}}"""

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
            
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                data = json.loads(json_match.group())
                categories = data.get("categories", [])
                # Validate and pad if needed
                while len(categories) < len(papers):
                    categories.append("Other")
                return categories[:len(papers)]

        except Exception as e:
            error_str = str(e)
            if "credit balance" in error_str.lower() or "insufficient balance" in error_str.lower():
                raise InsufficientCreditsError("API credit balance is too low to categorize papers")
            print(f"Error categorizing papers: {e}")

        # Fallback: all "Other"
        return ["Other"] * len(papers)
