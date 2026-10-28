#!/usr/bin/env python3
"""
Assemble final submission.zip for Kaggle competition.
"""

import argparse
import shutil
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


def validate_structure(base_path: Path, version: str) -> list:
    """Validate all required files exist."""
    missing = []
    for req in REQUIRED_FILES:
        # Handle version-specific adapter paths
        if "main_lora" in req or "tool_lora" in req:
            adapted = req.replace("main_lora", f"main_lora/{version}").replace(
                "tool_lora", f"tool_lora/{version}"
            )
        else:
            adapted = req

        full_path = base_path / adapted
        if not full_path.exists():
            missing.append(adapted)
    return missing


def validate_agent_yaml(agent_yaml_path: Path) -> list:
    """Validate agent.yaml has required fields."""
    import yaml

    errors = []

    with open(agent_yaml_path) as f:
        config = yaml.safe_load(f)

    required = ["agent_id", "model", "tools", "sub_agents", "adapters", "skills"]
    for field in required:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    if "model" in config and "gemma-4" not in config["model"]:
        errors.append(f"Model must be Gemma 4 variant, got: {config.get('model')}")

    return errors


def create_submission_zip(base_path: Path, output_path: Path, version: str) -> None:
    """Create submission.zip with correct structure."""

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        submission_dir = tmpdir / "submission"
        submission_dir.mkdir()

        # Copy all required files maintaining structure
        for req in REQUIRED_FILES:
            if "main_lora" in req or "tool_lora" in req:
                src = base_path / req.replace("main_lora", f"main_lora/{version}").replace(
                    "tool_lora", f"tool_lora/{version}"
                )
                dst = submission_dir / req
            else:
                src = base_path / req
                dst = submission_dir / req

            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            else:
                print(f"WARNING: Missing file: {src}")

        # Copy skill scripts and resources
        for skill in ["repo_navigation", "test_generation", "patch_validation"]:
            skill_src = base_path / "skills" / skill
            skill_dst = submission_dir / "skills" / skill
            if skill_src.exists():
                shutil.copytree(skill_src, skill_dst, dirs_exist_ok=True)

        # Create zip
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in submission_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(submission_dir)
                    zipf.write(file_path, arcname)

        print(f"Created submission.zip at {output_path}")
        print(f"Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble submission.zip for Kaggle")
    parser.add_argument("--version", default="final", help="Adapter version to use")
    parser.add_argument("--output", default="submission.zip", help="Output zip path")
    parser.add_argument("--base", default=".", help="Base directory")
    args = parser.parse_args()

    base_path = Path(args.base).resolve()
    output_path = Path(args.output).resolve()
    version = args.version

    print(f"Assembling submission from {base_path}")
    print(f"Using adapter version: {version}")

    # Validate structure
    missing = validate_structure(base_path, version)
    if missing:
        print("ERROR: Missing required files:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

    # Validate agent.yaml
    agent_yaml = base_path / "agent.yaml"
    errors = validate_agent_yaml(agent_yaml)
    if errors:
        print("ERROR: agent.yaml validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Create submission
    create_submission_zip(base_path, output_path, version)
    print("Submission assembly complete!")


if __name__ == "__main__":
    main()
