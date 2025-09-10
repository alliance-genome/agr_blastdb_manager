# Quick Reference - Reorganized Test Structure

## Most Common Commands

### Test Runner (Recommended)
```bash
# List all available test categories
uv run python tests/run_tests.py list

# Run all tests with summary
uv run python tests/run_tests.py all

# Run specific category
uv run python tests/run_tests.py unit -v           # Unit tests with verbose output
uv run python tests/run_tests.py integration       # Integration tests
uv run python tests/run_tests.py performance       # Performance benchmarks
```

### UI Testing
```bash
# Test specific MOD/release
uv run python tests/run_tests.py ui --mod WB --release WS297

# Comprehensive UI testing with detailed screenshots
uv run python tests/run_tests.py ui --mod FB --release FB2025_03 --comprehensive

# Generate new UI config from current databases
cd tests/ui/
uv run python generate_ui_config_simple.py
```

### Load Testing
```bash
# Quick load test (5 users, 2 minutes)
uv run python tests/run_tests.py load

# Custom load test
uv run python tests/run_tests.py load --users 20 --duration 10m
```

### Coverage Reports
```bash
# Generate coverage report
uv run python tests/run_tests.py coverage

# View HTML report
open htmlcov/index.html
```

## Direct pytest Usage

### Unit Tests
```bash
uv run pytest tests/unit/ -v                    # All unit tests
uv run pytest tests/unit/test_utils.py -v       # Specific test file
```

### Integration Tests
```bash
uv run pytest tests/integration/ -v --tb=short  # All integration tests
```

### Performance Tests
```bash
uv run pytest tests/performance/test_performance.py -v
```

## File Locations After Reorganization

**Before** → **After**
- `test_utils.py` → `unit/test_utils.py`
- `test_integration.py` → `integration/test_integration.py`
- `test_performance.py` → `performance/test_performance.py`
- `UI/test_ui.py` → `ui/test_ui.py`
- `UI/locustfile.py` → `performance/load_testing/locustfile.py`
- `CLI/test_cli.py` → `cli/test_cli.py`

## New Features

1. **Test Runner Script**: `tests/run_tests.py` - Unified interface for all testing
2. **Organized Structure**: Tests grouped by category for better maintainability
3. **Real UI Config**: `tests/ui/config.json` generated from actual current releases
4. **Load Testing**: Dedicated `performance/load_testing/` directory
5. **Reports Directory**: `tests/reports/` for generated test reports

## Current Database Releases (in ui/config.json)
- **WB**: WS297 (8 databases)
- **FB**: FB2025_03 (23 databases) 
- **SGD**: main (1 database)
- **RGD**: production (1 database)
- **ZFIN**: prod (1 database)

Total: 34 databases across 5 MODs ready for testing.