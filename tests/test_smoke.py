"""Smoke tests: repo structure parses and core script imports cleanly."""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_submission  # noqa: E402


def test_agent_yaml_parses() -> None:
    config = validate_submission._load_agent_config()
    assert isinstance(config, dict)


def test_agent_yaml_required_fields() -> None:
    config = validate_submission._load_agent_config()
    for field in ("agent_id", "model", "tools", "sub_agents", "adapters", "skills"):
        assert field in config, f"agent.yaml missing field: {field}"


def test_agent_yaml_model_is_gemma4_31b() -> None:
    config = validate_submission._load_agent_config()
    assert "gemma-4" in str(config["model"])
    assert "31b" in str(config["model"]).lower()


def test_agent_yaml_tools_are_allowed() -> None:
    config = validate_submission._load_agent_config()
    assert set(config["tools"]) <= validate_submission.ALLOWED_TOOLS


def test_sub_agent_yamls_parse() -> None:
    for yaml_path in (REPO_ROOT / "sub_agents").glob("*.yaml"):
        text = yaml_path.read_text(encoding="utf-8")
        loaded = yaml.load(text, Loader=validate_submission.IncludeLoader)
        assert isinstance(loaded, dict), f"unparseable: {yaml_path.name}"


def test_config_yamls_parse() -> None:
    for yaml_path in (REPO_ROOT / "configs").glob("*.yaml"):
        loaded = yaml.load(
            yaml_path.read_text(encoding="utf-8"), Loader=validate_submission.IncludeLoader
        )
        assert isinstance(loaded, dict), f"unparseable: {yaml_path.name}"


def test_validate_submission_dry_run_passes() -> None:
    valid, errors, _warnings = validate_submission.validate_repo(REPO_ROOT)
    assert valid, f"dry-run errors: {errors}"
