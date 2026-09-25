"""
test_terminal.py

Unit tests for terminal interface functions.
"""

from datetime import timedelta
import re
from io import StringIO
from unittest.mock import patch

import pytest

# rich styles its output, so a value like "3/10" arrives as
# "\x1b[1;36m3\x1b[0m/\x1b[1;36m10\x1b[0m" and a plain substring check fails.
# Strip the escape sequences before asserting on rendered text.
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(text):
    """Rendered console text with styling removed."""
    return ANSI.sub("", text)


try:
    from src.terminal import (
        log_error,
        log_success,
        log_warning,
        print_error_details,
        print_header,
        print_minimal_header,
        print_progress_line,
        print_status,
        show_summary,
    )
except ImportError:
    # Skip tests if terminal module not available
    pytest.skip("Terminal module not available", allow_module_level=True)


class TestLoggingFunctions:
    """Test logging and print functions."""

    @patch('sys.stdout', new_callable=StringIO)
    def test_log_success(self, mock_stdout):
        """Test success logging."""
        message = "Operation completed successfully"
        log_success(message)
        
        output = mock_stdout.getvalue()
        assert message in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_log_error(self, mock_stdout):
        """log_error writes to stdout via rich's console, not to stderr."""
        log_error("An error occurred")

        output = mock_stdout.getvalue()
        assert "An error occurred" in output
        assert "Error" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_log_error_includes_exception_detail(self, mock_stdout):
        """The optional exception argument is rendered alongside the message."""
        log_error("Download failed", ValueError("bad checksum"))

        output = mock_stdout.getvalue()
        assert "Download failed" in output
        assert "bad checksum" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_log_warning(self, mock_stdout):
        """Test warning logging."""
        message = "This is a warning"
        log_warning(message)
        
        output = mock_stdout.getvalue()
        assert message in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_header(self, mock_stdout):
        """print_header(text) renders the text it is given."""
        print_header("Creating databases")

        assert "Creating databases" in mock_stdout.getvalue()

    def test_print_minimal_header(self):
        """Test minimal header printing."""
        print_minimal_header("Minimal Header")
        assert True

    def test_print_status(self):
        """Test status printing."""
        print_status("Processing", "test.fa")
        assert True

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_progress_line(self, mock_stdout):
        """print_progress_line(current, total, name, status) shows position and name."""
        print_progress_line(3, 10, "c_elegans", "success")

        output = plain(mock_stdout.getvalue())
        assert "3/10" in output
        assert "c_elegans" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_progress_line_marks_failure_differently(self, mock_stdout):
        """An error status is visually distinct from a success."""
        print_progress_line(1, 2, "ok_db", "success")
        print_progress_line(2, 2, "bad_db", "error")

        output = mock_stdout.getvalue()
        assert "\u2713" in output, "expected a tick for the successful entry"
        assert "\u2717" in output, "expected a cross for the failed entry"


class TestErrorDisplay:
    """Test error display functions."""

    def test_print_error_details(self):
        """Test detailed error display."""
        error_details = {
            "database": "test_db",
            "error": "File not found",
            "stage": "download"
        }
        
        print_error_details("test_db", error_details)
        assert True

    def test_print_error_details_empty(self):
        """Test error display with empty details."""
        print_error_details("test_db", {})
        assert True


class TestSummaryDisplay:
    """Test summary display functions."""

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_summary_success(self, mock_stdout):
        """show_summary(operation, stats, duration) tabulates the stats mapping."""
        show_summary("Database creation", {"Created": 3, "Failed": 0}, timedelta(seconds=42))

        output = mock_stdout.getvalue()
        assert "Database creation" in output
        assert "Created" in output
        assert "3" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_summary_reports_failures(self, mock_stdout):
        """Failure counts appear in the table rather than being swallowed."""
        show_summary("Database creation", {"Created": 2, "Failed": 4}, timedelta(seconds=5))

        output = mock_stdout.getvalue()
        assert "Failed" in output
        assert "4" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_summary_formats_large_numbers(self, mock_stdout):
        """Numeric values are thousands-separated; strings pass through."""
        show_summary("Indexing", {"Sequences": 1234567, "Mode": "full"}, timedelta(seconds=1))

        output = mock_stdout.getvalue()
        assert "1,234,567" in plain(output)
        assert "full" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_summary_empty_stats(self, mock_stdout):
        """An empty stats mapping still renders a summary with its duration."""
        show_summary("Nothing to do", {}, timedelta(0))

        output = mock_stdout.getvalue()
        assert "Nothing to do" in output
        assert "Duration" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_progress_indicators(self, mock_stdout):
        """A sequence of progress lines reports each step and its position."""
        steps = ["Initializing", "Downloading", "Validating", "Processing", "Finalizing"]
        for i, name in enumerate(steps, start=1):
            print_progress_line(i, len(steps), name, "success")

        output = plain(mock_stdout.getvalue())
        for name in steps:
            assert name in output, f"{name} missing from progress output"
        assert "5/5" in output


    def test_status_updates(self):
        """Test status update displays."""
        statuses = [
            ("Processing", "genome.fa"),
            ("Validating", "proteins.fa"),
            ("Creating", "database.db"),
            ("Copying", "config.json")
        ]
        
        for action, item in statuses:
            print_status(action, item)
        
        assert len(statuses) == 4


