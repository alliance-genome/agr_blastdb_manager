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
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

console = Console()


def print_status(message: str, status: str = "info") -> None:
    """
    Prints a clean status message.
    Status can be: info, success, error, warning
    """
    styles = {
        "info": "white",
        "success": "green",
        "error": "red",
        "warning": "yellow",
    }

    icons = {
        "info": "→",
        "success": "✓",
        "error": "✗",
        "warning": "!",
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
    console.print(f"[red]✗ Error:[/red] {error_message}")
    if error:
        console.print(f"[dim red]Details: {str(error)}[/dim red]")


def log_success(message: str) -> None:
    """
    Displays a success message.
    """
    console.print(f"[green]✓ {message}[/green]")


def log_warning(message: str) -> None:
    """
    Displays a warning message.
    """
    console.print(f"[yellow]⚠ {message}[/yellow]")


def print_header(text: str) -> None:
    """
    Prints a clean section header.
    """
    console.print(f"\n[bold cyan]{text}[/bold cyan]")


def print_error_details(title: str, details: Dict[str, Any]) -> None:
    """
    Prints error details in a formatted box.
    """
    table = Table(box=box.ROUNDED, border_style="red")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    for key, value in details.items():
        table.add_row(key, str(value))

    panel = Panel(table, title=f"[bold red]{title}[/bold red]", border_style="red")
    console.print(panel)


def print_processing_status(
    current: int, total: int, item_name: str, status: str = "processing"
) -> None:
    """
    Prints current processing status with progress indicator.
    """
    percentage = (current / total) * 100 if total > 0 else 0
    status_color = {
        "processing": "blue",
        "success": "green",
        "error": "red",
        "warning": "yellow",
    }.get(status, "blue")

    console.print(
        f"[{status_color}][{current}/{total}] ({percentage:.1f}%) {item_name}[/{status_color}]"
    )


def print_simple(message: str) -> None:
    """
    Prints a simple message without styling.
    """
    console.print(message)


def print_progress_line(current: int, total: int, name: str, status: str) -> None:
    """
    Prints a single line progress update.
    """
    if status == "success":
        console.print(f"[green]✓[/green] [{current}/{total}] {name}")
    elif status == "error":
        console.print(f"[red]✗[/red] [{current}/{total}] {name}")
    else:
        console.print(f"[blue]→[/blue] [{current}/{total}] {name}")


def print_minimal_header(text: str) -> None:
    """
    Prints a minimal header for cleaner output.
    """
    console.print(f"\n[bold]{text}[/bold]")
