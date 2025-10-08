"""
Unit tests for the validation module.

Tests the database validation functionality including:
- Conserved sequence library
- MOD-specific sequence library
- BLAST validation engine
- Database discovery
- Result reporting
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.validation import (
    CONSERVED_SEQUENCES,
    MOD_SPECIFIC_SEQUENCES,
    DatabaseValidator,
    ValidationResult,
)


class TestConservedSequences:
    """Test the conserved sequence library."""

    def test_conserved_sequences_exist(self):
        """Test that conserved sequences are defined."""
        assert len(CONSERVED_SEQUENCES) == 8
        expected_keys = [
            "18S_rRNA",
            "28S_rRNA",
            "COI_mt",
            "actin",
            "gapdh",
            "U6_snRNA",
            "histone_H3",
            "EF1a",
        ]
        for key in expected_keys:
            assert key in CONSERVED_SEQUENCES

    def test_conserved_sequences_format(self):
        """Test that conserved sequences are properly formatted FASTA."""
        for name, seq in CONSERVED_SEQUENCES.items():
            assert seq.startswith(">"), f"{name} should start with >"
            assert "\n" in seq, f"{name} should contain newline"
            lines = seq.split("\n")
            assert len(lines) >= 2, f"{name} should have header and sequence"


class TestModSpecificSequences:
    """Test the MOD-specific sequence library."""

    def test_all_mods_have_sequences(self):
        """Test that all MODs have specific sequences."""
        expected_mods = ["FB", "WB", "SGD", "ZFIN", "RGD", "XB"]
        for mod in expected_mods:
            assert mod in MOD_SPECIFIC_SEQUENCES
            assert len(MOD_SPECIFIC_SEQUENCES[mod]) >= 2

    def test_mod_sequences_format(self):
        """Test that MOD-specific sequences are properly formatted."""
        for mod, sequences in MOD_SPECIFIC_SEQUENCES.items():
            for name, seq in sequences.items():
                assert seq.startswith(">"), f"{mod}/{name} should start with >"
                assert "\n" in seq, f"{mod}/{name} should contain newline"


class TestValidationResult:
    """Test the ValidationResult class."""

    def test_initialization(self):
        """Test ValidationResult initialization."""
        result = ValidationResult("test_db", "/path/to/db", "FB", "blastn")
        assert result.db_name == "test_db"
        assert result.db_path == "/path/to/db"
        assert result.mod == "FB"
        assert result.blast_type == "blastn"
        assert result.conserved_hits == 0
        assert result.specific_hits == 0
        assert result.total_hits == 0
        assert result.test_count == 0
        assert result.success is False
        assert result.error_message is None
        assert result.hit_details == []

    def test_add_hit(self):
        """Test adding hit information."""
        result = ValidationResult("test_db", "/path/to/db", "FB")
        result.add_hit("18S_rRNA", 5, 98.5)

        assert len(result.hit_details) == 1
        assert result.hit_details[0]["sequence"] == "18S_rRNA"
        assert result.hit_details[0]["hits"] == 5
        assert result.hit_details[0]["identity"] == 98.5
        assert result.total_hits == 5

    def test_get_hit_rate_no_tests(self):
        """Test hit rate calculation with no tests."""
        result = ValidationResult("test_db", "/path/to/db", "FB")
        assert result.get_hit_rate() == 0.0

    def test_get_hit_rate_with_tests(self):
        """Test hit rate calculation with tests."""
        result = ValidationResult("test_db", "/path/to/db", "FB")
        result.test_count = 10
        result.add_hit("18S_rRNA", 5, 98.5)
        result.add_hit("actin", 3, 95.0)

        # 2 sequences with hits out of 10 tests = 20%
        assert result.get_hit_rate() == 20.0


class TestDatabaseValidator:
    """Test the DatabaseValidator class."""

    def test_initialization(self):
        """Test DatabaseValidator initialization."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        assert validator.logger == logger
        assert validator.evalue == "10"
        assert validator.word_size == "7"
        assert validator.timeout == 30
        assert validator.num_threads == 2

    def test_initialization_custom_params(self):
        """Test DatabaseValidator initialization with custom parameters."""
        logger = MagicMock()
        validator = DatabaseValidator(
            logger, evalue="0.001", word_size="11", timeout=60, num_threads=4
        )

        assert validator.evalue == "0.001"
        assert validator.word_size == "11"
        assert validator.timeout == 60
        assert validator.num_threads == 4

    def test_discover_databases_nonexistent_path(self):
        """Test database discovery with non-existent path."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        databases = validator.discover_databases("/nonexistent/path")
        assert databases == {}

    def test_discover_databases_empty_directory(self):
        """Test database discovery with empty directory."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        with tempfile.TemporaryDirectory() as tmpdir:
            databases = validator.discover_databases(tmpdir)
            assert databases == {}

    def test_discover_databases_with_databases(self):
        """Test database discovery with mock databases."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock database structure
            fb_dir = Path(tmpdir) / "FB" / "dev" / "databases" / "test_db"
            fb_dir.mkdir(parents=True)

            # Create mock .nin file
            nin_file = fb_dir / "test.nin"
            nin_file.touch()

            databases = validator.discover_databases(tmpdir)

            assert "FB" in databases
            assert len(databases["FB"]) == 1
            assert databases["FB"][0][0] == "test_db"

    def test_discover_databases_with_mod_filter(self):
        """Test database discovery with MOD filter."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create databases for multiple MODs
            fb_dir = Path(tmpdir) / "FB" / "test_db"
            fb_dir.mkdir(parents=True)
            (fb_dir / "test.nin").touch()

            wb_dir = Path(tmpdir) / "WB" / "test_db"
            wb_dir.mkdir(parents=True)
            (wb_dir / "test.nin").touch()

            # Filter for FB only
            databases = validator.discover_databases(tmpdir, mod="FB")

            assert "FB" in databases
            assert "WB" not in databases

    @patch("src.validation.subprocess.run")
    def test_run_blast_test_success(self, mock_run):
        """Test successful BLAST test."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock successful BLAST output
        mock_result = Mock()
        mock_result.stdout = "query1\tsubject1\t98.5\t100\t1e-50\t200\n"
        mock_run.return_value = mock_result

        success, hits, identity = validator.run_blast_test(
            ">test\nATGC", "/path/to/db", "blastn"
        )

        assert success is True
        assert hits == 1
        assert identity == 98.5

    @patch("src.validation.subprocess.run")
    def test_run_blast_test_no_hits(self, mock_run):
        """Test BLAST test with no hits."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock empty BLAST output
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        success, hits, identity = validator.run_blast_test(
            ">test\nATGC", "/path/to/db", "blastn"
        )

        assert success is False
        assert hits == 0
        assert identity == 0.0

    @patch("src.validation.subprocess.run")
    def test_run_blast_test_timeout(self, mock_run):
        """Test BLAST test with timeout."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock timeout
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("blastn", 30)

        success, hits, identity = validator.run_blast_test(
            ">test\nATGC", "/path/to/db", "blastn"
        )

        assert success is False
        assert hits == 0
        assert identity == 0.0

    @patch("src.validation.subprocess.run")
    def test_run_blast_test_multiple_hits(self, mock_run):
        """Test BLAST test with multiple hits."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock multiple hits
        mock_result = Mock()
        mock_result.stdout = (
            "query1\tsubject1\t98.5\t100\t1e-50\t200\n"
            "query1\tsubject2\t95.0\t100\t1e-40\t180\n"
            "query1\tsubject3\t92.0\t100\t1e-30\t160\n"
        )
        mock_run.return_value = mock_result

        success, hits, identity = validator.run_blast_test(
            ">test\nATGC", "/path/to/db", "blastn"
        )

        assert success is True
        assert hits == 3
        assert identity == 98.5  # Best identity

    @patch.object(DatabaseValidator, "run_blast_test")
    def test_validate_database(self, mock_blast):
        """Test database validation."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock BLAST returning hits for some sequences
        def blast_side_effect(seq, db, blast_type):
            if "18S_rRNA" in seq:
                return True, 5, 98.5
            elif "actin" in seq:
                return True, 3, 95.0
            else:
                return False, 0, 0.0

        mock_blast.side_effect = blast_side_effect

        result = validator.validate_database("test_db", "/path/to/db", "FB")

        assert result.db_name == "test_db"
        assert result.success is True
        assert result.conserved_hits > 0
        assert result.total_hits > 0
        assert len(result.hit_details) >= 2

    @patch.object(DatabaseValidator, "run_blast_test")
    def test_validate_database_no_hits(self, mock_blast):
        """Test database validation with no hits."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock BLAST returning no hits
        mock_blast.return_value = (False, 0, 0.0)

        result = validator.validate_database("test_db", "/path/to/db", "FB")

        assert result.db_name == "test_db"
        assert result.success is False
        assert result.conserved_hits == 0
        assert result.total_hits == 0

    @patch.object(DatabaseValidator, "run_blast_test")
    def test_validate_database_with_mod_specific(self, mock_blast):
        """Test database validation includes MOD-specific sequences."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Count how many sequences are tested
        tested_sequences = []

        def blast_side_effect(seq, db, blast_type):
            tested_sequences.append(seq)
            return True, 1, 90.0

        mock_blast.side_effect = blast_side_effect

        result = validator.validate_database("test_db", "/path/to/db", "FB")

        # Should test conserved sequences + FB-specific sequences
        expected_tests = len(CONSERVED_SEQUENCES) + len(MOD_SPECIFIC_SEQUENCES["FB"])
        assert result.test_count == expected_tests

    @patch.object(DatabaseValidator, "validate_database")
    @patch.object(DatabaseValidator, "discover_databases")
    def test_validate_mod_databases(self, mock_discover, mock_validate):
        """Test validating all databases for a MOD."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock discovery
        mock_discover.return_value = {"FB": [("db1", "/path/db1"), ("db2", "/path/db2")]}

        # Mock validation results
        result1 = ValidationResult("db1", "/path/db1", "FB")
        result1.success = True
        result1.conserved_hits = 10
        result1.total_hits = 15

        result2 = ValidationResult("db2", "/path/db2", "FB")
        result2.success = False
        result2.conserved_hits = 0
        result2.total_hits = 0

        mock_validate.side_effect = [result1, result2]

        stats = validator.validate_mod_databases("FB", [("db1", "/path/db1"), ("db2", "/path/db2")])

        assert stats["total"] == 2
        assert stats["passed"] == 1
        assert stats["failed"] == 1
        assert stats["total_hits"] == 15
        assert stats["databases_with_conserved"] == 1


class TestValidationIntegration:
    """Integration tests for validation functionality."""

    @patch.object(DatabaseValidator, "discover_databases")
    @patch.object(DatabaseValidator, "validate_mod_databases")
    def test_validate_all(self, mock_validate_mod, mock_discover):
        """Test validating all MODs."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock discovery
        mock_discover.return_value = {
            "FB": [("db1", "/path/db1")],
            "WB": [("db2", "/path/db2")],
        }

        # Mock validation
        fb_stats = {"total": 1, "passed": 1, "failed": 0}
        wb_stats = {"total": 1, "passed": 1, "failed": 0}
        mock_validate_mod.side_effect = [fb_stats, wb_stats]

        results = validator.validate_all("/base/path")

        assert len(results) == 2
        assert "FB" in results
        assert "WB" in results

    @patch.object(DatabaseValidator, "discover_databases")
    def test_validate_all_no_databases(self, mock_discover):
        """Test validation with no databases found."""
        logger = MagicMock()
        validator = DatabaseValidator(logger)

        # Mock no databases found
        mock_discover.return_value = {}

        results = validator.validate_all("/base/path")

        assert results == {}
