"""Base scraper interface."""
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    """Abstract base scraper for extracting textual sources."""

    @abstractmethod
    def scrape(self):
        """Execute scraping logic."""
        pass
