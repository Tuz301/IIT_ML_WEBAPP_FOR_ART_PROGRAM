# Comprehensive Testing Suite Documentation

## Overview

The IIT ML Service includes a comprehensive testing suite covering unit tests, integration tests, end-to-end tests, security tests, and performance tests. This guide explains the testing strategy, how to run tests, and the coverage provided.

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Coverage Report](#coverage-report)
6. [CI/CD Integration](#cicd-integration)
7. [Best Practices](#best-practices)

---

## Testing Strategy

### Pyramid Approach

```
        /\
       /  \      E2E Tests (10%)
      /----\     - User workflows
     /------\    - System integration
    /--------\   - Business scenarios
   /----------\  --------------------
  /            \ Integration Tests (30%)
 /              \ - API endpoints
/                \ - Database operations
------------------ --------------------
                  Unit Tests (60%)
                  - Individual functions
                  - Business logic
                  - Data models
```

### Test Types

| Type | Purpose | Tools |
|------|---------|-------|
| Unit Tests | Test individual functions and classes | pytest, unittest |
| Integration Tests | Test component interactions | pytest, TestClient |
| E2E Tests | Test complete user workflows | pytest, TestClient |
| Security Tests | Test for vulnerabilities | pytest, custom payloads |
| Performance Tests | Test under load | pytest, locust |
| Fuzzing Tests | Test with random inputs | pytest, random |

---

## Test Structure

```
backend/ml-service/tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and fixtures
├── test_api.py              # API endpoint tests
├── test_comprehensive.py    # Comprehensive production tests
├── test_e2e.py              # End-to-end workflow tests
├── test_error_handling.py    # Error handling tests
├── test_etl.py              # ETL pipeline tests
├── test_integration.py      # Integration tests
├── test_middleware.py       # Middleware tests
├── test_model.py            # ML model tests
├── test_performance.py      # Performance tests
├── test_security.py         # Security and penetration tests
├── test_utilities.py        # Utility function tests
├── test_validation.py       # Input validation tests
└── uat/                    # User Acceptance Tests
    ├── performance_tests.py
    ├── usability_tests.py
    └── test_plan.md
```

---

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock
pip install httpx psutil

# Ensure the application is configured for testing
export TEST_MODE=true
export DATABASE_URL=sqlite:///test.db
```

### Basic Test Execution

```bash
# Run all tests
cd backend/ml-service
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test class
pytest tests/test_api.py::TestHealthEndpoints -v

# Run specific test
pytest tests/test_api.py::TestHealthEndpoints::test_health_check -v
```

### Running by Category

```bash
# Run only unit tests
pytest tests/ -k "not (e2e or integration or security)" -v

# Run only integration tests
pytest tests/ -k "integration" -v

# Run only E2E tests
pytest tests/ -k "e2e" -v

# Run only security tests
pytest tests/test_security.py -v

# Run only performance tests
pytest tests/test_performance.py -v
```

### Running with Markers

```bash
# Run tests marked as slow
pytest tests/ -m slow -v

# Run tests marked as fast
pytest tests/ -m fast -v

# Skip slow tests
pytest tests/ -m "not slow" -v
```

### Parallel Execution

```bash
# Install pytest-xdist for parallel execution
pip install pytest-xdist

# Run tests in parallel (use all CPU cores)
pytest tests/ -n auto -v

# Run with 4 workers
pytest tests/ -n 4 -v
```

### CI/CD Execution

```bash
# Run tests with coverage for CI
pytest tests/ --cov=app --cov-report=xml --cov-report=term-missing --junitxml=test-results.xml

# Exit on first failure
pytest tests/ -x

# Stop after N failures
pytest tests/ --maxfail=3
```

---

## Test Categories

### 1. API Endpoint Tests (`test_api.py`)

**Coverage:**
- Health and monitoring endpoints
- Prediction endpoints (single and batch)
- Analytics endpoints
- Backup endpoints
- Explainability endpoints
- Ensemble endpoints
- Caching endpoints
- Features endpoints
- Monitoring endpoints
- Model registry endpoints
- A/B testing endpoints
- Async operations

**Example:**
```python
def test_health_check(self):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

### 2. End-to-End Tests (`test_e2e.py`)

**Coverage:**
- Complete patient registration journey
- Batch processing workflows
- Error recovery scenarios
- Concurrent user sessions
- Scheduled report generation
- Backup and restore workflows
- Healthcare workflow compliance

**Example:**
```python
def test_complete_patient_journey(self, e2e_test_db):
    """Test full patient lifecycle: registration → data entry → prediction → analytics"""
    # Step 1: Patient Registration
    # Step 2: Add clinical data
    # Step 3: Make IIT Risk Prediction
    # Step 4: Access Analytics Dashboard
    # Step 5: Generate Report
```

### 3. Security Tests (`test_security.py`)

**Coverage:**
- SQL injection attacks
- XSS (Cross-Site Scripting) attacks
- Path traversal attacks
- Command injection attacks
- Authentication bypass attempts
- Rate limiting
- Sensitive data exposure
- PHI (Protected Health Information) protection
- Fuzzing with random inputs

**Example:**
```python
def test_sql_injection_in_prediction_endpoint(self):
    """Test SQL injection in prediction endpoint"""
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE patients; --",
        "' UNION SELECT * FROM users; --"
    ]
    for payload in sql_payloads:
        response = client.post("/predict", json=test_data)
        assert response.status_code in [200, 422, 400, 500]
```

### 4. Comprehensive Tests (`test_comprehensive.py`)

**Coverage:**
- Validation middleware
- Security middleware
- Performance middleware
- Analytics API
- Backup API
- Intervention workflow API
- Communication API
- Load testing
- Database optimization
- Compliance and security
- System integration

**Example:**
```python
def test_sql_injection_prevention(self):
    """Test SQL injection prevention in validation middleware"""
    malicious_data = {
        "messageData": {
            "demographics": {
                "stateProvince": "Lagos'; DROP TABLE patients; --"
            }
        }
    }
    response = client.post("/predict", json=malicious_data)
    assert response.status_code == 422
```

### 5. Performance Tests (`test_performance.py`)

**Coverage:**
- Response time tracking
- Slow query detection
- High concurrency load
- Memory leak prevention
- Database query performance

**Example:**
```python
def test_high_concurrency_load(self):
    """Test system under high concurrent load"""
    # Create multiple threads
    threads = []
    for i in range(50):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
    # Verify all requests complete successfully
```

### 6. Validation Tests (`test_validation.py`)

**Coverage:**
- Input data validation
- Schema validation
- Business rule validation
- Edge case handling

### 7. Error Handling Tests (`test_error_handling.py`)

**Coverage:**
- HTTP error responses
- Exception handling
- Graceful degradation
- Error logging

### 8. Model Tests (`test_model.py`)

**Coverage:**
- Model loading
- Prediction accuracy
- Feature extraction
- Model versioning

### 9. ETL Tests (`test_etl.py`)

**Coverage:**
- Data ingestion
- Data transformation
- Data quality checks
- ETL pipeline performance

---

## Coverage Report

### Generating Coverage

```bash
# Generate HTML coverage report
pytest tests/ --cov=app --cov-report=html

# Generate terminal coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Generate XML coverage report (for CI)
pytest tests/ --cov=app --cov-report=xml
```

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| API Endpoints | 90% | ~85% |
| Business Logic | 95% | ~90% |
| Data Models | 100% | ~95% |
| Security | 100% | ~95% |
| Utilities | 90% | ~85% |
| **Overall** | **90%** | **~88%** |

### Viewing Coverage Report

```bash
# Open HTML report in browser
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
xdg-open htmlcov/index.html # Linux
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml --junitxml=test-results.xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### GitLab CI Example

```yaml
test:
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest tests/ --cov=app --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

---

## Fixtures

### Available Fixtures (`conftest.py`)

```python
@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "test_mode": True,
        "redis_enabled": False,
        "model_path": "./tests/fixtures/mock_model.txt"
    }

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    class MockRedis:
        async def get(self, key):
            return None
        async def setex(self, key, ttl, value):
            pass
    return MockRedis()

@pytest.fixture(scope="function")
def e2e_test_db():
    """Create a test database for end-to-end testing"""
    # Creates temporary SQLite database
    # Yields database session
    # Cleans up after test
```

---

## Best Practices

### 1. Test Naming

```python
# Good: Descriptive and follows pattern
def test_prediction_with_missing_medication_duration_returns_default_risk():
    pass

# Bad: Vague
def test_prediction():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_patient_creation():
    # Arrange
    patient_data = {
        "given_name": "Test Patient",
        "birthdate": "1990-01-01",
        "gender": "F"
    }

    # Act
    response = client.post("/api/v1/patients/", json=patient_data)
    result = response.json()

    # Assert
    assert response.status_code == 201
    assert result["given_name"] == "Test Patient"
    assert "patient_uuid" in result
```

### 3. Use Fixtures for Setup

```python
# Good: Using fixtures
def test_prediction(sample_patient_data):
    response = client.post("/predict", json=sample_patient_data)
    assert response.status_code == 200

# Bad: Duplicating setup
def test_prediction():
    patient_data = {...}  # Duplicated code
    response = client.post("/predict", json=patient_data)
    assert response.status_code == 200
```

### 4. Test Edge Cases

```python
def test_prediction_with_boundary_values():
    # Test minimum values
    test_min = {"medication_duration": 0}
    response_min = client.post("/predict", json=test_min)
    assert response_min.status_code == 200

    # Test maximum values
    test_max = {"medication_duration": 999999}
    response_max = client.post("/predict", json=test_max)
    assert response_max.status_code == 200
```

### 5. Mock External Dependencies

```python
from unittest.mock import patch

def test_prediction_with_mocked_model():
    with patch('app.ml_model.predict') as mock_predict:
        mock_predict.return_value = 0.75

        response = client.post("/predict", json=sample_data)
        assert response.status_code == 200
        assert response.json()["iit_risk_score"] == 0.75
```

### 6. Test Error Scenarios

```python
def test_prediction_with_invalid_data():
    invalid_data = {"invalid": "data"}
    response = client.post("/predict", json=invalid_data)
    assert response.status_code == 422
    assert "validation error" in response.json()["detail"][0]["msg"]
```

---

## Troubleshooting

### Common Issues

#### 1. Tests Fail Due to Database Lock

**Problem:** SQLite database locked during concurrent tests

**Solution:**
```python
# Use separate database for each test
@pytest.fixture(scope="function")
def test_db():
    db_fd, db_path = tempfile.mkstemp()
    engine = create_engine(f"sqlite:///{db_path}")
    # ... test code ...
    os.close(db_fd)
    os.unlink(db_path)
```

#### 2. Tests Pass Individually but Fail Together

**Problem:** Test isolation issue

**Solution:**
```bash
# Run tests with isolation
pytest tests/ --forked

# Or use pytest-xdist
pytest tests/ -n auto
```

#### 3. Coverage Report Incomplete

**Problem:** Some files not included in coverage

**Solution:**
```bash
# Specify source directories
pytest tests/ --cov=app --cov=app.api --cov=app.models
```

#### 4. Slow Tests

**Problem:** Tests taking too long to run

**Solution:**
```bash
# Run only fast tests
pytest tests/ -m fast -v

# Profile slow tests
pytest tests/ --durations=10
```

---

## Test Metrics

### Key Metrics to Track

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Test Coverage | >90% | `pytest --cov=app` |
| Test Execution Time | <5 min | `pytest --durations=10` |
| Flaky Tests | 0% | Run tests multiple times |
| Failed Tests | 0% | CI/CD dashboard |
| Security Vulnerabilities | 0 | `pytest test_security.py` |

---

## Continuous Improvement

### Regular Tasks

1. **Weekly:**
   - Review failed tests
   - Update test cases for new features
   - Check coverage trends

2. **Monthly:**
   - Run full test suite
   - Review and update test data
   - Optimize slow tests

3. **Quarterly:**
   - Review test strategy
   - Update security test payloads
   - Performance benchmarking

---

## Support

For issues or questions about testing:
- Check pytest documentation: https://docs.pytest.org/
- Review test logs in `logs/`
- Contact development team
