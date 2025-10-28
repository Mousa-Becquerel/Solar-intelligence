# Test Suite for Solar Intelligence Application

## Overview

This directory contains the test suite for the Solar Intelligence application. Tests are written using pytest and cover authentication, conversations, models, and agents.

## Installation

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-mock flask-testing
```

Or if using poetry:

```bash
poetry add --group dev pytest pytest-cov pytest-mock flask-testing
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=. --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_auth.py
```

### Run specific test class
```bash
pytest tests/test_auth.py::TestLogin
```

### Run specific test
```bash
pytest tests/test_auth.py::TestLogin::test_login_success
```

### Run with verbose output
```bash
pytest -v
```

### Run and stop on first failure
```bash
pytest -x
```

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── test_auth.py                # Authentication tests
├── test_conversations.py       # Conversation CRUD tests
├── test_models.py              # Database model tests
└── README.md                   # This file
```

## Fixtures

Common fixtures defined in `conftest.py`:

- `app` - Flask application instance
- `client` - Test client for making requests
- `db_session` - Database session (cleaned after each test)
- `test_user` - Regular user account
- `admin_user` - Admin user account
- `authenticated_client` - Logged-in test client
- `test_conversation` - Sample conversation
- `test_message` - Sample message

## Test Coverage

Current test coverage:

- ✅ User authentication (login, register, logout)
- ✅ Password security
- ✅ Account deletion
- ✅ Conversation creation
- ✅ Conversation listing
- ✅ Message operations
- ✅ Conversation deletion
- ✅ User model methods
- ✅ Query limits and counting
- ✅ Relationships

### Not Yet Covered

- ⏳ Agent execution
- ⏳ Query processing
- ⏳ Admin operations
- ⏳ Survey submissions
- ⏳ Feedback submission
- ⏳ Rate limiting
- ⏳ Error handling
- ⏳ SSE streaming

## Writing New Tests

### Test Class Template

```python
class TestYourFeature:
    """Test your feature description"""

    def test_success_case(self, authenticated_client):
        """Test successful operation"""
        response = authenticated_client.post('/your-endpoint', json={
            'data': 'value'
        })
        assert response.status_code == 200

    def test_failure_case(self, authenticated_client):
        """Test error handling"""
        response = authenticated_client.post('/your-endpoint', json={})
        assert response.status_code == 400
```

### Using Fixtures

```python
def test_with_user(self, test_user, db_session):
    """Test that uses a test user"""
    # test_user is automatically created
    assert test_user.username == 'test@example.com'

    # Make modifications
    test_user.full_name = 'Updated Name'
    db_session.session.commit()
```

### Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_with_mock(self, authenticated_client):
    """Test with mocked agent"""
    with patch('app.market_intelligence_agent') as mock_agent:
        mock_agent.run_sync.return_value = {
            'response': 'Mocked response'
        }

        response = authenticated_client.post('/query', json={
            'message': 'test query'
        })

        assert response.status_code == 200
        mock_agent.run_sync.assert_called_once()
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Use fixtures to ensure clean state
3. **Descriptive Names**: Test names should describe what they test
4. **Arrange-Act-Assert**: Structure tests clearly
5. **Mock External Services**: Don't make real API calls in tests
6. **Test Edge Cases**: Test both success and failure scenarios

## Troubleshooting

### Database Errors

If you get database errors, ensure the test database is clean:

```python
# In your test
db.session.remove()
db.drop_all()
db.create_all()
```

### Import Errors

If you get import errors, ensure the parent directory is in Python path:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### Fixture Scope Issues

If fixtures aren't working as expected, check the scope:

- `function` - Created/destroyed for each test (default)
- `class` - Created/destroyed for each test class
- `module` - Created/destroyed for each test module
- `session` - Created once for entire test session

## Next Steps

To expand test coverage:

1. Add tests for agent execution
2. Add tests for query processing
3. Add tests for admin operations
4. Add integration tests
5. Add performance tests
6. Add security tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
