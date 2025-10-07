# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AGR BLAST Database Manager - A Python-based pipeline for automating the aggregation of model organism datasets and production of BLAST databases for the Alliance of Genome Resources.

## Development Commands

### Setup and Installation
```bash
# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry shell
```

### Running the Pipeline

#### Docker (recommended)
```bash
# Build Docker image (x86_64)
make docker-build

# Build Docker image (arm64 or multi-platform)
make docker-buildx

# Run pipeline in Docker
make docker-run
```

#### Native Python
```bash
# Main pipeline execution with YAML config (processes all MODs)
poetry run python src/create_blast_db.py --config_yaml=conf/global.yaml

# Run for specific JSON config file
poetry run python src/create_blast_db.py --input_json=conf/WB/databases.WB.WS285.json --environment=WS285 --mod=WB

# Additional options
poetry run python src/create_blast_db.py --config_yaml=conf/global.yaml --sync-s3 --update-slack
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_agr_blastdb_manager.py
poetry run pytest tests/CLI/test_cli.py
poetry run pytest tests/UI/test_ui.py
```

### Code Quality
```bash
# Format code with Black
poetry run black src/ tests/

# Sort imports with isort
poetry run isort src/ tests/

# Type checking with mypy
poetry run mypy src/
```

### Clean Commands
```bash
# Clean FASTA files
make clean-fasta

# Clean BLAST databases
make clean-blast

# Clean metadata
make clean-meta

# Clean all generated files
make clean-all-blast
```

## Architecture Overview

### Core Components

1. **Main Pipeline** (`src/create_blast_db.py`)
   - Orchestrates the entire BLAST database creation process
   - Reads configuration from YAML/JSON files
   - Downloads FASTA files from FTP/HTTP sources
   - Creates BLAST databases using makeblastdb
   - Manages directory structures for different environments (dev, stage, prod)
   - Integrates with AWS S3 for storage
   - Sends Slack notifications for monitoring

2. **Configuration System**
   - `conf/global.yaml`: Defines which model organisms and environments to process
   - `conf/{MOD}/databases.{MOD}.{ENV}.json`: Metadata for each organism's databases
   - Each MOD configuration specifies FASTA sources, BLAST parameters, and metadata

3. **Utility Modules**
   - `src/utils.py`: Helper functions for file operations, S3 sync, logging, and Slack integration
   - `src/terminal.py`: Rich terminal output for progress tracking and status display

### Data Flow

1. Configuration files define which databases to build
2. Pipeline downloads FASTA files from configured sources (FTP/HTTP)
3. FASTA files are stored in `../data/` directory with MD5 checksum verification
4. Files are unzipped (gunzip) if compressed
5. makeblastdb processes FASTA files into BLAST databases
6. Databases are organized in `../data/blast/{MOD}/{environment}/databases/`
7. Metadata and configuration copied to `../data/config/{MOD}/{environment}/`
8. Optional S3 sync uploads databases to AWS
9. Optional Slack notifications sent for monitoring

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
├── fasta/          # Downloaded FASTA files
├── blast/          # Generated BLAST databases
│   └── {MOD}/
│       └── {environment}/
│           └── databases/
└── config/         # Configuration metadata
    └── {MOD}/
        └── {environment}/
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

### Dependencies

- Python 3.10+
- Poetry for dependency management
- NCBI BLAST+ tools (makeblastdb)
- Docker for containerized execution
- AWS CLI/boto3 for S3 operations
- Slack SDK for notifications