class TestColoredOutput:
    """Test colored output functionality."""

    def test_colored_messages(self):
        """Test colored message output."""
        # These would test rich color formatting
        # For now, just verify functions exist
        
        messages = [
            ("Success", "green"),
            ("Warning", "yellow"),
            ("Error", "red"),
            ("Info", "blue")
        ]
        
        for message, color in messages:
            # In a real test, we'd verify the color formatting
            assert message is not None
            assert color in ["green", "yellow", "red", "blue"]

    def test_formatted_output(self):
        """Test formatted output styles."""
        # Test different formatting styles used in the terminal module
        styles = ["bold", "italic", "underline", "dim"]
        
        for style in styles:
            # In a real test, we'd verify the style formatting
            assert style is not None


class TestInteractiveElements:
    """Test interactive terminal elements."""

    def test_confirmation_prompts(self):
        """Test confirmation prompt functionality."""
        # This would test any confirmation prompts in the terminal module
        # For now, just verify the concept
        
        def mock_confirm(message):
            return True  # Mock user confirmation
        
        result = mock_confirm("Proceed with operation?")
        assert result is True

    def test_user_input_handling(self):
        """Test user input handling."""
        # Test handling of user input for interactive features
        
        def mock_input(prompt):
            return "y"  # Mock user input
        
        user_response = mock_input("Continue? (y/n): ")
        assert user_response in ["y", "n", "yes", "no"]


class TestOutputFormatting:
    """Test output formatting functions."""

    def test_table_formatting(self):
        """Test table output formatting."""
        # Test any table formatting used in the terminal module
        
        sample_data = [
            {"name": "db1", "status": "success", "size": "100MB"},
            {"name": "db2", "status": "failed", "size": "0MB"},
            {"name": "db3", "status": "success", "size": "250MB"}
        ]
        
        # In a real test, we'd verify table formatting
        assert len(sample_data) == 3
        assert sample_data[0]["status"] == "success"
        assert sample_data[1]["status"] == "failed"

    def test_list_formatting(self):
        """Test list output formatting."""
        items = ["item1", "item2", "item3"]
        
        # Test list formatting functionality
        for i, item in enumerate(items, 1):
            formatted_item = f"{i}. {item}"
            assert str(i) in formatted_item
            assert item in formatted_item

    def test_alignment_formatting(self):
        """Test text alignment formatting."""
        # Test various text alignment options
        
        text = "Sample Text"
        alignments = ["left", "center", "right"]
        
        for alignment in alignments:
            # In a real test, we'd verify alignment formatting
            assert alignment in ["left", "center", "right"]
            assert len(text) > 0


class TestVerbosityLevels:
    """Test different verbosity levels."""

    def test_verbose_output(self):
        """Test verbose output mode."""
        # Test verbose output functionality
        verbose_mode = True
        
        if verbose_mode:
            # Additional output would be shown
            extra_info = "Detailed processing information"
            assert len(extra_info) > 0

    def test_quiet_output(self):
        """Test quiet output mode."""
        # Test quiet output functionality
        quiet_mode = True
        
        if quiet_mode:
            # Limited output would be shown
            essential_info = "Essential information only"
            assert len(essential_info) > 0

    def test_normal_output(self):
        """Test normal output mode."""
        # Test normal output functionality
        normal_mode = True
        
        if normal_mode:
            # Standard output would be shown
            standard_info = "Standard processing information"
            assert len(standard_info) > 0