#!/usr/bin/env python3
"""
Validate submission.zip before Kaggle submit.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REQUIRED_FILES = [
    "agent.yaml",
    "configs/sampling.yaml",
    "configs/eval_config.yaml",
    "prompts/system.md",
    "prompts/analyzer.md",
    "prompts/coder.md",
    "prompts/verifier.md",
    "sub_agents/code_analyzer.yaml",
    "sub_agents/patch_generator.yaml",
    "sub_agents/verifier.yaml",
    "adapters/main_lora/adapter_config.json",
    "adapters/main_lora/adapter_model.safetensors",
    "adapters/tool_lora/adapter_config.json",
    "adapters/tool_lora/adapter_model.safetensors",
    "skills/repo_navigation/SKILL.md",
    "skills/test_generation/SKILL.md",
    "skills/patch_validation/SKILL.md",
]

def validate_zip(zip_path: Path) -> tuple:
    """Validate submission.zip structure and contents."""
    errors = []
    warnings = []
    
    if not zip_path.exists():
        return False, [f"File not found: {zip_path}"], []
    
    # Check size
    size_mb = zip_path.stat().st_size / 1024 / 1024
    if size_mb > 1024:
        warnings.append(f"Submission size: {size_mb:.1f}MB (>1GB may exceed Kaggle limits)")
    else:
        print(f"✓ Size: {size_mb:.1f}MB")
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        
        # Check required files
        for req in REQUIRED_FILES:
            if req in namelist:
                print(f"✓ {req}")
            else:
                errors.append(f"Missing required file: {req}")
        
        # Check for skills
        skill_files = [f for f in namelist if f.startswith("skills/") and f.endswith("SKILL.md")]
        if skill_files:
            print(f"✓ Skills found: {len(skill_files)}")
        else:
            warnings.append("No skills found")
        
        # Check for LoRA adapters
        adapter_files = [f for f in namelist if "adapter_model.safetensors" in f]
        if adapter_files:
            print(f"✓ LoRA adapters: {len(adapter_files)}")
        else:
            errors.append("No LoRA adapter weights found")
        
        # Validate agent.yaml
        if "agent.yaml" in namelist:
            with zf.open("agent.yaml") as f:
                import yaml
                config = yaml.safe_load(f)
                
                required_fields = ["agent_id", "model", "tools", "sub_agents", "adapters", "skills"]
                for field in required_fields:
                    if field not in config:
                        errors.append(f"agent.yaml missing field: {field}")
                
                if "model" in config and "gemma-4" not in config["model"]:
                    errors.append(f"Model must be Gemma 4 variant: {config.get('model')}")
                else:
                    print(f"✓ Model: {config.get('model')}")
                
                # Check tools are allowed
                allowed_tools = {
                    "run_command", "read_file", "edit_file", "write_file",
                    "submit_patch", "get_code_neighbors", "search_similar_code",
                    "get_code_subgraph", "get_status"
                }
                if "tools" in config:
                    for tool in config["tools"]:
                        if tool not in allowed_tools:
                            warnings.append(f"Potentially unallowed tool: {tool}")
    
    # Check for prohibited patterns
    if "agent.yaml" in namelist:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            with zf.open("agent.yaml") as f:
                content = f.read().decode()
                prohibited = ["requests", "httpx", "wget", "curl", "git clone", "pip install", "import os", "subprocess"]
                for pattern in prohibited:
                    if pattern in content:
                        warnings.append(f"Potentially prohibited pattern in agent.yaml: {pattern}")
    
    return len(errors) == 0, errors, warnings

def main():
    parser = argparse.ArgumentParser(description="Validate submission.zip for Kaggle")
    parser.add_argument("zip_path", nargs="?", default="submission.zip", help="Path to submission.zip")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()
    
    zip_path = Path(args.zip_path).resolve()
    
    print(f"Validating: {zip_path}")
    print("=" * 50)
    
    valid, errors, warnings = validate_zip(zip_path)
    
    print("\n" + "=" * 50)
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠ {w}")
    
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  ✗ {e}")
    
    print("\n" + "=" * 50)
    if valid and not (args.strict and warnings):
        print("✓ VALIDATION PASSED")
        return 0
    else:
        print("✗ VALIDATION FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
