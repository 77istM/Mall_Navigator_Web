# Testing Guide

This directory contains unit tests for the Mall Navigator application.

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run with verbose output:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_algorithms.py -v
```

### Run specific test class:
```bash
pytest tests/test_algorithms.py::TestDijkstra -v
```

### Run with coverage report:
```bash
pytest tests/ --cov=algorithms --cov=components --cov=utils --cov-report=html
```

## Test Structure

- `test_algorithms.py` - Tests for Dijkstra and A* pathfinding algorithms
  - `TestDijkstra` - Dijkstra's shortest-path algorithm tests
  - `TestAStar` - A* algorithm tests
  - `TestAlgorithmComparison` - Comparative analysis of both algorithms
  - `TestEdgeCases` - Edge case and boundary condition tests

## Coverage Goals

- **Algorithms**: 90%+ coverage (critical path)
- **Components**: 70%+ coverage (UI-dependent)
- **Utils**: 85%+ coverage

## Continuous Integration

Tests should pass before merging:
- All unit tests pass
- No style warnings
- Code coverage maintained above thresholds

See `.github/workflows/tests.yml` for CI configuration.
