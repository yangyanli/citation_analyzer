"""Interfaces and base classes for data providers and scorers."""

from abc import ABC, abstractmethod
from typing import Any


class CitationProvider(ABC):
    """Abstract base class for citation data providers (e.g. S2, Google Scholar, OpenAlex)."""

    @abstractmethod
    def search_paper(self, title: str) -> dict[str, Any] | None:
        """Search for a paper and return a normalized metadata dict."""
        pass

    @abstractmethod
    def fetch_citations(self, paper_id: str) -> list[dict[str, Any]]:
        """Fetch citations for a specific paper ID."""
        pass


class CitationScorer(ABC):
    """Abstract base class for citation scoring/classification (e.g. Multi-LLM, Section-Aware)."""

    @abstractmethod
    def score_citation(
        self, citation_data: dict[str, Any], criteria: dict[str, Any]
    ) -> dict[str, Any]:
        """Score a single citation and return a results dict."""
        pass
