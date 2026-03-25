"""Paper Filter Bot - Modular package for filtering academic papers.

This package provides a modular system for fetching, filtering, and posting academic papers.
It includes components for fetching papers from various sources, filtering by keywords and LLM relevance,
categorizing papers, and posting results to DingTalk.

Main components:
- Paper: Data model for academic papers
- PaperHistory: Manages paper history for deduplication
- DingTalkPoster: Posts papers to DingTalk
- run_pipeline: Main pipeline orchestration function
- save_papers_to_supabase: Exports papers to Supabase database
"""

from .models import Paper
from .history import PaperHistory
from .dingtalk import DingTalkPoster
from .pipeline import run_pipeline
from .supabase_export import save_papers_to_supabase

__all__ = ["Paper", "PaperHistory", "DingTalkPoster", "run_pipeline", "save_papers_to_supabase"]
