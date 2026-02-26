# Test Organization

This directory contains automated pytest suites intended for CI and repeatable local validation.

## Structure
- `tests/test_*.py` — CI-safe tests

## Smoke scripts
External, environment-dependent smoke tests have been moved to:
- `scripts/smoke/backend_test.py`
- `scripts/smoke/backend_test_quote_revenue.py`
- `scripts/smoke/campaign_test.py`

These are intentionally excluded from default pytest discovery.

## Run
```bash
pytest
```
