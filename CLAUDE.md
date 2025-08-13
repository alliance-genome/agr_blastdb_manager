# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development Commands
- `poetry install` - Install dependencies
- `poetry shell` - Activate virtual environment
- `poetry run python src/create_blast_db.py --help` - Show main script help

### Docker Commands
- `make docker-build` - Build Docker image (x86_64)
- `make docker-buildx` - Build multi-platform Docker image (arm64/amd64)
- `make docker-run` - Run the pipeline in Docker
- `make docker-run-help` - Show Docker help

### Testing Commands
- `poetry run pytest tests/` - Run all tests
- `poetry run pytest tests/test_agr_blastdb_manager.py` - Run specific test file
- `poetry run pytest tests/ --cov=src --cov-report=html` - Run tests with coverage report
- `poetry run pytest tests/test_integration.py` - Run integration tests
- `poetry run pytest tests/test_performance.py` - Run performance tests
- `python tests/UI/test_ui.py -m WB -t nematode --comprehensive` - Run comprehensive UI tests
- `python tests/UI/visual_regression.py -b baseline/ -c current/ -o results/` - Run visual regression tests
- `locust -f tests/UI/locustfile.py --host=https://blast.alliancegenome.org -u 10 -r 2 -t 5m` - Run load tests

### Code Quality Commands
- `poetry run black src/ tests/` - Format code with Black
- `poetry run ruff check src/ tests/` - Lint code with Ruff
- `poetry run ruff check --fix src/ tests/` - Lint and auto-fix with Ruff
- `poetry run mypy src/` - Type check with mypy
- `poetry run isort src/ tests/` - Sort imports

### Data Management Commands
- `make clean-fasta` - Remove downloaded FASTA files
- `make clean-blast` - Remove generated BLAST databases
- `make clean-meta` - Remove metadata files
- `make clean-all-blast` - Remove all BLAST-related data

## Architecture Overview

### Core Components

**Main Pipeline Script** (`src/create_blast_db.py`)
- Entry point for BLAST database creation
- Handles configuration parsing (YAML/JSON)
- Orchestrates download, validation, and database creation
- Supports multiple model organisms (MODs): FB, SGD, WB, XB, ZFIN, RGD

**Utility Functions** (`src/utils.py`)
- File download handlers (FTP/HTTP)
- MD5 checksum validation
- FASTA file validation and editing
- S3/EFS synchronization
- Slack notifications
- Logging utilities

**Terminal Interface** (`src/terminal.py`)
- Rich-based console output
- Progress bars and status indicators
- Error formatting and display

### Configuration System

**Global Configuration** (`conf/global.yaml`)
- Defines data providers and environments
- References MOD-specific JSON files

**MOD-Specific Configuration** (`conf/{mod}/databases.{mod}.{env}.json`)
- Contains database metadata for each model organism
- Includes download URLs, checksums, taxonomic info
- Supports genome browser mappings

### Data Flow

1. **Configuration Loading**: Parse YAML/JSON configs to get database specifications
2. **File Download**: Download FASTA files from FTP/HTTP sources with progress tracking
3. **Validation**: Verify MD5 checksums and FASTA format
4. **Database Creation**: Run `makeblastdb` with appropriate parameters
5. **Post-processing**: Handle file cleanup, S3 sync, and notifications

### Directory Structure

```
data/
├── blast/{mod}/{env}/databases/  # Generated BLAST databases
├── config/{mod}/{env}/          # Copied configuration files
└── fasta/                       # Downloaded FASTA files (temporary)

logs/                            # Detailed operation logs
conf/                           # Configuration files
src/                            # Source code
tests/                          # Test files
```

### Key Features

