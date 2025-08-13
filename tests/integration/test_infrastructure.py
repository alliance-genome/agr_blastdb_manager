"""
test_infrastructure.py

Test the testing infrastructure itself.
"""

import json
import tempfile
from pathlib import Path

import pytest


class TestTestInfrastructure:
    """Test the testing infrastructure components."""

    def test_fixtures_import(self):
        """Test that fixtures can be imported."""
        try:
            from .fixtures import SAMPLE_GLOBAL_CONFIG, SIMPLE_NUCLEOTIDE_FASTA
            assert SAMPLE_GLOBAL_CONFIG is not None
            assert SIMPLE_NUCLEOTIDE_FASTA is not None
        except ImportError:
            # Try alternative import
            from fixtures import SAMPLE_GLOBAL_CONFIG, SIMPLE_NUCLEOTIDE_FASTA
            assert SAMPLE_GLOBAL_CONFIG is not None
            assert SIMPLE_NUCLEOTIDE_FASTA is not None

    def test_temp_directory_fixture(self, temp_dir):
        """Test temporary directory fixture works."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_sample_config_fixture(self, sample_config_yaml):
        """Test sample configuration fixture."""
        assert "providers" in sample_config_yaml
        assert "WB" in sample_config_yaml["providers"]
        assert "SGD" in sample_config_yaml["providers"]

    def test_sample_database_config_fixture(self, sample_database_config):
        """Test sample database configuration fixture."""
        assert "databases" in sample_database_config
        assert len(sample_database_config["databases"]) == 2
        
        first_db = sample_database_config["databases"][0]
        assert "name" in first_db
        assert "uri" in first_db
        assert "md5" in first_db
        assert "seqtype" in first_db

    def test_sample_fasta_fixtures(self, sample_fasta_content, sample_fasta_with_parse_seqids):
        """Test FASTA content fixtures."""
        # Test standard FASTA
        assert sample_fasta_content.startswith(">seq1")
        assert "ATCGATCGATCG" in sample_fasta_content
        assert sample_fasta_content.count(">") == 3  # 3 sequences
        
        # Test parse_seqids FASTA
        assert sample_fasta_with_parse_seqids.startswith(">gi|")
        assert "|" in sample_fasta_with_parse_seqids
        assert sample_fasta_with_parse_seqids.count(">") == 2  # 2 sequences

    def test_config_files_fixture(self, config_files):
        """Test configuration files fixture."""
        assert "global" in config_files
        assert "database" in config_files
        
        # Test global config exists and is valid YAML
        global_config_path = config_files["global"]
        assert Path(global_config_path).exists()
        
        import yaml
        with open(global_config_path) as f:
            config = yaml.safe_load(f)
        assert "providers" in config
        
        # Test database config exists and is valid JSON
        db_config_path = config_files["database"]
        assert Path(db_config_path).exists()
        
        with open(db_config_path) as f:
            db_config = json.load(f)
        assert "databases" in db_config

    def test_fasta_file_fixture(self, fasta_file):
        """Test FASTA file fixture."""
        assert fasta_file.exists()
        content = fasta_file.read_text()
        assert content.startswith(">seq1")
        assert content.count(">") == 3

    def test_mock_fixtures(self, mock_http_response, mock_makeblastdb_success, mock_makeblastdb_failure):
        """Test mock fixtures."""
        # Test HTTP response mock
        assert mock_http_response.status_code == 200
        assert hasattr(mock_http_response, 'iter_content')
        
        # Test successful makeblastdb mock
        assert mock_makeblastdb_success.returncode == 0
        stdout, stderr = mock_makeblastdb_success.communicate()
        assert stdout == b"Success"
        
        # Test failed makeblastdb mock
        assert mock_makeblastdb_failure.returncode == 1
        stdout, stderr = mock_makeblastdb_failure.communicate()
        assert stderr == b"Error: makeblastdb failed"


class TestBasicPythonFunctionality:
    """Test basic Python functionality that our tests rely on."""

    def test_pathlib_operations(self):
        """Test pathlib operations work correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            
            # Test directory creation
            test_dir = base_path / "test_dir"
            test_dir.mkdir()
            assert test_dir.exists()
            assert test_dir.is_dir()
            
            # Test file creation
            test_file = test_dir / "test.txt"
            test_file.write_text("test content")
            assert test_file.exists()
            assert test_file.read_text() == "test content"
            
            # Test nested directory creation
            nested_dir = base_path / "nested" / "deep" / "structure"
            nested_dir.mkdir(parents=True)
            assert nested_dir.exists()

    def test_json_operations(self):
        """Test JSON operations work correctly."""
        test_data = {
            "databases": [
                {"name": "test_db", "uri": "http://example.com/test.fa", "md5": "abc123"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            json_file = f.name
        
        # Read it back
        with open(json_file) as f:
            loaded_data = json.load(f)
        
        assert loaded_data == test_data
        assert len(loaded_data["databases"]) == 1
        assert loaded_data["databases"][0]["name"] == "test_db"
        
        # Clean up
        Path(json_file).unlink()

    def test_yaml_operations(self):
        """Test YAML operations work correctly."""
        test_data = {
            "providers": {
                "WB": {"dev": "test.json"},
                "SGD": {"prod": "test2.json"}
            }
        }
        
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            yaml_file = f.name
        
        # Read it back
        with open(yaml_file) as f:
            loaded_data = yaml.safe_load(f)
        
        assert loaded_data == test_data
        assert "WB" in loaded_data["providers"]
        assert "SGD" in loaded_data["providers"]
        
        # Clean up
        Path(yaml_file).unlink()

    def test_mock_functionality(self):
        """Test that mocking works correctly."""
        from unittest.mock import MagicMock, patch, mock_open
        
        # Test basic mock
        mock_obj = MagicMock()
        mock_obj.method.return_value = "test_result"
        
        result = mock_obj.method()
        assert result == "test_result"
        mock_obj.method.assert_called_once()
        
        # Test patching
        with patch('builtins.open', mock_open(read_data='test file content')) as mock_file:
            with open('test.txt', 'r') as f:
                content = f.read()
            
            assert content == 'test file content'
            mock_file.assert_called_once_with('test.txt', 'r')

    def test_pytest_features(self):
        """Test pytest features work correctly."""
        # Test assertions
        assert True
        assert 1 == 1
        assert "test" in "testing"
        
        # Test exception testing
        with pytest.raises(ValueError):
            raise ValueError("test error")
        
        with pytest.raises(FileNotFoundError):
            open("nonexistent_file.txt", "r")
        
        # Test approximate assertions
        assert 1.0 == pytest.approx(0.999, abs=0.01)


class TestSequenceHandling:
    """Test sequence handling functionality independent of main code."""

    def test_fasta_parsing(self):
        """Test basic FASTA parsing logic."""
        fasta_content = """>seq1 description
ATGCGATCGATCG
>seq2 another sequence
GCTAGCTAGCTA
>seq3
TTAATTAATTAA
"""
        
        # Count sequences
        sequence_count = fasta_content.count(">")
        assert sequence_count == 3
        
        # Check for parse_seqids requirement
        needs_parse_seqids = "|" in fasta_content and "gi|" in fasta_content
        assert needs_parse_seqids is False
        
        # Test with parse_seqids content
        parse_seqids_content = """>gi|123456|ref|NM_001234.1| test sequence
ATGCGATCGATCG
>gi|789012|ref|NM_005678.2| another sequence
GCTAGCTAGCTA
"""
        
        needs_parse_seqids = "|" in parse_seqids_content and "gi|" in parse_seqids_content
        assert needs_parse_seqids is True

    def test_configuration_validation(self):
        """Test configuration validation logic."""
        # Valid configuration
        valid_config = {
            "databases": [
                {
                    "name": "test_db",
                    "uri": "http://example.com/test.fa",
                    "md5": "abc123def456",
                    "seqtype": "nucl",
                    "blast_title": "Test Database",
                    "taxonomy": "12345"
                }
            ]
        }
        
        # Check required fields
        db = valid_config["databases"][0]
        required_fields = ["name", "uri", "md5", "seqtype"]
        for field in required_fields:
            assert field in db
        
        # Test invalid configuration
        invalid_config = {"databases": [{"name": "incomplete"}]}
        db = invalid_config["databases"][0]
        
        missing_fields = []
        for field in required_fields:
            if field not in db:
                missing_fields.append(field)
        
        assert len(missing_fields) == 3  # uri, md5, seqtype missing

    def test_mod_specific_logic(self):
        """Test MOD-specific handling logic."""
        # Test ZFIN special case
        mod_code = "ZFIN"
        skip_md5_validation = (mod_code == "ZFIN")
        use_parse_seqids = (mod_code != "ZFIN")
        
        assert skip_md5_validation is True
        assert use_parse_seqids is False
        
        # Test other MODs (mandatory parse_seqids)
        for mod in ["WB", "SGD", "FB", "RGD", "XB"]:
            skip_md5_validation = (mod == "ZFIN")
            use_parse_seqids = (mod != "ZFIN")
            
            assert skip_md5_validation is False
            assert use_parse_seqids is True  # Mandatory for all non-ZFIN MODs