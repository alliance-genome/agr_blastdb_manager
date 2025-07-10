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

### Code Quality Commands
- `poetry run black src/ tests/` - Format code with Black
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
- Supports multiple model organisms (MODs): FB, SGD, WB, XB, ZFIN

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
- **Parse SeqIDs Detection**: Automatically detects if FASTA headers need -parse_seqids flag

### Testing

- Basic version test in `tests/test_agr_blastdb_manager.py`
- UI tests using Selenium in `tests/UI/`
- CLI tests in `tests/CLI/`
- Load testing with Locust framework

### Environment Variables

Required for full functionality:
- `SLACK`: Slack API token for notifications
- `S3`: S3 bucket path for file storage
- `EFS`: EFS mount path for sync operations