- **Multi-MOD Support**: Handles different model organisms with specific requirements
- **Environment Management**: Supports dev/stage/prod environments
- **Robust Download**: Automatic retry and validation for file downloads
- **Progress Tracking**: Rich terminal output with progress bars
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Slack Integration**: Optional notifications for pipeline status
- **Docker Support**: Containerized execution for consistent environments
- **Parse SeqIDs Policy**: Mandatory -parse_seqids flag for all MODs except ZFIN
- **Production Deployment**: Automatic copy to production location with dry-run preview
- **ZFIN Special Handling**: ZFIN databases skip MD5 validation and don't use -parse_seqids flag

### Testing

The project includes comprehensive test coverage across multiple categories:

**Unit Tests:**
- `tests/test_utils.py` - Utility function tests (file operations, sequence analysis, configuration parsing)
- `tests/test_terminal.py` - Terminal interface and logging function tests
- `tests/test_create_blast_db.py` - Core BLAST database creation functionality tests

**Integration Tests:**
- `tests/test_integration.py` - Full pipeline integration tests from configuration to database creation
- Tests error handling, multi-MOD workflows, and production deployment scenarios

**Performance Tests:**
- `tests/test_performance.py` - Performance, scalability, and resource utilization tests
- Download speed, validation performance, memory usage, concurrent processing

**UI/Visual Tests:**
- `tests/UI/test_ui.py` - Enhanced Selenium-based web interface tests with screenshot capabilities
- `tests/UI/visual_regression.py` - Visual regression testing comparing baseline and current screenshots
- Comprehensive test modes with step-by-step screenshot capture and error documentation

**Load Testing:**
- `tests/UI/locustfile.py` - Enhanced Locust-based load testing with detailed reporting
- Multiple task types, session tracking, and performance metrics export

**Test Infrastructure:**
- `tests/conftest.py` - Pytest configuration with comprehensive fixtures
- `tests/fixtures/` - Test data, sample configurations, and mock sequences
- Extensive mock data for all MODs (WB, SGD, FB, ZFIN, RGD, XB)

**Test Features:**
- Code coverage reporting with HTML output
- Visual regression testing with image comparison
- Performance benchmarking and resource monitoring  
- Load testing with detailed metrics and JSON export
- Comprehensive error scenario testing
- Memory leak detection and cleanup verification

### Environment Variables

Required for full functionality:
- `SLACK`: Slack API token for notifications
- `S3`: S3 bucket path for file storage
- `EFS`: EFS mount path for sync operations

## Operational Notes

### CLI Usage Patterns

**Run for specific MOD and environment:**
```bash
poetry run python src/create_blast_db.py --conf conf/global.yaml --mod WB --env WS285
```

**Check parse_seqids policy without creating databases:**
```bash
poetry run python src/create_blast_db.py --conf conf/global.yaml --mod WB --env WS285 --check-parse-seqids
```

**Run with production copy (requires confirmation):**
```bash
poetry run python src/create_blast_db.py --conf conf/global.yaml --mod WB --env WS285 --production-copy
```

### Configuration Structure

Configuration follows a hierarchical pattern:
- `conf/global.yaml` defines providers and references MOD-specific configs
- `conf/{mod}/databases.{mod}.{env}.json` contains database specifications
- Each database entry includes: URI, MD5, blast_title, taxonomy, seqtype

### Error Handling Patterns

The system provides comprehensive error reporting:
- Entry-level failures are logged with context (download, unzip, makeblastdb stages)
- Failed entries are summarized at completion
- Common error patterns are detected (network issues, makeblastdb failures)
- Individual logs per entry stored in `../logs/` directory

### File Management

- Downloaded FASTA files are temporary and cleaned up after processing
- BLAST databases are created in `../data/blast/{mod}/{env}/databases/`
- Configuration files are copied to `../data/config/{mod}/{env}/`
- Use `--store-files` flag to preserve original files for archival

### Special MOD Considerations

- **ZFIN**: Skips MD5 validation and never uses -parse_seqids flag
- **All others**: Mandatory -parse_seqids flag for consistent FASTA download functionality