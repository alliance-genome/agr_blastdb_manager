# Tests

Simple test organization for the AGR BLAST Database Manager.

## Structure

```
tests/
├── unit/           # Unit tests for individual functions/modules
├── ui/             # Web interface and visual tests  
├── integration/    # Full pipeline integration tests
├── performance/    # Performance and load tests
├── cli/            # Command-line interface tests
└── fixtures/       # Test data files (FASTA, configs, etc.)
```

## Running Tests

```bash
# All tests
poetry run pytest tests/

# Specific test type
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/performance/

# UI tests (Selenium-based)
python tests/ui/test_ui.py -m WB -t nematode --comprehensive

# With coverage
poetry run pytest tests/ --cov=src --cov-report=html
```

## Test Data

Test FASTA files and mock configurations are in `fixtures/`.