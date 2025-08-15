"""
conftest.py

Pytest configuration file with shared fixtures for the AGR BLAST DB Manager tests.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config_yaml():
    """Sample global YAML configuration."""
    return {
        "providers": {
            "WB": {
                "dev": "conf/WB/databases.WB.WS285.json",
                "prod": "conf/WB/databases.WB.WS286.json"
            },
            "SGD": {
                "dev": "conf/SGD/databases.SGD.dev.json",
                "prod": "conf/SGD/databases.SGD.prod.json"
            }
        }
    }


@pytest.fixture
def sample_database_config():
    """Sample database configuration JSON."""
    return {
        "databases": [
            {
                "name": "test_genome",
                "uri": "https://example.com/test_genome.fa.gz",
                "md5": "1234567890abcdef",
                "blast_title": "Test Genome Database",
                "taxonomy": "12345",
                "seqtype": "nucl",
                "gbrowse_moby": {
                    "data_source": "test_ds",
                    "organism": "test_org"
                }
            },
            {
                "name": "test_proteins",
                "uri": "https://example.com/test_proteins.fa.gz",
                "md5": "abcdef1234567890",
                "blast_title": "Test Protein Database",
                "taxonomy": "12345",
                "seqtype": "prot"
            }
        ]
    }


@pytest.fixture
def sample_fasta_content():
    """Sample FASTA content for testing."""
    return """>seq1
ATCGATCGATCG
>seq2
GCTAGCTAGCTA
>seq3
TTAATTAATTAA
"""


@pytest.fixture
def sample_fasta_with_parse_seqids():
    """Sample FASTA content that requires parse_seqids."""
    return """>gi|123456|ref|NM_001234.1| test sequence 1
ATCGATCGATCGATCGATCG
>gi|789012|ref|NM_005678.2| test sequence 2
GCTAGCTAGCTAGCTAGCTA
"""


@pytest.fixture
def mock_ftp_response():
    """Mock FTP response data."""
    return MagicMock()


@pytest.fixture
def mock_http_response():
    """Mock HTTP response for file downloads."""
    response = MagicMock()
    response.status_code = 200
    response.iter_content.return_value = [b"test content"]
    response.headers = {"content-length": "12"}
    return response


@pytest.fixture
def mock_makeblastdb_success():
    """Mock successful makeblastdb process."""
    process = MagicMock()
    process.returncode = 0
    process.communicate.return_value = (b"Success", b"")
    return process


@pytest.fixture
def mock_makeblastdb_failure():
    """Mock failed makeblastdb process."""
    process = MagicMock()
    process.returncode = 1
    process.communicate.return_value = (b"", b"Error: makeblastdb failed")
    return process


@pytest.fixture
def config_files(temp_dir, sample_config_yaml, sample_database_config):
    """Create temporary configuration files."""
    # Create global config
    global_config_path = temp_dir / "global.yaml"
    with open(global_config_path, 'w') as f:
        yaml.dump(sample_config_yaml, f)
    
    # Create database config
    db_config_path = temp_dir / "databases.WB.WS285.json"
    with open(db_config_path, 'w') as f:
        json.dump(sample_database_config, f)
    
    return {
        "global": global_config_path,
        "database": db_config_path
    }


@pytest.fixture
def fasta_file(temp_dir, sample_fasta_content):
    """Create a temporary FASTA file."""
    fasta_path = temp_dir / "test.fa"
    with open(fasta_path, 'w') as f:
        f.write(sample_fasta_content)
    return fasta_path


@pytest.fixture
def mock_slack_client():
    """Mock Slack client."""
    return MagicMock()


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    return MagicMock()


@pytest.fixture
def environment_vars():
    """Mock environment variables."""
    return {
        "SLACK": "test_token",
        "S3": "test_bucket",
        "EFS": "/test/efs/path"
    }