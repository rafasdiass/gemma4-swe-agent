#!/usr/bin/env python3
"""Validate submission.zip before Kaggle submit.

Also supports ``--dry-run``: validate the repository working tree instead of a
zip, so CI can gate PRs before the package is assembled.

Schema reference: ``swegemma`` / ``adk-submission`` (SandboxedAgentConfig) —
see planning/olimp-gemma4-swe-2026-q4/evidencias/S0_dataset.md.
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

# Adapters are optional in a base-model submission; they become REQUIRED when
# any agent YAML declares ``adapter: <name>`` (T09: adapter is per-agent).
ADAPTER_FILES = [
    "adapters/main_lora/adapter_config.json",
    "adapters/main_lora/adapter_model.safetensors",
    "adapters/tool_lora/adapter_config.json",
    "adapters/tool_lora/adapter_model.safetensors",
]

ALLOWED_MODELS = {
    "gemma-4-31b-it-qat-w4a16-ct",
    "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct",
    "gemma-4-e2b-it-qat-w4a16-ct",
}

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

# Only the root agent may call submit_patch: it terminates the whole session (T09_R2).
ROOT_ONLY_TOOLS = {"submit_patch"}

REQUIRED_AGENT_FIELDS = [
    "name",
    "model",
    "instruction",
    "tools",
    "generate_content_config",
]

# Skills are declared at the root level only (sample_submission confirms).
ROOT_ONLY_FIELDS = ["skills"]

LEGACY_AGENT_FIELDS = ["agent_id", "system_prompt", "sampling", "adapters"]

GCC_ALLOWED_KEYS = {
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "stop_sequences",
    "response_mime_type",
    "seed",
    "thinking_config",
}

GCC_FORBIDDEN_KEYS = {
    "tools",
    "system_instruction",
    "http_options",
    "safety_settings",
    "response_schema",
}

EVAL_BUDGET_KEYS = ["timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns"]
EVAL_BUDGET_BOUNDS = {
    "timeout_seconds": (1, 3600),
    "max_tool_calls": (1, 10000),
    "max_time_minutes": (1, 720),
    "max_turns": (1, 500),
}

LEGACY_EVAL_KEYS = [
    "task_limits",
    "total_budget_seconds",
    "warning_threshold_pct",
    "critical_threshold_pct",
    "ensemble",
]

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


def _parse_yaml_text(text: str) -> object:
    return yaml.load(text, Loader=IncludeLoader)


def _resolve_include(value: object, files: dict[str, str], errors: list[str], where: str) -> object:
    """Resolve an ``!include`` scalar (a path string) to its parsed YAML file.

    Returns the value unchanged when it is already a dict (inline config).
    """
    if not isinstance(value, str):
        return value
    path = value.replace("\\", "/")
    if path not in files:
        errors.append(f"{where}: !include target not found: {path}")
        return None
    parsed = _parse_yaml_text(files[path])
    if not isinstance(parsed, dict):
        errors.append(f"{where}: !include target is not a mapping: {path}")
        return None
    return parsed


def validate_agent_config(
    config: dict,
    files: dict[str, str],
    errors: list[str],
    warnings: list[str],
    where: str = "agent.yaml",
    is_root: bool = True,
) -> None:
    """Check required fields, model variant, tools and skills for one agent."""
    for field in REQUIRED_AGENT_FIELDS:
        if field not in config:
            errors.append(f"{where} missing field: {field}")
    if is_root:
        for field in ROOT_ONLY_FIELDS:
            if field not in config:
                errors.append(f"{where} missing field: {field}")

    for field in LEGACY_AGENT_FIELDS:
        if field in config:
            errors.append(f"{where} uses legacy/unknown field (A-12): {field}")

    model = config.get("model")
    if model is not None and model not in ALLOWED_MODELS:
        errors.append(f"{where} model not in ALLOWED_MODEL_NAMES: {model}")
    elif model is not None:
        print(f"[OK] {where} model: {model}")

    tools = config.get("tools") or []
    if not isinstance(tools, list):
        errors.append(f"{where} tools must be a list")
        tools = []
    for tool in tools:
        if isinstance(tool, str) and tool not in ALLOWED_TOOLS:
            warnings.append(f"{where} potentially unallowed tool: {tool}")
    if not is_root and "submit_patch" in tools:
        errors.append(
            f"{where} declares submit_patch: only the root agent may submit (T09_R2, session ends)"
        )

    # Skills: relative paths that must exist (T09: paths, not bare names)
    skills = config.get("skills") or []
    if isinstance(skills, list):
        for skill in skills:
            if not isinstance(skill, str) or not skill.startswith("skills/"):
                errors.append(
                    f"{where} skills entries must be relative paths like 'skills/<name>': {skill!r}"
                )
            elif f"{skill}/SKILL.md" not in files:
                errors.append(f"{where} skill path has no SKILL.md: {skill}")

    # Sub-agents: LIST of {config_path}, each resolvable and conformant (A-12)
    sub_agents = config.get("sub_agents")
    if sub_agents is not None:
        if not isinstance(sub_agents, list):
            errors.append(f"{where} sub_agents must be a LIST of {{config_path: ...}} (A-12)")
        else:
            for entry in sub_agents:
                if not isinstance(entry, dict) or "config_path" not in entry:
                    errors.append(f"{where} sub_agents entry missing config_path: {entry!r}")
                    continue
                sub_path = str(entry["config_path"]).replace("\\", "/")
                if sub_path not in files:
                    errors.append(f"{where} sub_agents config_path not found: {sub_path}")
                    continue
                sub_config = _parse_yaml_text(files[sub_path])
                if not isinstance(sub_config, dict):
                    errors.append(f"{where} sub_agents config is not a mapping: {sub_path}")
                    continue
                validate_agent_config(
                    sub_config, files, errors, warnings, where=sub_path, is_root=False
                )

    # generate_content_config: inline dict or !include path (T09)
    gcc = config.get("generate_content_config")
    if gcc is not None:
        resolved = _resolve_include(gcc, files, errors, f"{where}.generate_content_config")
        if isinstance(resolved, dict):
            validate_generate_content_config(
                resolved, errors, warnings, where=f"{where}.generate_content_config"
            )


def validate_generate_content_config(
    gcc: dict,
    errors: list[str],
    warnings: list[str],
    where: str = "generate_content_config",
) -> None:
    """Check allowed keys and ranges of a generate_content_config mapping."""
    for key in gcc:
        if key in GCC_FORBIDDEN_KEYS:
            errors.append(f"{where} forbidden key (bypasses sandbox): {key}")
        elif key not in GCC_ALLOWED_KEYS:
            errors.append(f"{where} unknown key (not in allowed_fields): {key}")

    max_output = gcc.get("max_output_tokens")
    if max_output is not None and not (1 <= int(max_output) <= 32768):
        errors.append(f"{where} max_output_tokens out of range 1..32768: {max_output}")

    thinking = gcc.get("thinking_config")
    if thinking is not None:
        if not isinstance(thinking, dict):
            errors.append(f"{where} thinking_config must be a mapping")
        else:
            budget = thinking.get("thinking_budget")
            if budget is not None and not (0 <= int(budget) <= 32768):
                errors.append(f"{where} thinking_budget out of range 0..32768: {budget}")

    stop_sequences = gcc.get("stop_sequences") or []
    if "```" in stop_sequences:
        warnings.append(
            f"{where} stop_sequences contains '```' (T09_R1: truncates edit_file payloads mid-argument)"
        )


def validate_eval_config(eval_text: str, errors: list[str], warnings: list[str]) -> None:
    """Check the root eval_config.yaml: `evaluation:` key with sane budgets."""
    config = _parse_yaml_text(eval_text)
    if not isinstance(config, dict):
        errors.append("eval_config.yaml is not a mapping")
        return

    for key in LEGACY_EVAL_KEYS:
        if key in config:
            errors.append(
                f"eval_config.yaml uses legacy key (A-12, budgets are per-task now): {key}"
            )

    evaluation = config.get("evaluation")
    if not isinstance(evaluation, dict):
        errors.append("eval_config.yaml missing top-level 'evaluation:' mapping")
        return

    for key in EVAL_BUDGET_KEYS:
        value = evaluation.get(key)
        if value is None:
            errors.append(f"eval_config.yaml evaluation.{key} missing")
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"eval_config.yaml evaluation.{key} must be numeric: {value!r}")
            continue
        low, high = EVAL_BUDGET_BOUNDS[key]
        if not (low <= value <= high):
            errors.append(f"eval_config.yaml evaluation.{key} out of range {low}..{high}: {value}")


def _declared_adapters(files: dict[str, str]) -> list[str]:
    """Collect adapter names declared by any agent YAML (root + sub-agents)."""
    declared: list[str] = []
    for path, text in files.items():
        if not (path == "agent.yaml" or path.startswith("sub_agents/")):
            continue
        config = _parse_yaml_text(text)
        if isinstance(config, dict) and isinstance(config.get("adapter"), str):
            declared.append(config["adapter"])
    return declared


def validate_tree(
    files: dict[str, str],
    required_present: set[str],
    mode: str,
) -> tuple[bool, list[str], list[str]]:
    """Shared validation over a file map (zip entries or repo working tree).

    ``files`` maps relative paths to text content (only YAML/eval files).
    ``required_present`` is the set every REQUIRED_FILES entry must belong to.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for req in REQUIRED_FILES:
        if req in required_present:
            print(f"[OK] {req}")
        else:
            errors.append(f"Missing required file: {req}")

    agent_text = files.get("agent.yaml")
    if agent_text is not None:
        config = _parse_yaml_text(agent_text)
        if isinstance(config, dict):
            validate_agent_config(config, files, errors, warnings, where="agent.yaml", is_root=True)
            for pattern in PROHIBITED_PATTERNS:
                if pattern in agent_text:
                    warnings.append(f"Potentially prohibited pattern in agent.yaml: {pattern}")
        else:
            errors.append("agent.yaml is not a mapping")
    else:
        errors.append("Missing required file: agent.yaml")

    eval_text = files.get("eval_config.yaml")
    if eval_text is not None:
        validate_eval_config(eval_text, errors, warnings)
    else:
        errors.append("Missing required file: eval_config.yaml")

    for sub_path, text in files.items():
        if sub_path.startswith("sub_agents/"):
            for pattern in PROHIBITED_PATTERNS:
                if pattern in text:
                    warnings.append(f"Potentially prohibited pattern in {sub_path}: {pattern}")

    # Adapters: error only when some YAML declares one (T09: per-agent, optional on base model)
    declared = _declared_adapters(files)
    if declared:
        for name in declared:
            for adapter_file in ("adapter_config.json", "adapter_model.safetensors"):
                path = f"adapters/{name}/{adapter_file}"
                if path in required_present:
                    print(f"[OK] {path}")
                else:
                    errors.append(f"Agent declares adapter '{name}' but file missing: {path}")
    elif mode == "zip":
        warnings.append("No LoRA adapters declared: base-model submission")
    else:
        warnings.append("Adapters not built yet (expected pre-submission, T03_ADAPTER_ABSENT)")

    return len(errors) == 0, errors, warnings


