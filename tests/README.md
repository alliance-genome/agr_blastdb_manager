# AGR BLAST Database Manager - Test Suite

This directory contains comprehensive tests for the AGR BLAST Database Manager project.

## Test Structure

```
tests/
├── unit/                           # Unit tests for individual components
│   ├── test_utils.py              # Utility function tests
│   ├── test_terminal.py           # Terminal interface tests
│   ├── test_create_blast_db.py    # Core functionality tests
│   └── test_agr_blastdb_manager.py # Basic version tests
├── integration/                    # End-to-end integration tests
│   ├── test_integration.py        # Full pipeline integration
│   └── test_infrastructure.py     # System integration tests
├── performance/                    # Performance and load testing
│   ├── test_performance.py        # Performance benchmarks
│   └── load_testing/              # Locust-based load tests
│       └── locustfile.py
├── ui/                            # User interface testing
│   ├── test_ui.py                 # Main UI test suite
│   ├── visual_regression.py       # Visual regression testing
│   ├── config.json                # UI test configuration
│   ├── generate_ui_config.py      # UI config generator (with browser)
│   ├── generate_ui_config_simple.py # UI config generator (filesystem)
│   └── screenshots/               # Test screenshots (generated)
├── cli/                           # Command-line interface testing
│   ├── test_cli.py                # CLI functionality tests
│   └── config.json                # CLI test configuration
├── fixtures/                      # Test data and fixtures
│   ├── mock_data/                 # Sample configurations and sequences
│   │   ├── sample_configurations.py
│   │   └── sample_sequences.py
│   ├── test_sequences.json        # Test sequence data
│   └── __init__.py
├── reports/                       # Generated test reports
├── conftest.py                    # Pytest configuration and fixtures
├── run_tests.py                   # Comprehensive test runner script
└── README.md                      # This documentation
```

## Test Categories

### Unit Tests (`unit/`)
- **test_utils.py**: Tests for utility functions (file operations, sequence analysis, configuration parsing)
- **test_terminal.py**: Tests for terminal interface and logging functions  
- **test_create_blast_db.py**: Tests for core BLAST database creation functionality
- **test_agr_blastdb_manager.py**: Basic version and infrastructure tests

### Integration Tests (`integration/`)
- **test_integration.py**: Full pipeline tests from configuration to database creation
- **test_infrastructure.py**: System integration and infrastructure tests
- Tests error handling, directory structure creation, and multi-MOD workflows

### Performance Tests (`performance/`)
- **test_performance.py**: Performance, scalability, and resource utilization tests
- **load_testing/locustfile.py**: Load testing for the BLAST web interface with Locust
- Includes download speed, validation performance, memory usage, and concurrent processing tests

### UI Tests (`ui/`)
- **test_ui.py**: Selenium-based web interface tests with enhanced screenshot capabilities
- **visual_regression.py**: Visual regression testing comparing baseline and current screenshots
- **config.json**: Real database configuration generated from current releases
- **generate_ui_config*.py**: Configuration generators for UI testing

### CLI Tests (`cli/`)
- **test_cli.py**: Command-line interface testing with real database validation

## Quick Start

### Prerequisites

Install test dependencies:
```bash
poetry install --with dev
```

### Running Tests

**Run all tests using the test runner:**
```bash
# Comprehensive test suite with summary
python tests/run_tests.py all

# Or with pytest directly
poetry run pytest tests/
```

**Run specific test categories:**
```bash
# Using the test runner (recommended)
python tests/run_tests.py unit           # Unit tests only
python tests/run_tests.py integration    # Integration tests
python tests/run_tests.py performance    # Performance tests
python tests/run_tests.py ui             # UI tests
python tests/run_tests.py load           # Load tests

# Using pytest directly
poetry run pytest tests/unit/            # Unit tests
poetry run pytest tests/integration/     # Integration tests  
poetry run pytest tests/performance/     # Performance tests
```

**UI and CLI Testing:**
```bash
# UI tests for specific MOD and release
python tests/run_tests.py ui --mod WB --release WS297 --comprehensive

# UI config generation
cd tests/ui/
python generate_ui_config_simple.py  # Generate from filesystem
python generate_ui_config.py         # Generate with browser inspection

# CLI tests
python tests/run_tests.py cli

# Load testing
python tests/run_tests.py load --users 10 --duration 5m
```

**Run tests with coverage:**
```bash
poetry run pytest tests/ --cov=src --cov-report=html
```

## Detailed Test Documentation

### Unit Tests

