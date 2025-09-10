"""
terminal.py

Professional terminal output utilities using Rich library for the AGR BLAST Database Manager.
Provides consistent, branded, and informative console output throughout the application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

# Professional console with enhanced features
console = Console(record=True, width=120)


def print_app_banner() -> None:
    """
    Prints the professional application banner.
    """
    banner_text = Text.assemble(
        ("AGR", "bold cyan"),
        (" BLAST Database Manager", "bold white"),
        (" v1.0", "dim white")
    )
    
    banner = Panel(
        Align.center(banner_text),
        box=box.DOUBLE,
        border_style="cyan",
        padding=(1, 2),
        title="[bold cyan]Alliance of Genome Resources[/bold cyan]",
        subtitle="[dim]Professional BLAST Database Pipeline[/dim]"
    )
    console.print(banner)
    console.print()


def print_phase_header(phase: str, description: str = "") -> None:
    """
    Prints a professional phase header for major operations.
    """
    text = Text()
    text.append("█ ", style="cyan")
    text.append(phase.upper(), style="bold cyan")
    if description:
        text.append(f" - {description}", style="dim white")
    
    panel = Panel(
        text,
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1)
    )
    console.print(panel)


def print_status(message: str, status: str = "info", indent: int = 0) -> None:
    """
    Prints a professional status message with consistent styling.
    Status can be: info, success, error, warning, processing
    """
    styles = {
        "info": "bright_blue",
        "success": "bright_green", 
        "error": "bright_red",
        "warning": "bright_yellow",
        "processing": "bright_cyan",
        "debug": "dim white"
    }

    icons = {
        "info": "ℹ",
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️",
        "processing": "⚙️",
        "debug": "🔍"
    }

    style = styles.get(status, "white")
    icon = icons.get(status, "•")
    indent_str = "  " * indent
    
    console.print(f"{indent_str}{icon} {message}", style=style)


def create_progress() -> Progress:
    """
    Creates a professional progress bar with enhanced styling.
    """
    return Progress(
        SpinnerColumn(spinner_style="cyan"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(
            complete_style="bright_green",
            finished_style="bright_green",
            bar_width=40
        ),
        MofNCompleteColumn(),
        TaskProgressColumn(show_speed=True),
        TimeElapsedColumn(),
        console=console,
        transient=False
    )


def create_download_progress() -> Progress:
    """
    Creates a specialized progress bar for downloads.
    """
    return Progress(
        SpinnerColumn(spinner_style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(
            complete_style="bright_cyan",
            finished_style="bright_cyan", 
            bar_width=30
        ),
        TaskProgressColumn(show_speed=True),
        TextColumn("[progress.download]{task.fields[filename]}"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    )


def show_summary(
    operation: str,
    stats: Dict[str, Any],
    duration: datetime,
    details: Optional[str] = None,
) -> None:
    """
    Shows a professional summary of the completed operation with statistics.
    """
    # Create main summary table
    table = Table(box=box.ROUNDED, border_style="cyan", title_style="bold cyan")
    table.add_column("📊 Metric", style="bold cyan", width=25)
    table.add_column("📈 Value", style="bright_white", justify="right", width=20)

    # Add statistics rows with better formatting
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            if "rate" in key.lower() or "percentage" in key.lower():
                formatted_value = f"{value:.1f}%"
            elif "speed" in key.lower():
                formatted_value = f"{value:.2f} MB/s"
            else:
                formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        
        # Add emoji for specific metrics
        if "successful" in key.lower():
            emoji = "✅"
        elif "failed" in key.lower():
            emoji = "❌" 
        elif "total" in key.lower():
            emoji = "📦"
        elif "duration" in key.lower():
            emoji = "⏱️"
        else:
            emoji = "📋"
            
        table.add_row(f"{emoji} {key}", formatted_value)

    # Add duration with nice formatting
    if isinstance(duration, datetime):
        duration_str = str(duration)
    else:
        duration_str = str(duration)
    table.add_row("⏱️ Duration", duration_str)

    # Create panel with operation status
    success_rate = 0
    if "Successful" in stats and "Total Entries" in stats:
        total = stats["Total Entries"]
        successful = stats["Successful"] 
        if total > 0:
            success_rate = (successful / total) * 100

    if success_rate == 100:
        border_color = "bright_green"
        status_emoji = "🎉"
        status_text = "COMPLETED SUCCESSFULLY"
    elif success_rate >= 80:
        border_color = "bright_yellow"
        status_emoji = "⚠️"
        status_text = "COMPLETED WITH WARNINGS"
    else:
        border_color = "bright_red"
        status_emoji = "❌"
        status_text = "COMPLETED WITH ERRORS"

    panel = Panel(
        table, 
        title=f"[bold]{status_emoji} {operation.upper()} {status_text}",
        border_style=border_color,
        padding=(1, 2)
    )
    console.print(panel)

    # Show details if provided
    if details:
        detail_panel = Panel(
            details,
            title="[bold dim]Additional Details",
            border_style="dim",
            padding=(0, 1)
        )
        console.print(detail_panel)


def log_error(error_message: str, error: Optional[Exception] = None) -> None:
    """
    Displays a professional error message with optional exception details.
    """
    console.print(f"[bright_red]❌ ERROR:[/bright_red] {error_message}")
    if error:
        console.print(f"[dim bright_red]   Details: {str(error)}[/dim bright_red]")


def log_success(message: str) -> None:
    """
    Displays a professional success message.
    """
    console.print(f"[bright_green]✅ {message}[/bright_green]")


def log_warning(message: str) -> None:
    """
    Displays a professional warning message.
    """
    console.print(f"[bright_yellow]⚠️ WARNING:[/bright_yellow] {message}")


def print_header(text: str) -> None:
    """
    Prints a professional section header.
    """
    console.print()
    header_text = Text(f"━━━ {text.upper()} ━━━", style="bold cyan")
    console.print(Align.center(header_text))
    console.print()


def print_operation_start(operation: str, target: str = "") -> None:
    """
    Prints a professional operation start message.
    """
    text = Text()
    text.append("🚀 Starting: ", style="bright_cyan") 
    text.append(operation, style="bold white")
    if target:
        text.append(f" → {target}", style="dim white")
    
    console.print(Panel(
        text,
        border_style="bright_cyan",
        padding=(0, 1),
        box=box.ROUNDED
    ))


def print_error_details(title: str, details: Dict[str, Any]) -> None:
    """
    Prints error details in a professional formatted panel.
    """
    table = Table(box=box.ROUNDED, border_style="bright_red", show_header=False)
    table.add_column("Field", style="bold bright_red", width=20)
    table.add_column("Value", style="bright_white")

    for key, value in details.items():
        table.add_row(f"❌ {key}:", str(value))

    panel = Panel(
        table, 
        title=f"[bold bright_red]🚨 {title.upper()}[/bold bright_red]", 
        border_style="bright_red",
        padding=(1, 2)
    )
    console.print(panel)


def print_processing_status(
    current: int, total: int, item_name: str, status: str = "processing"
) -> None:
    """
    Prints current processing status with professional progress indicator.
    """
    percentage = (current / total) * 100 if total > 0 else 0
    status_icons = {
        "processing": "⚙️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
    }
    status_colors = {
        "processing": "bright_blue",
        "success": "bright_green",
        "error": "bright_red",
        "warning": "bright_yellow",
    }
    
    icon = status_icons.get(status, "•")
    color = status_colors.get(status, "white")
    
    console.print(
        f"[{color}]{icon} [{current}/{total}] ({percentage:.1f}%) {item_name}[/{color}]"
    )


def print_simple(message: str) -> None:
    """
    Prints a simple message without styling.
    """
    console.print(message)


def print_progress_line(current: int, total: int, name: str, status: str) -> None:
    """
    Prints a professional single line progress update.
    """
    if status == "success":
        console.print(f"[bright_green]✅[/bright_green] [{current:>3}/{total}] {name}")
    elif status == "error":
        console.print(f"[bright_red]❌[/bright_red] [{current:>3}/{total}] {name}")
    elif status == "warning":
        console.print(f"[bright_yellow]⚠️[/bright_yellow] [{current:>3}/{total}] {name}")
    else:
        console.print(f"[bright_blue]⚙️[/bright_blue] [{current:>3}/{total}] {name}")


def print_minimal_header(text: str) -> None:
    """
    Prints a minimal header for cleaner output.
    """
    console.print(f"\n[bold cyan]▸ {text}[/bold cyan]")


def print_config_summary(config: Dict[str, Any]) -> None:
    """
    Prints a professional configuration summary.
    """
    table = Table(box=box.ROUNDED, border_style="dim", title="Configuration Overview")
    table.add_column("Setting", style="bold dim")
    table.add_column("Value", style="bright_white")
    
    for key, value in config.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value[:3])
            if len(value) > 3:
                value_str += f" (+ {len(value) - 3} more)"
        else:
            value_str = str(value)
        table.add_row(key.replace("_", " ").title(), value_str)
    
    console.print(table)
    console.print()


def print_completion_message(operation: str, success: bool = True) -> None:
    """
    Prints a professional completion message.
    """
    if success:
        text = Text()
        text.append("🎉 ", style="bright_green")
        text.append("OPERATION COMPLETED SUCCESSFULLY", style="bold bright_green")
        text.append(f"\n{operation} finished without errors.", style="dim white")
        
        panel = Panel(
            Align.center(text),
            border_style="bright_green",
            box=box.DOUBLE,
            padding=(1, 2)
        )
    else:
        text = Text()
        text.append("❌ ", style="bright_red")
        text.append("OPERATION COMPLETED WITH ERRORS", style="bold bright_red")
        text.append(f"\n{operation} finished with some issues.", style="dim white")
        
        panel = Panel(
            Align.center(text),
            border_style="bright_red",
            box=box.DOUBLE,
            padding=(1, 2)
        )
    
    console.print(panel)
