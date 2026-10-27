#!/usr/bin/env python3
"""
Test Generation Helpers for SWE Agent
Automated test generation for regression testing.
"""

import json
from typing import List, Dict, Any

def generate_bug_regression_test(issue_id: str, issue_title: str, 
                                  test_file: str, test_function: str,
                                  setup_code: str, assertion_code: str) -> str:
    """Generate a regression test for a fixed bug."""
    return f'''def test_regression_{issue_id}_{issue_title.lower().replace(" ", "_")}():
    """Regression test for issue #{issue_id} - {issue_title}."""
    # Setup
{setup_code}
    
    # Act & Assert
{assertion_code}
'''

def generate_feature_regression_test(feature_name: str, 
                                      test_scenarios: List[Dict]) -> str:
    """Generate regression tests for a feature."""
    tests = []
    for i, scenario in enumerate(test_scenarios):
        tests.append(f'''
def test_{feature_name}_scenario_{i+1}():
    """Test {feature_name} - {scenario['description']}."""
    # Arrange
    {scenario.get('setup', '')}
    
    # Act
    result = {scenario['call']}
    
    # Assert
    assert result == {scenario['expected']}
''')
    return "\n".join(tests)

def generate_parametrized_test(func_name: str, test_cases: List[Dict]) -> str:
    """Generate parametrized test for multiple inputs."""
    params = ", ".join([f"({json.dumps(c['input'])}, {json.dumps(c['expected'])})" 
                        for c in test_cases])
    
    return f'''@pytest.mark.parametrize("input_data,expected", [
{params}
])
def test_{func_name}_parametrized(input_data, expected):
    """Parametrized test for {func_name}."""
    result = {func_name}(input_data)
    assert result == expected
'''

def find_existing_tests(module_pattern: str) -> List[str]:
    """Find existing test files for a module."""
    import subprocess
    try:
        result = subprocess.run(
            ["find", "tests", "-name", f"*{module_pattern}*", "-type", "f"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().split("\n") if result.stdout else []
    except Exception:
        return []

def run_specific_test(test_path: str, test_function: str = None) -> Dict:
    """Run a specific test and return results."""
    import subprocess
    cmd = ["pytest", test_path]
    if test_function:
        cmd.append(f"::{test_function}")
    cmd.extend(["-v", "--tb=short", "--json-report"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "passed": False}
    except Exception as e:
        return {"error": str(e), "passed": False}

if __name__ == "__main__":
    # Demo
    print(generate_bug_regression_test(
        "1234", "Memory leak in iterator",
        "tests/test_iterator.py", "test_iterator_memory",
        "    large_data = create_large_dataset(10000)\n    qs = QuerySet(large_data)",
        "    result = list(qs.iterator(chunk_size=100))\n    assert len(result) == 10000"
    ))
