#!/usr/bin/env python3
"""Validate submission.zip before Kaggle submit.

Also supports ``--dry-run``: validate the repository working tree instead of a
zip, so CI can gate PRs before the package is assembled.
"""

import argparse
import sys
import zipfile
from pathlib import Path

import yaml


class IncludeLoader(yaml.SafeLoader):
    """SafeLoader that tolerates the custom ``!include`` tag used by agent.yaml.

    Competition harness configs reference other files via ``!include path``;
    for validation purposes the tag resolves to the path string itself.
    """


IncludeLoader.add_constructor(
    "!include",
    lambda loader, node: loader.construct_scalar(node),
)

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

# Adapters are produced by train_lora.py at submission time; their absence in
# the working tree is expected until then (T03_ADAPTER_ABSENT) and only a
# warning in dry-run mode. Inside a zip they are mandatory.
ADAPTER_PREFIX = "adapters/"

ALLOWED_TOOLS = {
    "run_command",
    "read_file",
    "edit_file",
    "write_file",
    "submit_patch",
    "get_code_neighbors",
    "search_similar_code",
    "get_code_subgraph",
    "get_status",
}

PROHIBITED_PATTERNS = [
    "requests",
    "httpx",
    "wget",
    "curl",
    "git clone",
    "pip install",
    "import os",
    "subprocess",
]


def validate_agent_config(config: dict, errors: list[str], warnings: list[str]) -> None:
    """Check required fields, model variant and allowed tools in agent.yaml."""
    required_fields = ["agent_id", "model", "tools", "sub_agents", "adapters", "skills"]
    for field in required_fields:
        if field not in config:
            errors.append(f"agent.yaml missing field: {field}")

    model = config.get("model")
    if model is not None and "gemma-4" not in str(model):
        errors.append(f"Model must be Gemma 4 variant: {model}")
    else:
        print(f"[OK] Model: {model}")

    tools = config.get("tools") or []
    for tool in tools:
        if tool not in ALLOWED_TOOLS:
            warnings.append(f"Potentially unallowed tool: {tool}")


def validate_zip(zip_path: Path) -> tuple[bool, list[str], list[str]]:
    """Validate submission.zip structure and contents."""
    errors: list[str] = []
    warnings: list[str] = []

    if not zip_path.exists():
        return False, [f"File not found: {zip_path}"], []

    size_mb = zip_path.stat().st_size / 1024 / 1024
    if size_mb > 1024:
        warnings.append(f"Submission size: {size_mb:.1f}MB (>1GB may exceed Kaggle limits)")
    else:
        print(f"[OK] Size: {size_mb:.1f}MB")

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()

        for req in REQUIRED_FILES:
            if req in namelist:
                print(f"[OK] {req}")
            else:
                errors.append(f"Missing required file: {req}")

        skill_files = [f for f in namelist if f.startswith("skills/") and f.endswith("SKILL.md")]
        if skill_files:
            print(f"[OK] Skills found: {len(skill_files)}")
        else:
            warnings.append("No skills found")

        adapter_files = [f for f in namelist if "adapter_model.safetensors" in f]
        if adapter_files:
            print(f"[OK] LoRA adapters: {len(adapter_files)}")
        else:
            errors.append("No LoRA adapter weights found")

        if "agent.yaml" in namelist:
            with zf.open("agent.yaml") as f:
                config = yaml.load(f, Loader=IncludeLoader)
            if isinstance(config, dict):
                validate_agent_config(config, errors, warnings)

            content = zf.read("agent.yaml").decode()
            for pattern in PROHIBITED_PATTERNS:
                if pattern in content:
                    warnings.append(f"Potentially prohibited pattern in agent.yaml: {pattern}")

    return len(errors) == 0, errors, warnings


def _load_agent_config() -> dict:
    """Load agent.yaml from the repo root, tolerating ``!include`` tags."""
    agent_yaml = Path(__file__).resolve().parent.parent / "agent.yaml"
    config = yaml.load(agent_yaml.read_text(encoding="utf-8"), Loader=IncludeLoader)
    assert isinstance(config, dict)
    return config


def validate_repo(base_path: Path) -> tuple[bool, list[str], list[str]]:
    """Validate the repository working tree (dry-run mode, no zip required)."""
    errors: list[str] = []
    warnings: list[str] = []

    for req in REQUIRED_FILES:
        if (base_path / req).exists():
            print(f"[OK] {req}")
        elif req.startswith(ADAPTER_PREFIX):
            warnings.append(f"Adapter not built yet (expected pre-submission): {req}")
        else:
            errors.append(f"Missing required file: {req}")

    skill_files = sorted(base_path.glob("skills/*/SKILL.md"))
    if skill_files:
        print(f"[OK] Skills found: {len(skill_files)}")
    else:
        warnings.append("No skills found")

    agent_yaml = base_path / "agent.yaml"
    if agent_yaml.exists():
        config = yaml.load(agent_yaml.read_text(encoding="utf-8"), Loader=IncludeLoader)
        if isinstance(config, dict):
            validate_agent_config(config, errors, warnings)
            content = agent_yaml.read_text(encoding="utf-8")
            for pattern in PROHIBITED_PATTERNS:
                if pattern in content:
                    warnings.append(f"Potentially prohibited pattern in agent.yaml: {pattern}")
    else:
        errors.append("Missing required file: agent.yaml")

    return len(errors) == 0, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate submission.zip for Kaggle")
    parser.add_argument(
        "zip_path", nargs="?", default="submission.zip", help="Path to submission.zip"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate the repo working tree instead of a zip"
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    if args.dry_run:
        target = Path.cwd()
        print(f"Dry-run validating repo at: {target}")
    else:
        target = Path(args.zip_path).resolve()
        print(f"Validating: {target}")
    print("=" * 50)

    if args.dry_run:
        valid, errors, warnings = validate_repo(target)
    else:
        valid, errors, warnings = validate_zip(target)

    print("\n" + "=" * 50)
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  [WARN] {w}")

    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  [X] {e}")

    print("\n" + "=" * 50)
    if valid and not (args.strict and warnings):
        print("[OK] VALIDATION PASSED")
        return 0
    print("[X] VALIDATION FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