#### test_utils.py
Tests utility functions including:
- File operations (copying, validation, compression handling)
- Sequence analysis (parse_seqids detection, FASTA validation)
- Configuration parsing (JSON/YAML processing)
- Network operations (HTTP downloads, retries)
- Special MOD handling (ZFIN-specific logic)

**Key test cases:**
- `test_needs_parse_seqids_true/false`: Validates detection of sequences requiring parse_seqids flag
- `test_get_files_http_success/failure`: Tests HTTP download with various scenarios
- `test_copy_config_file`: Validates configuration file copying

#### test_terminal.py
Tests terminal interface functions:
- Logging functions (success, error, warning messages)
- Progress display (headers, status updates, progress bars)
- Summary reporting (successful/failed operations)
- Rich console formatting

#### test_create_blast_db.py
Tests core BLAST database creation:
- makeblastdb command execution and error handling
- Configuration file processing (YAML to JSON workflow)
- Directory structure creation and management
- Error handling scenarios (download failures, validation errors)
- CLI interface testing

### Integration Tests

#### test_integration.py
Comprehensive integration tests covering:

**Full Pipeline Integration:**
- End-to-end workflow from configuration loading to database creation
- Error cascading and recovery mechanisms
- Multi-MOD processing scenarios

**Configuration Integration:**
- YAML global config to JSON database config workflow
- Multi-MOD configuration handling
- Invalid configuration scenarios

**Data Processing Integration:**
- FASTA file processing pipeline
- Compression/decompression handling
- Parse_seqids requirement detection

**Production Deployment:**
- Production copy workflows
- S3 synchronization integration
- File validation and checksums

### Performance Tests

#### test_performance.py
Performance and scalability tests:

**Download Performance:**
- Small vs. large file download speeds
- Concurrent download efficiency
- Network timeout handling

**Validation Performance:**
- MD5 checksum calculation speed scaling
- FASTA parsing performance with varying sequence counts
- Memory usage during large file processing

**Database Creation Performance:**
- makeblastdb execution time for different dataset sizes
- Concurrent database creation efficiency
- Memory cleanup verification

**Resource Utilization:**
- CPU utilization monitoring
- Disk I/O efficiency testing
- Memory leak detection

### UI Tests

#### UI/test_ui.py
Selenium-based web interface testing with enhanced features:

**Standard Testing:**
```python
# Run basic UI tests
python tests/UI/test_ui.py -m WB -t nematode -s 3 -M nucl
```

**Comprehensive Testing:**
```python  
# Run comprehensive tests with detailed screenshots
python tests/UI/test_ui.py -m WB -t nematode --comprehensive --no-headless
```

**Features:**
- Step-by-step screenshot capture
- Error screenshot capture
- Element presence verification
- Progress monitoring during long-running searches
- Detailed test reporting with success/failure summaries

#### UI/visual_regression.py
Visual regression testing tool:

```bash
# Compare baseline vs current screenshots
python tests/UI/visual_regression.py \
  -b baseline_screenshots/ \
  -c current_screenshots/ \
  -o regression_results/ \
  -t 0.01
```

**Features:**
- Image comparison with configurable similarity thresholds
- Difference image generation for visual inspection
- HTML report generation with side-by-side comparisons
- JSON results export for automated processing

#### UI/locustfile.py
Load testing with enhanced reporting:

```bash
# Run load test
locust -f tests/UI/locustfile.py \
  --host=https://blast.alliancegenome.org \
  -u 10 -r 2 -t 5m \
  --mod WB --env prod
```

**Enhanced Features:**
- Multiple task types (nucleotide BLAST, protein BLAST, homepage browsing)
- Detailed per-user session tracking
- Comprehensive test reporting with percentile statistics
- JSON report export with performance metrics
- Real-time success/failure tracking

## Configuration

### Test Configuration Files

**Global Test Configuration:**
```yaml
# tests/fixtures/sample_configurations.py
SAMPLE_GLOBAL_CONFIG = {
    "providers": {
        "WB": {"dev": "conf/WB/databases.WB.WS285.json"},
        "SGD": {"prod": "conf/SGD/databases.SGD.prod.json"}
    }
}
```

**UI Test Configuration:**
```json
{
    "WB": {
        "nematode": {
            "items": ["Caenorhabditis_elegans_genomic", "Caenorhabditis_elegans_protein"],
            "nucl": "ATGCGATCGATCGATCGATCGATCG",
            "prot": "MKLLIVDDSSGKVRAEIKQLLK"
        }
    }
}
```

### Environment Variables

**Required for full test functionality:**
```bash
export SLACK=your_slack_token          # For Slack notification tests
export S3=your_s3_bucket_path         # For S3 sync tests  
export EFS=your_efs_mount_path        # For EFS operation tests
```

