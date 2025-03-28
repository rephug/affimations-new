# Testing the Morning Coffee Application

This directory contains tests for the Morning Coffee application. The tests are organized into two main categories:

1. **Unit Tests** - These test individual components in isolation.
2. **Functional Tests** - These test the API endpoints and integrations between components.

## Test Directory Structure

```
tests/
├── conftest.py           # Common fixtures for all tests
├── unit/                 # Unit tests for individual components
│   ├── test_models.py    # Tests for data models
│   ├── test_tts_client.py  # Tests for the TTS client
│   └── test_redis_store.py # Tests for the Redis store
├── functional/           # Functional tests for API endpoints
│   └── test_api.py       # Tests for API endpoints
└── README.md             # This file
```

## Setting Up the Test Environment

Install the test dependencies:

```bash
pip install -r app/requirements.txt
```

## Running the Tests

To run all tests:

```bash
python -m pytest
```

To run unit tests only:

```bash
python -m pytest tests/unit/
```

To run functional tests only:

```bash
python -m pytest tests/functional/
```

To generate a test coverage report:

```bash
python -m pytest --cov=app tests/
```

To generate an HTML coverage report:

```bash
python -m pytest --cov=app --cov-report=html tests/
```

## Writing New Tests

When writing new tests, follow these guidelines:

1. Use the [GIVEN-WHEN-THEN](https://martinfowler.com/bliki/GivenWhenThen.html) structure in your test docstrings.
2. Use fixtures for common setup.
3. Mock external dependencies using the fixtures in `conftest.py`.
4. Write clear assertions that check for specific outcomes.

### Example Test

```python
def test_something(client):
    """
    GIVEN a Flask application
    WHEN some action is performed
    THEN check the expected outcome
    """
    # Arrange (Given)
    # ...
    
    # Act (When)
    response = client.get('/some/endpoint')
    
    # Assert (Then)
    assert response.status_code == 200
    assert 'expected_value' in response.data
```

## Mocking External Services

The `conftest.py` file provides fixtures for mocking external services:

- `mock_redis` - Mocks the Redis client
- `mock_telnyx` - Mocks the Telnyx API
- `mock_assemblyai` - Mocks the AssemblyAI API
- `mock_tts_client` - Mocks the Spark TTS client
- `mock_llm` - Mocks the LLM handler

Use these fixtures in your tests to avoid making real API calls.

## Continuous Integration

These tests are designed to run in a CI environment. The pipeline will:

1. Install dependencies
2. Run all tests
3. Generate a coverage report
4. Fail if coverage drops below a certain threshold 