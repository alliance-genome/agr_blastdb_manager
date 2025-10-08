# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AGR BLAST Database Manager - A Python-based pipeline for automating the aggregation of model organism datasets and production of BLAST databases for the Alliance of Genome Resources.

## Development Commands

### Docker-based Development (Recommended)
- `make docker-build` - Build Docker container for x86_64
- `make docker-buildx` - Build multi-platform Docker container (requires `docker buildx create --use`)
- `make docker-run` - Run the BLAST database creation pipeline
- `make docker-run-help` - Run container with help output

### Native Development
- `uv sync` or `poetry install` - Install Python dependencies (project uses uv as primary package manager)
- `uv run python src/create_blast_db.py --help` - Main script help
- `black agr_blastdb_manager scripts` - Format code
- `make format` - Alternative formatting command
- `uv build` - Build wheel distribution

### Testing Commands
- `uv run pytest tests/` - Run all tests
- `uv run pytest tests/unit/test_agr_blastdb_manager.py` - Run specific test file
- `uv run pytest tests/ --cov=src --cov-report=html` - Run tests with coverage report
- `uv run pytest tests/integration/test_integration.py` - Run integration tests
- `uv run pytest tests/performance/test_performance.py` - Run performance tests
- `uv run python tests/ui/test_ui.py -m WB -t nematode --comprehensive` - Run comprehensive UI tests
- `uv run python tests/ui/visual_regression.py -b baseline/ -c current/ -o results/` - Run visual regression tests
- `uv run locust -f tests/performance/load_testing/locustfile.py --host=https://blast.alliancegenome.org -u 10 -r 2 -t 5m` - Run load tests

### Code Quality Commands
- `uv run black src/ tests/` - Format code with Black
- `uv run ruff check src/ tests/` - Lint code with Ruff
- `uv run ruff check --fix src/ tests/` - Lint and auto-fix with Ruff
- `uv run mypy src/` - Type check with mypy
- `uv run isort src/ tests/` - Sort imports

### Data Management
- `make clean-fasta` - Remove FASTA files
- `make clean-blast` - Remove BLAST database files
- `make clean-meta` - Remove metadata files
- `make clean-all-blast` - Remove all BLAST-related data

### MOD Configuration Generation
- `make conf/flybase/databases.json` - Generate FlyBase metadata (requires FB_EMAIL, FB_RELEASE, DMEL_RELEASE env vars)
- `make conf/wormbase/databases.json` - Download WormBase metadata from FTP
- `make conf/sgd/databases.json` - Download SGD metadata from web service

## Architecture Overview

This is a **Python CLI tool** for automating model organism dataset aggregation and BLAST database creation.

### Core Components

1. **Main Script**: `src/create_blast_db.py`
   - CLI tool using Click framework
   - Processes YAML/JSON configurations
   - Downloads FASTA files from FTP/HTTP
   - Creates BLAST databases using makeblastdb
   - Supports batch processing with progress tracking

2. **Utility Modules**:
   - `src/utils.py` - File operations, logging, Slack notifications, S3 sync
   - `src/terminal.py` - Rich-based terminal UI and progress display

3. **Configuration System**:
   - Global YAML config defines data providers and environments
   - MOD-specific JSON files contain database metadata
   - Pattern: `conf/<MOD_NAME>/databases.<MOD_NAME>.<environment>.json`

### Key Features

- **Multi-MOD Support**: Supports multiple Model Organism Databases (FB, SGD, WB, XB, ZFIN, RGD)
- **Environment Management**: dev/stage/prod environments with separate configurations
- **File Validation**: MD5 checksum verification for downloaded files
- **Progress Tracking**: Rich-based progress bars and status displays
- **Slack Integration**: Batch message sending with attachment limits handling
- **S3 Sync**: AWS S3 synchronization capabilities
- **Cleanup Management**: Automatic cleanup of temporary files

### Data Flow

1. Load global YAML configuration
2. Process MOD-specific JSON database definitions
3. Download FASTA files (FTP/HTTP) with MD5 validation
4. Uncompress files as needed
5. Run makeblastdb with appropriate flags (including -parse_seqids when needed)
6. Create organized directory structure for databases
7. Copy configuration files to output directories
8. Clean up temporary files
9. Optional S3 sync and Slack notifications

### CLI Options

- `-g, --config_yaml`: YAML file with all MODs configuration (processes multiple organisms)
- `-j, --input_json`: JSON file input coordinates (for single organism)
- `-e, --environment`: Environment name (default: "dev")
- `-m, --mod`: Model organism abbreviation (FB, SGD, WB, XB, ZFIN)
- `-s, --skip_efs_sync`: Skip EFS sync (flag)
- `-u, --update-slack`: Send Slack notifications (flag)
- `-s3, --sync-s3`: Sync to S3 bucket (flag)
- `--skip-local-storage`: Skip local archival storage of FASTA files (flag)
- `--copy-to-sequenceserver` / `--no-copy-to-sequenceserver`: Copy databases and config to /var/sequenceserver-data/ (default: enabled)

