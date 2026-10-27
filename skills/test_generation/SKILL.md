---
name: test_generation
version: "1.0"
description: "Test generation templates and patterns for regression testing"
author: "Iris/Hefesto"
tags: [testing, pytest, regression, templates]
---

# Test Generation Skill

## Pytest Templates

### Basic Test Template
```python
import pytest
from module_under_test import function_under_test

class TestFunctionUnderTest:
    """Tests for function_under_test."""
    
    def test_normal_case(self):
        """Test normal operation."""
        result = function_under_test(input_data)
        assert result == expected_output
    
    def test_edge_case_empty_input(self):
        """Test empty input handling."""
        result = function_under_test([])
        assert result == []
    
    def test_edge_case_none_input(self):
        """Test None input handling."""
        with pytest.raises(TypeError):
            function_under_test(None)
    
    def test_boundary_condition(self):
        """Test boundary values."""
        result = function_under_test(boundary_value)
        assert result == expected_boundary_result
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input_data,expected", [
    (input1, expected1),
    (input2, expected2),
    (edge_case, expected_edge),
])
def test_function_parametrized(input_data, expected):
    assert function_under_test(input_data) == expected
```

### Fixture-Based Tests
```python
@pytest.fixture
def sample_data():
    return {"key": "value", "list": [1, 2, 3]}

@pytest.fixture
def mock_dependency(mocker):
    return mocker.patch("module.dependency", return_value="mocked")

def test_with_fixtures(sample_data, mock_dependency):
    result = function_under_test(sample_data)
    assert result == "mocked"
```

## Regression Test Patterns

### Bug Regression Test
```python
def test_bug_1234_memory_leak_fixed():
    """Regression test for issue #1234 - memory leak in iterator."""
    # Arrange
    large_dataset = create_large_dataset(10000)
    
    # Act
    result = list(QuerySet(large_dataset).iterator(chunk_size=100))
    
    # Assert - no memory leak (indirectly tested via completion)
    assert len(result) == 10000
    
    # Verify no memory growth (if memory_profiler available)
    # assert memory_usage < threshold
```

### Feature Regression Test
```python
def test_feature_xyz_regression():
    """Ensure feature XYZ continues to work after refactor."""
    # Test the exact scenario from the feature request
    result = new_feature(params)
    assert result == expected_behavior
    
    # Test edge cases that were added during implementation
    assert edge_case_handling() == expected
```

## Test Discovery Patterns

### Find Related Tests
```bash
# Find tests for a specific module
find tests -name "*module_name*" -type f

# Find tests for a specific function
grep -r "function_name" tests/ --include="*.py"

# Find tests by keyword
grep -r "memory_leak\|iterator" tests/ --include="*.py"
```

### Run Specific Tests
```bash
# Run single test
pytest tests/test_module.py::TestClass::test_method -v

# Run all tests in module
pytest tests/test_module.py -v

# Run with pattern matching
pytest -k "memory_leak or iterator" -v
```

## Test Quality Checklist

### For Each Test
- [ ] Clear test name describing what is tested
- [ ] Single assertion per test (or related assertions)
- [ ] Covers happy path + edge cases + error cases
- [ ] Uses fixtures for shared setup
- [ ] Isolated (no test interdependencies)
- [ ] Fast execution (<1s per test)

### For Test Suite
- [ ] Covers all public APIs
- [ ] Includes regression tests for fixed bugs
- [ ] Runs in <30s for module, <5min for full suite
- [ ] CI integration (GitHub Actions)
- [ ] Coverage target: >80% for critical paths
