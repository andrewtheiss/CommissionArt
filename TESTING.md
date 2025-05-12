# Testing Documentation

This document provides information on how to run and extend the test suite for CommissionArt.

## Test Structure

The test suite is organized in several files, each focusing on specific aspects of the contracts:

- `tests/test_profile_art_basic.py` - Basic profile and art piece creation tests
- `tests/test_profile_art_creation.py` - Advanced art piece creation functionality
- `tests/test_profile_array_methods.py` - Tests for array operations and pagination
- `tests/test_profile_settings_methods.py` - Tests for settings and configuration methods

## Running Tests

### Basic Test Execution

Run all tests:

```bash
ape test
```

Run a specific test file:

```bash
ape test tests/test_profile_array_methods.py
```

Run tests with verbose output:

```bash
ape test -v
```

### Parallel Test Execution

For faster test execution, use pytest-xdist which runs tests in parallel:

```bash
# Run all tests using all available CPU cores
ape test -n auto

# Run tests with a specific number of processes
ape test -n 4

# Run a specific test file in parallel
ape test tests/test_profile_array_methods.py -n auto
```

Running tests in parallel can significantly reduce execution time, especially on larger test suites.

### Test Selection

Run specific test functions:

```bash
# Run a specific test function
ape test tests/test_profile_array_methods.py::test_commission_array_methods

# Run tests matching a specific pattern
ape test -k "commission"

# Run tests with extra accounts:
ape test .  --network ethereum:local -n 10
```

## Test Coverage

The test suite covers:

1. **Profile Management**
   - Profile creation and initialization
   - Artist status management
   - Profile image management
   - Whitelist and blacklist functionality

2. **Array Operations**
   - Adding, removing items from arrays
   - Pagination with forward and reverse ordering
   - Handling edge cases (empty arrays, out-of-bounds indices)

3. **Art Piece Creation**
   - Creating art pieces as commissioners or artists
   - Verifying art piece properties
   - Testing multiple art pieces

4. **Artist-specific Methods**
   - Artist commission management
   - Additional mint ERC1155 functionality
   - Commission to ERC1155 mapping

## Best Practices

1. **Parallel-safe Tests**: When writing tests to run in parallel, ensure they use unique addresses and don't interfere with each other.

2. **Test Isolation**: Each test should be independent and not rely on state from other tests.

3. **Setup Fixtures**: Use pytest fixtures for common setup logic.

4. **Clear Assertions**: Write assertions that produce clear error messages.

## Requirements

The test suite requires:

- eth-ape: Smart contract testing framework
- pytest-xdist: For parallel test execution

These dependencies are included in `requirements.txt`. 