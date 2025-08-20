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
uv run pytest tests/

# Specific test type
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/performance/

# UI tests (Selenium-based)
python tests/ui/test_ui.py -m WB -t nematode --comprehensive

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## Test Data

Test FASTA files and mock configurations are in `fixtures/`.