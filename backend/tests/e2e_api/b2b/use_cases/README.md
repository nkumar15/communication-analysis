# B2B Use Case Tests

This directory contains domain-specific tests for various business use cases.

## Structure

```
use_cases/
├── __init__.py
├── bank_surveillance/     # Banking surveillance domain tests
│   ├── __init__.py
│   ├── conftest.py       # Banking-specific fixtures
│   └── test_*.py         # Domain tests
├── marketing_agency/      # Marketing domain tests (future)
└── task_management/       # Task management tests (future)
```

## Usage

Use case tests require the corresponding `USE_CASE` environment variable:

```bash
# Run bank surveillance tests
USE_CASE=bank_surveillance pytest tests/e2e_api/b2b/use_cases/bank_surveillance/

# Run with Docker
docker compose run -e USE_CASE=bank_surveillance --rm e2e-tests \
  pytest tests/e2e_api/b2b/use_cases/bank_surveillance/ -v
```

## Design Principle

Use case tests are **separate from core tests**:

- **Core tests** (`tests/e2e_api/b2b/core/`): Platform features, base roles only
- **Use case tests** (`tests/e2e_api/b2b/use_cases/`): Domain features, domain-specific roles

This separation ensures:
1. Core platform can be tested independently
2. New use cases don't break existing tests
3. Domain features build on verified core functionality
