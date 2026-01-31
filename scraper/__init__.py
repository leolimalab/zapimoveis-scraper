"""Módulo de scraping."""

from .browser import BrowserManager
from .api_client import ZapImoveisClient
from .parser import ListingParser
from .retry import retry_with_backoff
from .html_extractor import HTMLExtractor

__all__ = [
    "BrowserManager",
    "ZapImoveisClient",
    "ListingParser",
    "retry_with_backoff",
    "HTMLExtractor",
]
