"""
terminal.py

This module provides terminal output utilities using the Rich library for consistent
and informative console output throughout the application.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn)
from rich.table import Table

console = Console()


def print_status(message: str, status: str = "info") -> None:
    """
    Prints a status message with an appropriate style.
    Status can be: info, success, error, warning
    """
    styles = {
        "info": "blue",
        "success": "green",
        "error": "red",
        "warning": "yellow",
    }

    icons = {
        "info": "ℹ",
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
    }

    style = styles.get(status, "default")
    icon = icons.get(status, "→")
    console.print(f"{icon} {message}", style=style)


def create_progress() -> Progress:
    """
    Creates a consistent progress bar style for the application.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[blue]{task.description}"),
        BarColumn(complete_style="green"),
        TaskProgressColumn(),
        console=console,
    )


def show_summary(
    operation: str,
    stats: Dict[str, Any],
    duration: datetime,
    details: Optional[str] = None,
) -> None:
    """
    Shows a summary of the completed operation with statistics.
    """
    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    for key, value in stats.items():
        if isinstance(value, (int, float)):
            formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        table.add_row(key, formatted_value)

    table.add_row("Duration", str(duration))

    panel = Panel(table, title=f"[bold blue]{operation} Summary", border_style="blue")
    console.print(panel)

    if details:
        console.print(details, style="dim")


def log_error(error_message: str, error: Optional[Exception] = None) -> None:
    """
    Displays an error message with optional exception details.
    """
    console.print(f"[red]Error:[/red] {error_message}")
    if error:
        console.print(f"[dim red]Details: {str(error)}[/dim red]")


def print_header(text: str) -> None:
    """
    Prints a section header.
    """
    console.print(f"\n[bold blue]{text}[/bold blue]")
    console.print("[blue]" + "─" * len(text) + "[/blue]")
