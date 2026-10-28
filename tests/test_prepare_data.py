"""Tests for the T-07 SFT pair builder (scripts/prepare_data.py).

All fixtures are SYNTHETIC: the mini-zip is built in tmp_path with fake repos,
fake issues and fake patches. No Competition Data is ever used here (hard rule
for this public repo).
"""

import io
import json
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import prepare_data as prep  # noqa: E402

CORE_PY = (
    "from widgets.helpers import make_hash\n"
    "\n"
    "\n"
    "def run(widget: str) -> str:\n"
    "    return make_hash(widget)\n"
)

HELPERS_PY = "def make_hash(value: str) -> str:\n    return value + '!'\n"

PATCH_1 = (
    "diff --git a/src/widgets/core.py b/src/widgets/core.py\n"
    "--- a/src/widgets/core.py\n"
    "+++ b/src/widgets/core.py\n"
    "@@ -1,3 +1,5 @@\n"
    "+FIX = True\n"
)

PATCH_7 = (
    "diff --git a/gears/engine.py b/gears/engine.py\n"
    "--- a/gears/engine.py\n"
    "+++ b/gears/engine.py\n"
    "@@ -1 +1,2 @@\n"
    "+SPEED = 11\n"
)


def _task(
    instance_id: str,
    repo: str,
    patch: str,
    problem: str = "Widget crashes when hashed twice.",
    hints: str = "hint words here",
) -> dict[str, str]:
    return {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": "0000000000000000000000000000000000000000",
        "patch": patch,
        "test_patch": "synthetic",
        "problem_statement": problem,
        "hints_text": hints,
        "created_at": "2026-01-01T00:00:00",
    }


def _add_tgz(archive: zipfile.ZipFile, entry: str, files: dict[str, str]) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    archive.writestr(entry, buf.getvalue())


@pytest.fixture()
def dataset_zip(tmp_path: Path) -> Path:
    """Synthetic mini-zip: 7 tasks covering every pipeline branch."""
    tasks = [
        _task("acme__widgets-1", "acme/widgets", PATCH_1),
        _task("acme__widgets-2", "acme/widgets", PATCH_1),  # duplicate pair
        _task("acme__widgets-3", "acme/widgets", ""),  # empty patch
        {"instance_id": "acme__widgets-4", "repo": "acme/widgets"},  # schema invalid
        _task("acme__widgets-5", "acme/orphans", PATCH_1),  # no snapshot
        _task("acme__widgets-6", "acme/widgets", PATCH_7),  # touched file absent
        _task("acme__gears-7", "acme/gears", PATCH_7),
    ]
    zip_path = tmp_path / "dataset.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "data/tasks.jsonl",
            "\n".join(json.dumps(t) for t in tasks) + "\n",
        )
        _add_tgz(
            archive,
            "snapshots/acme__widgets-1.tgz",
            {
                "repo/src/widgets/core.py": CORE_PY,
                "repo/widgets/helpers.py": HELPERS_PY,
            },
        )
        # duplicate task resolves its snapshot via the repo-slug fallback
        _add_tgz(
            archive,
            "snapshots/acme_widgets.tgz",
            {"repo/src/widgets/core.py": CORE_PY},
        )
        _add_tgz(
            archive,
            "snapshots/acme__widgets-6.tgz",
            {"repo/docs/notes.md": "unrelated"},
        )
        _add_tgz(
            archive,
            "snapshots/acme__gears-7.tgz",
            {"repo/gears/engine.py": "RPM = 3\n"},
        )
    return zip_path


def _run(zip_path: Path, out: Path, **overrides: object) -> dict[str, object]:
    cfg_kwargs: dict[str, object] = {
        "zip_path": zip_path,
        "out_dir": out,
        "limit": None,
        "max_context_chars": 60_000,
        "per_file_chars": 8_000,
        "include_hints": False,
    }
    cfg_kwargs.update(overrides)
    cfg = prep.Config(**cfg_kwargs)  # type: ignore[arg-type]
    return prep.run(cfg, io.StringIO())


