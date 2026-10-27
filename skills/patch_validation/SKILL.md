---
name: patch_validation
version: "1.0"
description: "Patch validation and quality checks before submission"
author: "Hefesto/Apolo"
tags: [validation, patch, git, quality, ci]
---

# Patch Validation Skill

## Validation Checklist

### Pre-Submission Checks

#### 1. Patch Applies Cleanly
```bash
# Check if patch applies without conflicts
git apply --check submission.patch
# Exit code 0 = clean, non-zero = conflicts
```

#### 2. Patch Format Validation
```bash
# Verify patch format
git apply --stat submission.patch
# Shows files changed, lines added/removed
```

#### 3. No Binary Files
```bash
# Ensure no binary files in patch
git diff --numstat HEAD | awk '$1 == "-" && $2 == "-" {print "BINARY: " $3}'
```

#### 4. Whitespace Clean
```bash
# Check for trailing whitespace
git diff --check HEAD
```

### Test Validation

#### 1. Issue-Specific Tests Pass
```bash
# Run the exact test from the issue
pytest tests/path/to/test.py::test_function -v
```

#### 4. Regression Tests Pass
```bash
# Run broader test suite
pytest tests/ -x --tb=short -q
```

#### 5. No New Test Failures
```bash
# Compare test results before/after
pytest tests/ --tb=no -q 2>&1 | tail -5
```

### Code Quality Checks

#### 1. Linting (if configured)
```bash
ruff check .
# or
flake8 .
```

#### 2. Type Checking (if configured)
```bash
mypy .
```

#### 3. Formatting (if configured)
```bash
ruff format --check .
# or
black --check .
```

### Competition-Specific Checks

#### 1. Patch Size Limit
```bash
# Check patch size (Kaggle limit: ~1GB for submission.zip)
wc -c submission.patch
# Should be reasonably small (<10MB for typical patches)
```

#### 2. Only Allowed Files Modified
```bash
# Verify only source files in repo are modified
git diff --name-only HEAD | grep -vE "^(tests?/|\.github/|docs?/|README|\.md$)"
```

#### 3. No Test File Modifications
```bash
# Ensure test files aren't modified (usually not allowed)
git diff --name-only HEAD | grep "^tests/" && echo "WARNING: Test files modified"
```

#### 4. No Config/CI Changes
```bash
# Ensure no CI/config changes unless explicitly needed
git diff --name-only HEAD | grep -E "^\.github/|^pyproject\.toml$|^requirements" && echo "WARNING: Config files modified"
```

## Validation Script

```bash
#!/bin/bash
# validate_patch.sh - Run all validation checks

set -e

echo "=== Patch Validation ==="

# 1. Clean apply check
echo "1. Checking clean apply..."
git apply --check submission.patch || { echo "FAIL: Patch doesn't apply cleanly"; exit 1; }
echo "   PASS"

# 2. Show patch stats
echo "2. Patch statistics:"
git apply --stat submission.patch

# 3. Whitespace check
echo "3. Checking whitespace..."
git diff --check HEAD || { echo "FAIL: Whitespace issues"; exit 1; }
echo "   PASS"

# 4. Run issue tests (placeholder - replace with actual test)
echo "4. Running validation tests..."
# pytest tests/specific_test.py -v

# 5. Linting (if available)
if command -v ruff &> /dev/null; then
    echo "5. Running linter..."
    ruff check . || echo "   WARNING: Linting issues found"
fi

echo "=== Validation Complete ==="
```

## Integration with Agent Workflow

```yaml
# In agent workflow, before submit_patch:
- name: Validate Patch
  run: |
    ./scripts/validate_patch.sh
    # If passes, proceed to submit_patch
```

## Common Patch Issues & Fixes

| Issue | Detection | Fix |
|-------|-----------|-----|
| Trailing whitespace | `git diff --check` | `sed -i 's/[[:space:]]*$//' file.py` |
| Line endings | `git diff --check` | `dos2unix file.py` or editor config |
| Binary file | `git diff --numstat` | Remove binary, use text alternative |
| Test file modified | `grep "^tests/"` | Revert test changes: `git checkout tests/file.py` |
| Config modified | `grep "^\.github/"` | Revert unless explicitly required |

## Budget Impact
- Validation: ~30-60 seconds
- Full test suite: 2-10 minutes (budget dependent)
- Run validation every 2-3 patches during development
- Full validation before final submission
