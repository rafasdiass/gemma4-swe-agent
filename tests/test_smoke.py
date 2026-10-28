"""Smoke tests: repo structure parses and core script imports cleanly."""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_submission  # noqa: E402

LEGACY_FIELDS = {"agent_id", "system_prompt", "sampling", "adapters"}


def _load_agent_config() -> dict:
    agent_yaml = REPO_ROOT / "agent.yaml"
    config = yaml.load(
        agent_yaml.read_text(encoding="utf-8"), Loader=validate_submission.IncludeLoader
    )
    assert isinstance(config, dict)
    return config


def _load_sub_agents() -> dict[str, dict]:
    sub_agents = {}
    for yaml_path in (REPO_ROOT / "sub_agents").glob("*.yaml"):
        loaded = yaml.load(
            yaml_path.read_text(encoding="utf-8"), Loader=validate_submission.IncludeLoader
        )
        assert isinstance(loaded, dict), f"unparseable: {yaml_path.name}"
        sub_agents[yaml_path.name] = loaded
    return sub_agents


def test_agent_yaml_parses() -> None:
    assert isinstance(_load_agent_config(), dict)


def test_agent_yaml_required_fields() -> None:
    config = _load_agent_config()
    for field in ("name", "model", "instruction", "tools", "skills", "generate_content_config"):
        assert field in config, f"agent.yaml missing field: {field}"


def test_agent_yaml_no_legacy_fields() -> None:
    configs = [_load_agent_config(), *_load_sub_agents().values()]
    for config in configs:
        legacy = LEGACY_FIELDS & set(config)
        assert not legacy, f"legacy/unknown fields present (A-12): {legacy}"


def test_agent_yaml_model_is_allowed_31b() -> None:
    config = _load_agent_config()
    assert config["model"] in validate_submission.ALLOWED_MODELS
    assert "31b" in str(config["model"]).lower()


def test_agent_yaml_tools_are_allowed() -> None:
    config = _load_agent_config()
    assert set(config["tools"]) <= validate_submission.ALLOWED_TOOLS


def test_sub_agents_are_list_of_config_paths() -> None:
    config = _load_agent_config()
    sub_agents = config.get("sub_agents")
    assert isinstance(sub_agents, list), "sub_agents must be a LIST of {config_path} (A-12)"
    for entry in sub_agents:
        assert isinstance(entry, dict) and "config_path" in entry
        sub_path = REPO_ROOT / str(entry["config_path"])
        assert sub_path.exists(), f"sub_agents config not found: {sub_path}"
        loaded = yaml.load(
            sub_path.read_text(encoding="utf-8"), Loader=validate_submission.IncludeLoader
        )
        assert "name" in loaded and "instruction" in loaded
        assert "capabilities" not in loaded, "field outside schema (T09_R4)"
        assert "submit_patch" not in (loaded.get("tools") or []), "only root submits (T09_R2)"


def test_generate_content_config_valid() -> None:
    gcc = _load_agent_config()["generate_content_config"]
    if isinstance(gcc, str):
        gcc = yaml.load(
            (REPO_ROOT / gcc).read_text(encoding="utf-8"), Loader=validate_submission.IncludeLoader
        )
    assert set(gcc) <= validate_submission.GCC_ALLOWED_KEYS, (
        f"unknown keys: {set(gcc) - validate_submission.GCC_ALLOWED_KEYS}"
    )
    assert 1 <= gcc["max_output_tokens"] <= 32768
    assert 0 <= gcc["thinking_config"]["thinking_budget"] <= 32768
    assert "```" not in (gcc.get("stop_sequences") or []), (
        "T09_R1: backtick stop sequence truncates edit_file"
    )


def test_eval_config_at_root() -> None:
    assert (REPO_ROOT / "eval_config.yaml").exists(), (
        "eval_config.yaml must live at submission root (A-12)"
    )
    assert not (REPO_ROOT / "configs" / "eval_config.yaml").exists(), (
        "legacy configs/eval_config.yaml must be gone"
    )
    config = yaml.load(
        (REPO_ROOT / "eval_config.yaml").read_text(encoding="utf-8"),
        Loader=validate_submission.IncludeLoader,
    )
    assert isinstance(config.get("evaluation"), dict), "missing top-level evaluation: mapping"
    for key in ("timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns"):
        assert isinstance(config["evaluation"].get(key), (int, float)), f"evaluation.{key} numeric"


def test_skills_are_relative_paths() -> None:
    config = _load_agent_config()
    for skill in config["skills"]:
        assert skill.startswith("skills/"), f"skills entries must be paths: {skill!r}"
        assert (REPO_ROOT / skill / "SKILL.md").exists(), f"SKILL.md missing for {skill}"


def test_sub_agent_and_config_yamls_parse() -> None:
    assert len(_load_sub_agents()) == 3
    for yaml_path in (REPO_ROOT / "configs").glob("*.yaml"):
        loaded = yaml.load(
            yaml_path.read_text(encoding="utf-8"), Loader=validate_submission.IncludeLoader
        )
        assert isinstance(loaded, dict), f"unparseable: {yaml_path.name}"


def test_validate_submission_dry_run_passes() -> None:
    valid, errors, _warnings = validate_submission.validate_repo(REPO_ROOT)
    assert valid, f"dry-run errors: {errors}"
