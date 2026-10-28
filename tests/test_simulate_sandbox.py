"""Tests for the T-04 sandbox simulation harness (scripts/simulate_sandbox.py)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import simulate_sandbox as sim  # noqa: E402


def test_issue_1_golden_path_passes(tmp_path: Path) -> None:
    report = sim.run_issue(1, log_path=tmp_path / "issue1.log")
    assert report.passed, report.violations
    assert report.budget.tool_calls <= sim.MAX_TOOL_CALLS
    assert report.budget.turns <= sim.MAX_TURNS
    assert report.budget.seconds <= sim.MAX_TIME_MINUTES * 60
    assert report.patch_chars > 0
    assert not report.patch_from_fallback
    assert report.protected_in_patch == 0
    assert report.parent_peak <= sim.CONTEXT_TOKENS
    assert report.parent_compactions == 0


def test_issue_2_stress_measures_delegations(tmp_path: Path) -> None:
    report = sim.run_issue(2, log_path=tmp_path / "issue2.log")
    assert report.passed, report.violations
    assert report.stress_cycles >= 10
    assert report.delegation_count == report.stress_cycles * 3
    assert report.parent_peak <= sim.CONTEXT_TOKENS
    assert not report.parent_saturated


def test_issue_3_long_turns_passes(tmp_path: Path) -> None:
    report = sim.run_issue(3, log_path=tmp_path / "issue3.log")
    assert report.passed, report.violations
    assert report.windows["root"].response_headroom == 8192
    assert report.max_turn_by_agent["root"] <= report.windows["root"].max_output_tokens


def test_submit_and_get_status_do_not_count() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    sandbox.call("get_status")
    sandbox.call("submit_patch")
    assert sandbox.budget.tool_calls == 0
    assert sandbox.budget.turns == 2
    assert sandbox.session_ended


def test_read_file_caps() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    result = sandbox.call("read_file", path=sim.FIXTURE_BUG_FILE)
    content = str(result["content"])
    assert len(content) <= sim.READ_FILE_MAX_CHARS
    assert len(content.splitlines()) <= sim.READ_FILE_MAX_LINES


def test_output_cap_counts_truncation() -> None:
    """T04_2: the 5000-char cap must count truncations (counter is live)."""
    sandbox = sim.MockSandbox(sim.build_fixture())
    original = sandbox._dispatch
    sandbox._dispatch = lambda tool, kwargs: {"stdout": "x" * (sim.COMMAND_OUTPUT_CHARS + 500)}  # type: ignore[method-assign]
    result = sandbox.call("run_command", command="anything")
    assert result["truncated"] is True
    assert len(str(result["output"])) == sim.COMMAND_OUTPUT_CHARS
    assert sandbox.command_truncations == 1
    assert len(sandbox.last_output_text) < sim.COMMAND_OUTPUT_CHARS + 500
    sandbox._dispatch = original  # type: ignore[method-assign]


def test_no_submit_fallback_extracts_diff() -> None:
    """T04_6: session ending without submit_patch still yields the diff."""
    sandbox = sim.MockSandbox(sim.build_fixture())
    assert sandbox.diff() == ""  # nothing changed yet
    sandbox.call(
        "edit_file",
        path=sim.FIXTURE_BUG_FILE,
        old_string=sim.FIXTURE_OLD_SNIPPET,
        new_string=sim.FIXTURE_NEW_SNIPPET,
    )
    diff = sandbox.diff()
    assert "divide" in diff
    assert sandbox.changed_protected_paths() == []


def test_read_file_missing_is_json_error() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    result = sandbox.call("read_file", path="nope.py")
    assert "error" in result
    assert sandbox.budget.tool_calls == 1


def test_protected_files_reject_edits() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    edit = sandbox.call("edit_file", path="tests/test_ops.py", old_string="divide", new_string="x")
    assert "error" in edit
    write = sandbox.call("write_file", path="pyproject.toml", content="x")
    assert "error" in write
    assert sandbox.protected_attempts == 2


def test_planted_bug_flips_pytest() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    before = sandbox.call("run_command", command="python -m pytest -q")
    assert before["returncode"] == 1
    sandbox.call(
        "edit_file",
        path=sim.FIXTURE_BUG_FILE,
        old_string=sim.FIXTURE_OLD_SNIPPET,
        new_string=sim.FIXTURE_NEW_SNIPPET,
    )
    after = sandbox.call("run_command", command="python -m pytest -q")
    assert after["returncode"] == 0
    assert "3 passed" in str(after["stdout"])


def test_edit_requires_unique_match() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    result = sandbox.call(
        "edit_file", path=sim.FIXTURE_BUG_FILE, old_string="return a - b", new_string="x"
    )
    assert "error" in result  # 'return a - b' appears in sub() and divide()


def test_patch_strips_protected_files() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    sandbox.call(
        "edit_file",
        path=sim.FIXTURE_BUG_FILE,
        old_string=sim.FIXTURE_OLD_SNIPPET,
        new_string=sim.FIXTURE_NEW_SNIPPET,
    )
    result = sandbox.call("submit_patch")
    patch = str(result["patch"])
    assert "mini_calc/ops.py" in patch
    assert "tests/test_ops.py" not in patch


def test_unknown_command_is_json_error() -> None:
    sandbox = sim.MockSandbox(sim.build_fixture())
    result = sandbox.call("run_command", command="curl http://example.invalid")
    assert "error" in result
    assert sandbox.budget.tool_calls == 1


def test_compaction_triggers_at_threshold() -> None:
    ctx = sim.ContextWindow("test")
    ctx.seed(1000)
    added = ctx.add("a" * 60_000)  # 15000 tokens -> crosses 14336
    assert ctx.compactions == 1
    # post-compaction model: floor + the message that triggered it
    assert ctx.tokens == sim.COMPACTION_FLOOR_TOKENS + added
    assert ctx.peak_tokens == 1000 + added  # high-water mark before compaction
    assert not ctx.saturated


def test_output_window_checks() -> None:
    window = sim.AgentWindow("t", 100, 50)
    assert window.check(sim.TurnProfile(50, 50, "exact")) == []
    assert len(window.check(sim.TurnProfile(51, 40, "think-over"))) == 1
    assert len(window.check(sim.TurnProfile(50, 51, "total-over"))) == 1


def test_windows_loaded_from_real_configs() -> None:
    windows = sim.load_agent_windows()
    assert windows["root"].max_output_tokens == 16384
    assert windows["root"].thinking_budget == 8192
    assert windows["code_analyzer"].max_output_tokens == 4096
    assert windows["verifier"].thinking_budget == 4096
