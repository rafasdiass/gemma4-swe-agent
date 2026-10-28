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

import yaml
from validate_submission import IncludeLoader

REQUIRED_FILES = [
    "agent.yaml",
    "eval_config.yaml",
    "configs/sampling.yaml",
    "prompts/system.md",
    "prompts/analyzer.md",
    "prompts/coder.md",
    "prompts/verifier.md",
    "sub_agents/code_analyzer.yaml",
    "sub_agents/patch_generator.yaml",
    "sub_agents/verifier.yaml",
    "skills/repo_navigation/SKILL.md",
    "skills/test_generation/SKILL.md",
    "skills/patch_validation/SKILL.md",
]

# Adapters are versioned subdirectories selected via --version; required only
# when an agent YAML declares `adapter: <name>` (T09: per-agent, optional).
ADAPTER_TEMPLATE = "adapters/{name}/adapter_{file}"


def validate_structure(base_path: Path, version: str) -> list[str]:
    """Validate all required files exist (adapters only when declared)."""

    missing = []
    for req in REQUIRED_FILES:
        if not (base_path / req).exists():
            missing.append(req)

    # Adapters: version-specific subdirs, required only if some YAML declares one
    declared = set()
    for yaml_path in [base_path / "agent.yaml", *(base_path / "sub_agents").glob("*.yaml")]:
        if not yaml_path.exists():
            continue
        config = yaml.load(yaml_path.read_text(encoding="utf-8"), Loader=IncludeLoader)
        if isinstance(config, dict) and isinstance(config.get("adapter"), str):
            declared.add(config["adapter"])
    for name in sorted(declared):
        for file_name in ("config.json", "model.safetensors"):
            adapted = f"adapters/{name}/adapter_{file_name.replace('model.', 'model.')}"
            adapted = ADAPTER_TEMPLATE.format(name=name, file=file_name)
            if not (base_path / adapted).exists():
                missing.append(adapted)
    return missing


def validate_agent_yaml(agent_yaml_path: Path) -> list[str]:
    """Validate agent.yaml has required fields (SandboxedAgentConfig schema, T09)."""

    errors = []

    with open(agent_yaml_path) as f:
        config = yaml.load(f, Loader=IncludeLoader)

    required = ["name", "model", "instruction", "tools", "skills", "generate_content_config"]
    for field in required:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    for field in ("agent_id", "system_prompt", "sampling", "adapters"):
        if field in config:
            errors.append(f"Legacy/unknown field (A-12): {field}")

    if "model" in config and config["model"] not in {
        "gemma-4-31b-it-qat-w4a16-ct",
        "gemma-4-12b-it-qat-w4a16-ct",
        "gemma-4-e4b-it-qat-w4a16-ct",
        "gemma-4-e2b-it-qat-w4a16-ct",
    }:
        errors.append(f"Model not in ALLOWED_MODEL_NAMES, got: {config.get('model')}")

    return errors


def create_submission_zip(base_path: Path, output_path: Path, version: str) -> None:
    """Create submission.zip with correct structure."""

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        submission_dir = tmpdir / "submission"
        submission_dir.mkdir()

        # Copy all required files maintaining structure
        for req in REQUIRED_FILES:
            src = base_path / req
            dst = submission_dir / req
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            else:
                print(f"WARNING: Missing file: {src}")

        # Copy declared adapters from their version-specific subdirs (T09)
        declared = set()
        for yaml_path in [base_path / "agent.yaml", *(base_path / "sub_agents").glob("*.yaml")]:
            if not yaml_path.exists():
                continue
            config = yaml.load(yaml_path.read_text(encoding="utf-8"), Loader=IncludeLoader)
            if isinstance(config, dict) and isinstance(config.get("adapter"), str):
                declared.add(config["adapter"])
        for name in sorted(declared):
            src_dir = base_path / "adapters" / name / version
            dst_dir = submission_dir / "adapters" / name
            if src_dir.exists():
                dst_dir.mkdir(parents=True, exist_ok=True)
                for adapter_file in src_dir.iterdir():
                    if adapter_file.is_file():
                        shutil.copy2(adapter_file, dst_dir / adapter_file.name)
            else:
                print(f"WARNING: Adapter dir missing: {src_dir}")

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