def validate_zip(zip_path: Path) -> tuple[bool, list[str], list[str]]:
    """Validate submission.zip structure and contents."""
    errors: list[str] = []
    warnings: list[str] = []

    if not zip_path.exists():
        return False, [f"File not found: {zip_path}"], []

    size_mb = zip_path.stat().st_size / 1024 / 1024
    if size_mb > 3072:
        errors.append(f"Submission size: {size_mb:.1f}MB (exceeds 3 GiB harness limit)")
    elif size_mb > 1024:
        warnings.append(f"Submission size: {size_mb:.1f}MB (>1GB, watch the 3 GiB limit)")
    else:
        print(f"[OK] Size: {size_mb:.1f}MB")

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = set(zf.namelist())
        files = {
            name: zf.read(name).decode("utf-8")
            for name in namelist
            if name in ("agent.yaml", "eval_config.yaml")
            or name.startswith(("configs/", "sub_agents/", "skills/"))
        }
        skill_files = [f for f in namelist if f.startswith("skills/") and f.endswith("SKILL.md")]
        if skill_files:
            print(f"[OK] Skills found: {len(skill_files)}")
        else:
            warnings.append("No skills found")

    return validate_tree(files, namelist, mode="zip")


def collect_repo_files(base_path: Path) -> dict[str, str]:
    """Read the YAML/SKILL files the validator needs from the working tree."""
    files: dict[str, str] = {}
    rels = [
        "agent.yaml",
        "eval_config.yaml",
        "configs/sampling.yaml",
        *[p.relative_to(base_path).as_posix() for p in (base_path / "sub_agents").glob("*.yaml")],
        *[p.relative_to(base_path).as_posix() for p in base_path.glob("skills/*/SKILL.md")],
    ]
    for rel in rels:
        full = base_path / rel
        if full.exists():
            files[rel] = full.read_text(encoding="utf-8")
    return files


def validate_repo(base_path: Path) -> tuple[bool, list[str], list[str]]:
    """Validate the repository working tree (dry-run mode, no zip required)."""
    files = collect_repo_files(base_path)
    required_present = {req for req in REQUIRED_FILES if (base_path / req).exists()}
    skill_count = len(list(base_path.glob("skills/*/SKILL.md")))
    if skill_count:
        print(f"[OK] Skills found: {skill_count}")
    else:
        pass  # reported as warning by validate_tree via skills check in agent config
    return validate_tree(files, required_present, mode="repo")


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