### Logging

Each pipeline run creates a unique log file with the following naming convention:
```
blast_db_{MOD}_{environment}_{timestamp}.log
```

Example: `blast_db_SGD_sgdtest2_20251007_010940.log`

Log files include:
- Configuration file used
- MOD and environment
- All processing steps
- Errors and warnings
- Timing information

### Directory Structure

```
data/
├── blast/<mod>/<env>/databases/  # BLAST database output
├── config/<mod>/<env>/           # Configuration copies
└── fasta/                        # Temporary FASTA files
logs/                             # Processing logs
conf/                             # Configuration files (if present)
src/                              # Python source code
tests/                            # Test files
```

### Local Storage

By default, FASTA files are archived in `../data/database_{YYYY_Mon_DD}/` for record-keeping. Use `--skip-local-storage` to disable this behavior when archival storage is not needed (e.g., when databases are immediately synced to S3).

### SequenceServer Integration

By default, the pipeline automatically copies generated BLAST databases and configuration files to `/var/sequenceserver-data/` at the end of each successful run. This directory structure is:

```
/var/sequenceserver-data/
├── blast/
│   └── {MOD}/
│       └── {environment}/
│           └── databases/
└── config/
    └── {MOD}/
        └── {environment}/
            └── environment.json
```

**Behavior:**
- Enabled by default (use `--no-copy-to-sequenceserver` to disable)
- Removes existing data for the same MOD/environment before copying
- Only runs after successful database creation
- Copies both BLAST database files (.nhr, .nin, .nsq, etc.) and config files

**Use cases:**
- Enable (default): For production deployments where SequenceServer serves the databases
- Disable (`--no-copy-to-sequenceserver`): For testing or when databases are served from a different location

### Testing

The project includes comprehensive test coverage across multiple categories:

**Unit Tests:**
- `tests/unit/test_utils.py` - Utility function tests (file operations, sequence analysis, configuration parsing)
- `tests/unit/test_terminal.py` - Terminal interface and logging function tests
- `tests/unit/test_create_blast_db.py` - Core BLAST database creation functionality tests

**Integration Tests:**
- `tests/integration/test_integration.py` - Full pipeline integration tests from configuration to database creation
- Tests error handling, multi-MOD workflows, and production deployment scenarios

**Performance Tests:**
- `tests/performance/test_performance.py` - Performance, scalability, and resource utilization tests
- Download speed, validation performance, memory usage, concurrent processing

**UI/Visual Tests:**
- `tests/ui/test_ui.py` - Enhanced Selenium-based web interface tests with screenshot capabilities
- `tests/ui/visual_regression.py` - Visual regression testing comparing baseline and current screenshots
- Comprehensive test modes with step-by-step screenshot capture and error documentation

**Load Testing:**
- `tests/performance/load_testing/locustfile.py` - Enhanced Locust-based load testing with detailed reporting
- Multiple task types, session tracking, and performance metrics export

**Test Infrastructure:**
- `tests/conftest.py` - Pytest configuration with comprehensive fixtures
- `tests/fixtures/` - Test data, sample configurations, and mock sequences
- Extensive mock data for all MODs (WB, SGD, FB, ZFIN, RGD, XB)

### Adding New Model Organisms

1. Create `conf/{MOD}/databases.{MOD}.{ENV}.json` with database metadata
2. Add MOD entry to `conf/global.yaml` under `data_providers`
3. Run pipeline to generate BLAST databases

### Environment Variables

Create a `.env` file in `src/` directory (see `src/.env.example` for template):

- `MODS`: Comma-separated list of model organisms (e.g., "FB,SGD,WB,XB,ZFIN")
- `AWS_ACCESS_KEY_ID`: AWS access key for S3 operations
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for S3 operations
- `S3`: S3 bucket path for syncing databases
- `EFS`: EFS mount path for syncing databases
- `MAKEBLASTDB_BIN`: Path to makeblastdb binary (if not in PATH)
- `SLACK`: Slack webhook URL for notifications
- `FB_EMAIL`: FlyBase email for metadata generation
- `FB_RELEASE`: FlyBase release version
- `DMEL_RELEASE`: Drosophila melanogaster annotation release

## Important Notes

- Always use Python 3.10+ with uv as primary package manager (poetry also supported)
- Docker is the recommended deployment method
- The system requires external tools: makeblastdb, gunzip, wget, jq
- FASTA files can be large - cleanup is automatic but configurable
- Parse seqids detection is automatic based on FASTA header format
- Uses Rich library for terminal UI and progress display
- Selenium integration for UI testing with browser automation
- Slack SDK integration for notifications with batch message handling
- ZFIN Special Handling: ZFIN databases skip MD5 validation and don't use -parse_seqids flag
- Production Deployment: Automatic copy to production location with dry-run preview

### Dependencies

- Python 3.10+
- Poetry for dependency management
- NCBI BLAST+ tools (makeblastdb)
- Docker for containerized execution
- AWS CLI/boto3 for S3 operations
- Slack SDK for notifications