def _read_pairs(out: Path) -> list[dict[str, object]]:
    lines = (out / "pairs.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_end_to_end_counts(dataset_zip: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    summary = _run(dataset_zip, out)
    assert summary["tasks_read"] == 7
    assert summary["pairs_emitted"] == 2
    assert summary["discarded_total"] == 5
    assert summary["discarded_by_reason"] == {
        "patch_vazio": 1,
        "schema_invalid": 1,
        "sem_snapshot": 1,
        "sem_contexto": 1,
        "duplicado": 1,
    }
    pairs = _read_pairs(out)
    assert len(pairs) == 2


def test_zero_pairs_with_empty_patch(dataset_zip: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    _run(dataset_zip, out)
    for pair in _read_pairs(out):
        messages = pair["messages"]
        assert isinstance(messages, list)
        assistant = messages[-1]
        assert assistant["role"] == "assistant"
        assert isinstance(assistant["content"], str)
        assert assistant["content"].strip() != ""


def test_pair_schema_is_chat_format(dataset_zip: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    _run(dataset_zip, out)
    pair = _read_pairs(out)[0]
    assert set(pair.keys()) == {"id", "instance_id", "repo", "messages", "meta"}
    roles = [m["role"] for m in pair["messages"]]  # type: ignore[index]
    assert roles == ["system", "user", "assistant"]
    assert str(pair["id"]).startswith("sft-")
    meta = pair["meta"]
    assert isinstance(meta, dict)
    assert meta["n_context_files"] >= 1
    assert meta["est_tokens"] > 0


def test_context_selection_touched_file_and_import_neighbor(
    dataset_zip: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    _run(dataset_zip, out)
    pairs = _read_pairs(out)
    user = next(
        m["content"]
        for p in pairs
        for m in p["messages"]  # type: ignore[union-attr]
        if m["role"] == "user" and "widgets" in str(p["repo"])  # type: ignore[index]
    )
    assert isinstance(user, str)
    assert "=== FILE: src/widgets/core.py ===" in user
    assert "=== FILE: widgets/helpers.py ===" in user
    assert "[HINTS]" not in user


def test_include_hints_flag(dataset_zip: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    _run(dataset_zip, out, limit=1, include_hints=True)
    pair = _read_pairs(out)[0]
    user = pair["messages"][1]["content"]  # type: ignore[index]
    assert isinstance(user, str)
    assert "[HINTS]" in user
    assert "hint words here" in user


def test_context_budget_truncates_and_drops_neighbor(dataset_zip: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    _run(
        dataset_zip,
        out,
        limit=1,
        max_context_chars=100,
        per_file_chars=60,
    )
    pair = _read_pairs(out)[0]
    user = pair["messages"][1]["content"]  # type: ignore[index]
    assert isinstance(user, str)
    assert "[truncated by prepare_data]" in user
    assert "widgets/helpers.py" not in user


def test_limit_emits_at_most_n(dataset_zip: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    summary = _run(dataset_zip, out, limit=1)
    assert summary["pairs_emitted"] == 1
    assert summary["tasks_read"] == 1


def test_summary_contains_no_competition_content(dataset_zip: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    _run(dataset_zip, out)
    text = (out / "summary.json").read_text(encoding="utf-8")
    assert "acme__widgets" not in text
    assert "acme/gears" not in text
    assert "crashes" not in text


def test_dedup_hash_is_whitespace_stable() -> None:
    assert prep.pair_hash("a  b\nc", "x\ny") == prep.pair_hash("a b c", "x y")


def test_touched_files_from_patch_order_and_devnull() -> None:
    patch = (
        "diff --git a/a.py b/a.py\n"
        "+++ b/a.py\n"
        "diff --git a/b.py b/b.py\n"
        "--- /dev/null\n"
        "+++ b/b.py\n"
    )
    assert prep.touched_files_from_patch(patch) == ["a.py", "b.py"]


def test_snapshot_matching_by_repo_slug(dataset_zip: Path, tmp_path: Path) -> None:
    with zipfile.ZipFile(dataset_zip, "r") as archive:
        index = prep.SnapshotIndex(archive)
        record = prep.TaskRecord(
            instance_id="acme__widgets-2",
            repo="acme/widgets",
            base_commit="",
            patch=PATCH_1,
            problem_statement="x",
            hints_text="",
        )
        entry = index.find(record)
    assert entry == "snapshots/acme_widgets.tgz"


def test_ensure_outside_repo_refuses_repo_paths() -> None:
    with pytest.raises(SystemExit):
        prep.ensure_outside_repo(REPO_ROOT / "data" / "sft_pairs")
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        prep.ensure_outside_repo(Path(tmp))
