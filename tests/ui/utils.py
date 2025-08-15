"""
utils.py

This module provides utilities for web scraping and HTML parsing,
specifically focused on extracting BLAST-related information from
web pages.

Features:
- HTML parsing with BeautifulSoup
- Command-line interface for file/URL processing
- Error handling and logging
"""

import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import click
from bs4 import BeautifulSoup
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class BlastScraper:
    """
    Handles web scraping operations for BLAST-related content.
    """

    def __init__(self):
        self.session = requests.Session()

    def extract_items_from_html(self, content: str) -> List[str]:
        """
        Extract item IDs from HTML content containing jstree elements.

        Args:
            content: HTML content to parse

        Returns:
            List of unique item IDs
        """
        soup = BeautifulSoup(content, features="html.parser")
        items = [
            tag.get("id") for tag in soup.find_all("a", class_="jstree-anchor")
            if tag.get("id")
        ]
        return sorted(list(set(items)))

    def scrape_url(self, url: str) -> List[str]:
        """
        Scrape items from a given URL.

        Args:
            url: URL to scrape

        Returns:
            List of extracted items

        Raises:
            requests.RequestException: If URL fetch fails
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return self.extract_items_from_html(response.text)
        except requests.RequestException as e:
            console.log(f"[red]Error fetching URL {url}: {str(e)}[/red]")
            raise

    def scrape_file(self, filepath: Path) -> List[str]:
        """
        Extract items from a local HTML file.

        Args:
            filepath: Path to HTML file

        Returns:
            List of extracted items
        """
        try:
            content = filepath.read_text(encoding='utf-8')
            return self.extract_items_from_html(content)
        except Exception as e:
            console.log(f"[red]Error reading file {filepath}: {str(e)}[/red]")
            raise


@click.group()
def cli():
    """BLAST web scraping utilities."""
    pass


@cli.command()
@click.argument('source')
@click.option('-o', '--output', type=click.Path(), help='Output file path')
def scrape(source: str, output: Optional[str]) -> None:
    """
    Scrape items from a URL or local file.

    Args:
        source: URL or file path to scrape
        output: Optional file path to save results
    """
    try:
        scraper = BlastScraper()

        # Determine if source is URL or file
        parsed = urlparse(source)
        if parsed.scheme and parsed.netloc:
            items = scraper.scrape_url(source)
        else:
            items = scraper.scrape_file(Path(source))

        # Output results
        if output:
            Path(output).write_text('\n'.join(items))
            console.log(f"Results saved to {output}")
        else:
            console.print(items)

    except Exception as e:
        console.log(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()