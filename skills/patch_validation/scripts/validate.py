#!/usr/bin/env python3
"""
Patch Validation Helpers for SWE Agent
Automated validation before submission.
"""

import subprocess
import sys
from typing import List, Tuple, Dict, Any

def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """Run command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def check_clean_apply(patch_file: str = "submission.patch") -> Tuple[bool, str]:
    """Check if patch applies cleanly."""
    code, out, err = run_cmd(["git", "apply", "--check", patch_file])
    return code == 0, err if code != 0 else "Clean apply OK"

def check_patch_stats(patch_file: str = "submission.patch") -> str:
    """Get patch statistics."""
    code, out, err = run_cmd(["git", "apply", "--stat", patch_file])
    return out if code == 0 else f"Error: {err}"

def check_whitespace() -> Tuple[bool, str]:
    """Check for whitespace issues."""
    code, out, err = run_cmd(["git", "diff", "--check", "HEAD"])
    return code == 0, err if code != 0 else "No whitespace issues"

def get_modified_files() -> List[str]:
    """Get list of modified files."""
    code, out, err = run_cmd(["git", "diff", "--name-only", "HEAD"])
    if code == 0:
        return [f for f in out.strip().split("\n") if f]
    return []

def validate_files(modified: List[str]) -> List[str]:
    """Validate modified files meet competition rules."""
    warnings = []
    
    # Check for test file modifications
    test_files = [f for f in modified if f.startswith("tests/")]
    if test_files:
        warnings.append(f"Test files modified: {test_files}")
    
    # Check for config/CI modifications
    config_files = [f for f in modified if f.startswith(".github/") or 
                    f in ("pyproject.toml", "requirements.txt", "requirements-dev.txt",
                          "setup.py", "setup.cfg", "tox.ini")]
    if config_files:
        warnings.append(f"Config/CI files modified: {config_files}")
    
    # Check for binary files
    code, out, err = run_cmd(["git", "diff", "--numstat", "HEAD"])
    if code == 0:
        for line in out.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0] == "-" and parts[1] == "-":
                warnings.append(f"Binary file detected: {parts[2]}")
    
    return warnings

def run_validation_tests(test_path: str = None) -> Tuple[bool, str]:
    """Run validation tests."""
    cmd = ["pytest", "-x", "--tb=short", "-q"]
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    code, out, err = run_cmd(cmd + ["--maxfail=5"])
    return code == 0, out if code != 0 else "Tests passed"

def run_linter() -> Tuple[bool, str]:
    """Run linter if available."""
    for linter in ["ruff", "flake8"]:
        code, out, err = run_cmd(["which", linter])
        if code == 0:
            code, out, err = run_cmd([linter, "check", "."])
            return code == 0, out if code != 0 else f"{linter} passed"
    return True, "No linter configured"

def main():
    """Main validation routine."""
    print("=== Patch Validation ===\n")
    
    all_passed = True
    results = {}
    
    # 1. Clean apply check
    print("1. Checking clean apply...")
    passed, msg = check_clean_apply()
    results["clean_apply"] = passed
    print(f"   {'PASS' if passed else 'FAIL'}: {msg}")
    if not passed:
        all_passed = False
    
    # 2. Patch stats
    print("\n2. Patch statistics:")
    stats = check_patch_stats()
    print(stats)
    
    # 3. Whitespace check
    print("\n3. Checking whitespace...")
    passed, msg = check_whitespace()
    results["whitespace"] = passed
    print(f"   {'PASS' if passed else 'FAIL'}: {msg}")
    if not passed:
        all_passed = False
    
    # 4. File validation
    print("\n4. Validating modified files...")
    modified = get_modified_files()
    print(f"   Modified files: {len(modified)}")
    for f in modified:
        print(f"   - {f}")
    
    warnings = validate_files(modified)
    if warnings:
        print("   WARNINGS:")
        for w in warnings:
            print(f"   - {w}")
    else:
        print("   No issues detected")
    
    # 5. Linting (if available)
    print("\n5. Running linter...")
    passed, msg = run_linter()
    results["linting"] = passed
    print(f"   {'PASS' if passed else 'WARNING'}: {msg}")
    
    # 6. Tests (if test path provided)
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
        print(f"\n6. Running tests: {test_path}")
        passed, msg = run_validation_tests(test_path)
        results["tests"] = passed
        print(f"   {'PASS' if passed else 'FAIL'}")
        if not passed:
            print(msg)
            all_passed = False
    
    # Summary
    print("\n=== Validation Summary ===")
    for check, passed in results.items():
        print(f"  {check}: {'PASS' if passed else 'FAIL'}")
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
