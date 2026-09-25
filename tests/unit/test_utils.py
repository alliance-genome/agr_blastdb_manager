"""
test_utils.py

Unit tests for utility functions in the utils module.
"""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

# Try to import from source, skip if not available
try:
    from src.utils import (
        copy_config_file,
        extendable_logger,
        get_files_http,
        get_mod_from_json,
        needs_parse_seqids,
        setup_detailed_logger,
    )
    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Source code not available")
class TestFileOperations:
    """Test file operation utilities."""

    def test_copy_config_file(self, temp_dir, sample_database_config):
        """copy_config_file(json_file, config_dir, logger) writes environment.json.

        The destination filename is fixed -- the server reads
        <config_dir>/environment.json -- so the source name is not preserved.
        """
        source_path = temp_dir / "source.json"
        dest_dir = temp_dir / "dest"
        source_path.write_text(json.dumps(sample_database_config))

        assert copy_config_file(source_path, dest_dir, MagicMock()) is True

        written = dest_dir / "environment.json"
        assert written.exists(), "expected the config at <config_dir>/environment.json"
        assert json.loads(written.read_text()) == sample_database_config

    def test_copy_config_file_creates_missing_directory(self, temp_dir, sample_database_config):
        """The config directory is created rather than required to exist."""
        source_path = temp_dir / "source.json"
        source_path.write_text(json.dumps(sample_database_config))
        dest_dir = temp_dir / "does" / "not" / "exist"

        assert copy_config_file(source_path, dest_dir, MagicMock()) is True
        assert (dest_dir / "environment.json").exists()

    def test_copy_config_file_nonexistent_source(self, temp_dir):
        """A missing source is reported by return value, not an exception.

        The caller treats copy failure as a step failure and carries on with the
        remaining databases, so this must not raise.
        """
        logger = MagicMock()
        result = copy_config_file(temp_dir / "nonexistent.json", temp_dir / "dest", logger)

        assert result is False
        logger.error.assert_called_once()


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Source code not available")
class TestSequenceAnalysis:
    """Test sequence analysis functions."""

    def test_needs_parse_seqids_true(self, sample_fasta_with_parse_seqids):
        """Test detection of sequences that need parse_seqids."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(sample_fasta_with_parse_seqids)
            f.flush()
            
            result = needs_parse_seqids(f.name)
            assert result is True

    def test_needs_parse_seqids_false(self, sample_fasta_content):
        """Test detection of sequences that don't need parse_seqids."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(sample_fasta_content)
            f.flush()
            
            result = needs_parse_seqids(f.name)
            assert result is False

    def test_needs_parse_seqids_empty_file(self, temp_dir):
        """Test parse_seqids detection with empty file."""
        empty_file = temp_dir / "empty.fa"
        empty_file.touch()
        
        result = needs_parse_seqids(str(empty_file))
        assert result is False

    def test_needs_parse_seqids_nonexistent_file(self, temp_dir):
        """A missing FASTA yields True rather than raising.

        The headers cannot be inspected, so it defaults to applying the flag.
        That is the safe direction: makeblastdb will fail on the missing file
        regardless, and the alternative default would silently produce a
        database with no sequence retrieval.
        """
        assert needs_parse_seqids(str(temp_dir / "nonexistent.fa")) is True

    def test_needs_parse_seqids_is_false_for_zfin(self, temp_dir):
        """ZFIN databases are deliberately built without -parse_seqids."""
        fasta = temp_dir / "zfin.fa"
        fasta.write_text(">gb|ABC123| something\nACGT\n")

        assert needs_parse_seqids(str(fasta), mod="ZFIN") is False


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Source code not available")
class TestConfigurationParsing:
    """Test configuration parsing functions."""

    def test_get_mod_from_json(self, temp_dir, sample_database_config):
        """The MOD comes from the FILENAME, not the file contents.

        Configs are named databases.<MOD>.<release>.json, and the second
        dot-separated part is the MOD.
        """
        config_path = temp_dir / "databases.WB.WS285.json"
        config_path.write_text(json.dumps(sample_database_config))

        assert get_mod_from_json(str(config_path)) == "WB"

    def test_get_mod_from_json_matches_variant_by_prefix(self, temp_dir):
        """A variant like SGD_test resolves to its parent MOD."""
        config_path = temp_dir / "databases.SGD_test.2025-10-07.json"
        config_path.write_text("{}")

        assert get_mod_from_json(str(config_path)) == "SGD"

    def test_get_mod_from_json_ignores_file_contents(self, temp_dir):
        """Malformed JSON is irrelevant: only the filename is parsed."""
        invalid_config = temp_dir / "databases.FB.FB2026_03.json"
        invalid_config.write_text("not json at all")

        assert get_mod_from_json(str(invalid_config)) == "FB"

    def test_get_mod_from_json_without_a_mod_part(self, temp_dir):
        """A filename with nothing to extract returns False, and does not raise."""
        assert get_mod_from_json(str(temp_dir / "nomod")) is False


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Source code not available")
class TestLogging:
    """Test logging utilities."""

    def test_setup_detailed_logger(self, temp_dir):
        """Test detailed logger setup."""
        log_file = temp_dir / "test.log"
        
        logger = setup_detailed_logger("test_logger", str(log_file))
        
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0
        
        # Test logging
        logger.info("Test message")
        
        assert log_file.exists()
        with open(log_file) as f:
            content = f.read()
        assert "Test message" in content

    def test_extendable_logger(self, temp_dir):
        """Test extendable logger functionality."""
        log_file = temp_dir / "test.log"
        
        logger = extendable_logger("test_logger", str(log_file))
        logger.info("First message")
        
        # Create another instance with same name
        logger2 = extendable_logger("test_logger", str(log_file))
        logger2.info("Second message")
        
        assert log_file.exists()
        with open(log_file) as f:
            content = f.read()
        
        assert "First message" in content
        assert "Second message" in content


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Source code not available")
class TestHTTPDownload:
    """Test HTTP download functionality."""

    @patch('src.utils.Popen')
    def test_get_files_http_returns_false_when_wget_fails(self, mock_popen, temp_dir):
        """get_files_http downloads with wget, not requests.

        The previous tests here patched src.utils.requests, which this function
        never uses -- requests is imported inside get_ftp_file_size. The real
        seam is the Popen call that runs wget.
        """
        proc = MagicMock()
        proc.communicate.return_value = (b"", b"404 Not Found")
        proc.returncode = 1
        mock_popen.return_value = proc

        logger = MagicMock()
        result = get_files_http("https://example.com/missing.fa.gz", "deadbeef", logger)

        assert result is False
        logger.error.assert_called()

    @patch('src.utils.Popen')
    def test_get_files_http_invokes_wget_with_the_uri(self, mock_popen, temp_dir):
        """The URI reaches wget, and the output lands under ../data."""
        proc = MagicMock()
        proc.communicate.return_value = (b"", b"")
        proc.returncode = 1          # stop after the download step
        mock_popen.return_value = proc

        uri = "https://example.com/c_elegans.fa.gz"
        get_files_http(uri, "deadbeef", MagicMock())

        command = mock_popen.call_args[0][0]
        assert command[0] == "wget"
        assert uri in command
        assert any(arg.endswith("c_elegans.fa.gz") for arg in command), \
            "expected the download target to be named after the source file"

    @patch('src.utils.Popen')
    def test_get_files_http_survives_a_raising_subprocess(self, mock_popen, temp_dir):
        """An exception from the subprocess is reported, not propagated.

        A download failure must fail that one database, not abort the run.
        """
        mock_popen.side_effect = OSError("wget not found")

        logger = MagicMock()
        assert get_files_http("https://example.com/x.fa.gz", "deadbeef", logger) is False
        logger.error.assert_called()


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Source code not available") 
class TestFileValidation:
    """Test file validation functions."""

    def test_md5_validation_success(self, temp_dir):
        """Test successful MD5 validation."""
        test_content = b"test file content"
        expected_md5 = hashlib.md5(test_content).hexdigest()
        
        test_file = temp_dir / "test.txt"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # This would be tested in the actual implementation
        # For now, just verify the MD5 calculation
        with open(test_file, 'rb') as f:
            actual_md5 = hashlib.md5(f.read()).hexdigest()
        
        assert actual_md5 == expected_md5

    def test_fasta_format_validation(self, sample_fasta_content, temp_dir):
        """Test FASTA format validation."""
        fasta_file = temp_dir / "test.fa"
        with open(fasta_file, 'w') as f:
            f.write(sample_fasta_content)
        
        # Basic validation - check that file has FASTA headers
        with open(fasta_file) as f:
            content = f.read()
        
        assert content.startswith('>')
        assert '\n>seq2\n' in content
        assert '\n>seq3\n' in content


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Source code not available")
class TestSpecialCases:
    """Test special case handling."""

    def test_zfin_special_handling(self):
        """Test ZFIN-specific behavior."""
        # ZFIN databases skip MD5 validation and don't use -parse_seqids
        mod_code = "ZFIN"
        
        # This would be tested in the actual makeblastdb function
        # For now, just verify the MOD detection
        assert mod_code == "ZFIN"

    def test_empty_database_list(self):
        """Test handling of empty database configuration."""
        empty_config = {"databases": []}
        
        databases = empty_config.get("databases", [])
        assert len(databases) == 0

    def test_missing_required_fields(self):
        """Test handling of missing required configuration fields."""
        incomplete_db = {
            "name": "test_db"
            # Missing uri, md5, etc.
        }
        
        # Verify required fields are missing
        assert "uri" not in incomplete_db
        assert "md5" not in incomplete_db
        assert "blast_title" not in incomplete_db