**Load testing specific:**
```bash
export LOCUST_MOD=WB                  # MOD to test
export LOCUST_ENV=prod                # Environment (dev/prod)
export BLAST_CONFIG=config.json       # Path to test configuration
```

## Test Data and Fixtures

### Sequence Fixtures
Located in `tests/fixtures/sample_sequences.py`:

- **SIMPLE_NUCLEOTIDE_FASTA**: Basic nucleotide sequences for standard testing
- **PARSE_SEQIDS_NUCLEOTIDE_FASTA**: Sequences requiring -parse_seqids flag  
- **LARGE_SEQUENCE_FASTA**: Large sequences for performance testing
- **INVALID_FASTA_***: Various invalid formats for error testing
- **MOD_SPECIFIC_SEQUENCES**: Organism-specific test sequences

### Configuration Fixtures
Located in `tests/fixtures/sample_configurations.py`:

- **SAMPLE_*_CONFIG**: MOD-specific database configurations
- **ERROR_SCENARIOS**: Various error conditions for testing
- **PERFORMANCE_TEST_DATA**: Performance test parameters and expectations

## Continuous Integration

### GitHub Actions Integration

```yaml
# Example CI configuration
- name: Run tests
  run: |
    poetry install --with dev
    poetry run pytest tests/ --cov=src --cov-report=xml
    
- name: Run UI tests  
  run: |
    poetry run python tests/UI/test_ui.py -m WB -t nematode -s 1 --comprehensive
    
- name: Performance tests
  run: |
    poetry run pytest tests/test_performance.py -v
```

### Test Reporting

**Coverage Reports:**
```bash
# Generate HTML coverage report
poetry run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

**Test Results:**
- JUnit XML output for CI integration
- JSON reports for load testing
- HTML reports for visual regression testing
- Screenshot archives for UI testing

## Troubleshooting

### Common Issues

**UI Tests Failing:**
- Ensure Chrome/Chromium is installed and accessible
- Check that the BLAST web interface is accessible
- Verify test configuration files contain valid database IDs

**Performance Tests Timing Out:**
- Adjust timeout values in performance test configuration
- Consider system load when running performance tests
- Use smaller datasets for faster feedback during development

**Import Errors:**
- Ensure all dependencies are installed: `poetry install --with dev`
- Verify Python path includes the src directory
- Check that __init__.py files are present in test directories

**Load Test Connection Issues:**
- Verify the target host is accessible
- Check network connectivity and firewall settings
- Ensure MOD and environment variables are set correctly

### Debugging Tests

**Run tests with verbose output:**
```bash
poetry run pytest tests/test_utils.py -v -s
```

**Run specific test methods:**
```bash
poetry run pytest tests/test_utils.py::TestFileOperations::test_copy_config_file -v
```

**Debug with breakpoints:**
```python
import pdb; pdb.set_trace()  # Add to test code
poetry run pytest tests/test_utils.py -s
```

## Contributing to Tests

### Adding New Tests

1. **Unit Tests**: Add to appropriate test_*.py file or create new file
2. **Integration Tests**: Add to test_integration.py  
3. **Performance Tests**: Add to test_performance.py
4. **UI Tests**: Extend test_ui.py or create specialized test files

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `TestFunctionality`  
- Test methods: `test_specific_behavior`
- Fixtures: `sample_*`, `mock_*`, `temp_*`

### Mock Usage

Use mocks for external dependencies:
```python
@patch('src.utils.requests.get')
def test_http_download(mock_get):
    mock_get.return_value.status_code = 200
    # Test implementation
```

## Performance Benchmarks

### Expected Performance Metrics

**Download Performance:**
- Small files (1MB): < 5 seconds
- Large files (100MB): < 60 seconds  
- Concurrent downloads: Faster than sequential

**Validation Performance:**
- MD5 validation: Linear scaling with file size
- FASTA parsing: > 1000 sequences/second

**Database Creation:**
- Small datasets (100 sequences): < 5 seconds
- Medium datasets (10K sequences): < 30 seconds
- Large datasets (100K sequences): < 300 seconds

**Memory Usage:**
- Large file processing: < 100MB memory increase
- Memory cleanup: Return to baseline after processing

## Security Testing

### Security Considerations

- Input validation testing for FASTA files
- Path traversal prevention in file operations
- SQL injection prevention in database operations
- XSS prevention in web interface testing

### Sensitive Data Handling

- Test configurations exclude real credentials
- Mock external service interactions
- Temporary files are properly cleaned up
- No sensitive data in test fixtures or logs