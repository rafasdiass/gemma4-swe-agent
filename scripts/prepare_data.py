#!/usr/bin/env python3
"""T-07 -- Build SFT chat pairs (issue -> gold patch) from the official dataset zip.

Reads 'tasks.jsonl' in streaming fashion directly from the competition zip
(no full extraction) and emits JSONL chat-format pairs to an output directory
OUTSIDE this repository.

HARD RULE (public repo): no Competition Data may land in the repo. This script
contains ONLY logic; every emitted pair (issue text, patch text, snapshot file
content) is written exclusively to --out. The summary file written next to the
pairs contains aggregate numbers only -- no instance ids, no content. The
script also refuses to write when --out resolves inside the repository.

OUTPUT PAIR SCHEMA (one JSON object per line in '<out>/pairs.jsonl'):

    {
      "id": "sft-<first 16 hex of dedup hash>",
      "instance_id": "<dataset instance id (metadata, never committed)>",
      "repo": "<repo slug>",
      "messages": [
        {"role": "system", "content": "<fixed instruction>"},
        {"role": "user", "content": "[ISSUE] ... + [REPO CONTEXT] file blocks"},
        {"role": "assistant", "content": "<gold patch diff, verbatim>"}
      ],
      "meta": {
        "n_context_files": <int>,
        "context_chars": <int>,
        "est_tokens": <int>,
        "dedup_hash": "<sha256 hex>"
      }
    }

CONTEXT SELECTION STRATEGY (documented decision):
  1. Files touched by the gold patch (parsed from '+++ b/<path>' and
     'diff --git' headers) are read from the repo snapshot '.tgz' inside the
     zip -- base (pre-patch) versions, which is what the model must see.
  2. Import neighborhood: 'import' / 'from X import' statements found in the
     touched files are resolved against the snapshot file index and added
     while the character budget lasts (lower priority than touched files;
     only when at least MIN_NEIGHBOR_BUDGET chars remain).
  3. Budget: --max-context-chars (default 60000, ~15k tokens at chars/4)
     total, --per-file-chars (default 8000) per file, greedy fill in
     patch-touch order. Content is truncated at the cap with a marker line.
  4. hints_text is EXCLUDED by default: at eval time the agent sees only the
     issue, so the SFT distribution should match (opt in via --include-hints).

SNAPSHOT MATCHING: zip entries ending in '.tgz' are matched to a task by
normalized substring of the instance_id first, then the repo slug. Inside the
tar, paths are matched by suffix so any leading directory prefix (e.g.
'repo-<name>/') is tolerated.

DEDUP: sha256 over normalized (whitespace-collapsed) issue text + normalized
patch text. First occurrence wins; duplicates are counted, not emitted.

ZERO EMPTY-PATCH INVARIANT: lines whose gold patch is empty/missing are
discarded with reason 'patch_vazio' and counted -- never emitted.

CEILING JUSTIFICATION (DoD: '>= 1000 valid pairs OR justification of the real
ceiling'): the dataset has exactly 129 SWE-bench-style tasks, each with ONE
gold patch. The honest ceiling is therefore 129 pairs (minus discards for
empty patches and duplicates) -- far below 1000. Fabricating pairs (splitting
patches, paraphrasing issues) would poison SFT with synthetic supervision and
is forbidden by design. Mitigations deferred to S1 (also recorded in the
summary): context augmentation (multiple context-subset variants per pair),
multi-epoch LoRA on the small set, or accepting a light few-shot/LoRA
configuration sized for ~100 examples. This script NEVER invents pairs.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import tarfile
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

DEFAULT_ZIP = Path(r"C:\gemma4-data\gemma-4-developer-agent.zip")
DEFAULT_OUT = Path(r"C:\gemma4-data\sft_pairs")
DEFAULT_MAX_CONTEXT_CHARS = 60_000
DEFAULT_PER_FILE_CHARS = 8_000
CHARS_PER_TOKEN = 4
# A neighbor file smaller than this budget is noise, not signal: only fetch
# import neighbors when at least this many chars of context budget remain.
MIN_NEIGHBOR_BUDGET = 1_000

SYSTEM_PROMPT = (
    "You are an expert software engineer. You are given a GitHub issue and the "
    "relevant files of a repository snapshot. Produce a unified diff patch that "
    "resolves the issue. Reply with the patch only."
)

RE_DIFF_GIT = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)
RE_PLUS_PLUS = re.compile(r"^\+\+\+ (?:b/)?(\S+)", re.MULTILINE)
RE_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import\s|import\s+([\w.]+))", re.MULTILINE)
_TRUNCATION_MARKER = "\n... [truncated by prepare_data]\n"


class SchemaError(ValueError):
    """A tasks.jsonl line does not conform to the documented schema."""


@dataclass(frozen=True)
class TaskRecord:
    instance_id: str
    repo: str
    base_commit: str
    patch: str
    problem_statement: str
    hints_text: str


@dataclass(frozen=True)
class Config:
    zip_path: Path
    out_dir: Path
    limit: int | None
    max_context_chars: int
    per_file_chars: int
    include_hints: bool


@dataclass(frozen=True)
class BuiltPair:
    payload: dict[str, object]
    dedup_hash: str
    est_tokens: int


@dataclass
class Stats:
    tasks_read: int = 0
    emitted: int = 0
    discarded: Counter[str] = field(default_factory=Counter)
    token_sizes: list[int] = field(default_factory=list)


def normalize_text(text: str) -> str:
    """Collapse all whitespace runs so hashes are stable across trivial diffs."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_key(text: str) -> str:
    """Alphanumeric-only lowercase key for fuzzy name matching."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def normalize_path_key(path: str) -> str:
    """Lowercase path key that keeps '/' so suffix matching stays positional."""
    return re.sub(r"[^a-z0-9/]+", "", path.lower())


def pair_hash(problem_statement: str, patch: str) -> str:
    payload = normalize_text(problem_statement) + "\x00" + normalize_text(patch)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_task_line(raw: str) -> TaskRecord:
    """Validate one tasks.jsonl line against the documented schema.

    Raises SchemaError when required fields are missing or not strings. An
    empty patch is NOT a schema error: it has its own discard reason
    ('patch_vazio') downstream, so it stays visible in the metrics.
    """
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"invalid json: {exc}") from exc
    if not isinstance(obj, dict):
        raise SchemaError("line is not a json object")
    for field_name in ("instance_id", "repo", "patch", "problem_statement"):
        value = obj.get(field_name)
        if not isinstance(value, str):
            raise SchemaError(f"field {field_name!r} missing or not a string")
        if field_name != "patch" and not value.strip():
            raise SchemaError(f"field {field_name!r} is empty")
    hints = obj.get("hints_text", "")
    base = obj.get("base_commit", "")
    if not isinstance(hints, str):
        hints = ""
    if not isinstance(base, str):
        base = ""
    return TaskRecord(
        instance_id=obj["instance_id"],
        repo=obj["repo"],
        base_commit=base,
        patch=obj["patch"],
        problem_statement=obj["problem_statement"],
        hints_text=hints,
    )


def touched_files_from_patch(patch: str) -> list[str]:
    """Extract repo-relative file paths touched by a unified diff, in order."""
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        if path in ("", "/dev/null") or path in seen:
            return
        seen.add(path)
        paths.append(path)

    for match in RE_DIFF_GIT.finditer(patch):
        add(match.group(2))
    for match in RE_PLUS_PLUS.finditer(patch):
        add(match.group(1))
    return paths


def percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    rank = max(1, round(pct / 100 * len(sorted_values)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


class SnapshotIndex:
    """Index of '.tgz' repo snapshots inside the competition zip."""

    def __init__(self, archive: zipfile.ZipFile) -> None:
        self._archive = archive
        self.entries: list[str] = [name for name in archive.namelist() if name.endswith(".tgz")]
        self._by_key: dict[str, str] = {}
        for entry in self.entries:
            stem = entry.rsplit("/", 1)[-1][: -len(".tgz")]
            self._by_key.setdefault(normalize_key(stem), entry)

    def find(self, record: TaskRecord) -> str | None:
        by_id = normalize_key(record.instance_id)
        by_repo = normalize_key(record.repo)
        if by_id and by_id in self._by_key:
            return self._by_key[by_id]
        if by_repo and by_repo in self._by_key:
            return self._by_key[by_repo]
        for key, entry in self._by_key.items():
            if by_id and by_id in key:
                return entry
            if by_repo and by_repo in key:
                return entry
        return None

    def read_files(
        self,
        entry: str,
        wanted: list[str],
        budget_chars: int,
        per_file_chars: int,
    ) -> dict[str, str]:
        """Read wanted paths from the snapshot tar within the char budget.

        Single walk over the tar: each member is suffix-matched against the
        wanted paths and read on the fly. Returns '{requested_path: content}'
        keyed by the REQUESTED repo-relative path (not the tar-internal name).
        """
        result: dict[str, str] = {}
        if budget_chars <= 0 or not wanted:
            return result
        wanted_keys = {normalize_path_key(w): w for w in wanted}
        remaining = budget_chars
        with tarfile.open(fileobj=self._archive.open(entry, "r"), mode="r:*") as tar:
            for member in tar:
                if remaining <= 0:
                    break
                if not member.isfile():
                    continue
                key = normalize_path_key(member.name)
                matched = wanted_keys.get(key)
                if matched is None:
                    for wanted_key, original in wanted_keys.items():
                        if key.endswith("/" + wanted_key):
                            matched = original
                            break
                if matched is None or matched in result:
                    continue
                cap = min(per_file_chars, remaining)
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                content = extracted.read(cap + 1).decode("utf-8", errors="replace")
                if len(content) > cap:
                    content = content[:cap] + _TRUNCATION_MARKER
                result[matched] = content
                remaining -= len(content)
        return result

    def all_paths(self, entry: str) -> list[str]:
        with tarfile.open(fileobj=self._archive.open(entry, "r"), mode="r:*") as tar:
            return [member.name for member in tar if member.isfile()]


def import_neighbors(
    contents: dict[str, str],
    available_paths: list[str],
    exclude: set[str],
) -> list[str]:
    """Resolve import statements in selected files to snapshot-relative paths.

    Returns candidate paths in REQUESTED (repo-relative) form; the tar suffix
    matching in read_files resolves any directory prefix later.
    """
    available_keys = [normalize_path_key(p) for p in available_paths]
    candidates: list[str] = []
    seen: set[str] = set(exclude)
    for content in contents.values():
        for match in RE_IMPORT.finditer(content):
            module = (match.group(1) or match.group(2) or "").split(",")[0].strip()
            if not module or module.startswith("."):
                continue
            parts = module.split(".")
            for candidate in (
                "/".join(parts) + ".py",
                "/".join(parts) + "/__init__.py",
            ):
                key = normalize_path_key(candidate)
                hit = any(k == key or k.endswith("/" + key) for k in available_keys)
                if hit and candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)
    return candidates


def build_user_content(
    record: TaskRecord,
    context_files: dict[str, str],
    include_hints: bool,
) -> str:
    blocks: list[str] = ["[ISSUE]", record.problem_statement.strip()]
    if include_hints and record.hints_text.strip():
        blocks.extend(["", "[HINTS]", record.hints_text.strip()])
    blocks.extend(
        [
            "",
            "[REPO CONTEXT] repo="
            + record.repo
            + " base_commit="
            + (record.base_commit or "unknown"),
        ]
    )
    for path, content in context_files.items():
        blocks.extend(["", "=== FILE: " + path + " ===", content])
    return "\n".join(blocks)


def build_pair(
    record: TaskRecord,
    snapshots: SnapshotIndex,
    cfg: Config,
) -> tuple[BuiltPair | None, str]:
    """Return (pair, '') on success or (None, discard_reason)."""
    patch = record.patch.strip()
    if not patch:
        return None, "patch_vazio"

    entry = snapshots.find(record)
    if entry is None:
        return None, "sem_snapshot"

    touched = touched_files_from_patch(patch)
    if not touched:
        return None, "sem_contexto"

    context_files = snapshots.read_files(entry, touched, cfg.max_context_chars, cfg.per_file_chars)
    if not context_files:
        return None, "sem_contexto"

    remaining = cfg.max_context_chars - sum(len(c) for c in context_files.values())
    if remaining >= MIN_NEIGHBOR_BUDGET:
        available = snapshots.all_paths(entry)
        neighbors = import_neighbors(context_files, available, set(context_files))
        extra = snapshots.read_files(entry, neighbors, remaining, cfg.per_file_chars)
        context_files.update(extra)

    user_content = build_user_content(record, context_files, cfg.include_hints)
    dedup = pair_hash(record.problem_statement, patch)
    est_tokens = (len(SYSTEM_PROMPT) + len(user_content) + len(patch)) // CHARS_PER_TOKEN
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": patch},
    ]
    payload: dict[str, object] = {
        "id": "sft-" + dedup[:16],
        "instance_id": record.instance_id,
        "repo": record.repo,
        "messages": messages,
        "meta": {
            "n_context_files": len(context_files),
            "context_chars": sum(len(c) for c in context_files.values()),
            "est_tokens": est_tokens,
            "dedup_hash": dedup,
        },
    }
    return BuiltPair(payload=payload, dedup_hash=dedup, est_tokens=est_tokens), ""


def ensure_outside_repo(out_dir: Path) -> None:
    """Refuse to write anything inside the public repository (hard rule)."""
    repo_root = Path(__file__).resolve().parent.parent
    resolved = out_dir.resolve()
    if resolved == repo_root or repo_root in resolved.parents:
        raise SystemExit(
            "REFUSING: --out "
            + str(out_dir)
            + " resolves inside the repository ("
            + str(repo_root)
            + "). Competition Data must never be written into the public repo."
        )


def run(cfg: Config, stdout: TextIO) -> dict[str, object]:
    ensure_outside_repo(cfg.out_dir)
    cfg.out_dir.mkdir(parents=True, exist_ok=True)

    stats = Stats()
    seen_hashes: set[str] = set()
    pairs_path = cfg.out_dir / "pairs.jsonl"

    with (
        zipfile.ZipFile(cfg.zip_path, "r") as archive,
        pairs_path.open("w", encoding="utf-8") as sink,
    ):
        tasks_name = next((n for n in archive.namelist() if n.endswith("tasks.jsonl")), None)
        if tasks_name is None:
            raise SystemExit("tasks.jsonl not found in " + str(cfg.zip_path))
        snapshots = SnapshotIndex(archive)
        with archive.open(tasks_name, "r") as raw_stream:
            text_stream = io.TextIOWrapper(raw_stream, encoding="utf-8")
            for line in text_stream:
                if cfg.limit is not None and stats.emitted >= cfg.limit:
                    break
                line = line.strip()
                if not line:
                    continue
                stats.tasks_read += 1
                try:
                    record = parse_task_line(line)
                except SchemaError:
                    stats.discarded["schema_invalid"] += 1
                    continue
                built, reason = build_pair(record, snapshots, cfg)
                if built is None:
                    stats.discarded[reason] += 1
                    continue
                if built.dedup_hash in seen_hashes:
                    stats.discarded["duplicado"] += 1
                    continue
                seen_hashes.add(built.dedup_hash)
                sink.write(json.dumps(built.payload, ensure_ascii=False) + "\n")
                stats.emitted += 1
                stats.token_sizes.append(built.est_tokens)

    ordered = sorted(stats.token_sizes)
    p50 = percentile(ordered, 50)
    p90 = percentile(ordered, 90)
    token_max = ordered[-1] if ordered else 0
    summary: dict[str, object] = {
        "tasks_read": stats.tasks_read,
        "pairs_emitted": stats.emitted,
        "discarded_total": sum(stats.discarded.values()),
        "discarded_by_reason": dict(stats.discarded),
        "token_dist": {"p50": p50, "p90": p90, "max": token_max},
        "ceiling_note": (
            "Dataset has 129 tasks with one gold patch each; the honest ceiling "
            "is <=129 pairs, below the 1000-pair DoD threshold. No pairs are "
            "fabricated. S1 mitigations: context augmentation (multiple "
            "context-subset variants per pair), multi-epoch LoRA, or a light "
            "few-shot/LoRA configuration sized for ~100 examples."
        ),
    }
    (cfg.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    stdout.write(
        "tasks read:            "
        + str(stats.tasks_read)
        + "\n"
        + "pairs emitted:         "
        + str(stats.emitted)
        + "\n"
        + "discarded:             "
        + str(sum(stats.discarded.values()))
        + " "
        + json.dumps(dict(stats.discarded), ensure_ascii=False)
        + "\n"
        + "token est p50/p90/max: "
        + str(p50)
        + "/"
        + str(p90)
        + "/"
        + str(token_max)
        + "\n"
        + "pairs written to:      "
        + str(pairs_path)
        + "\n"
    )
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build SFT chat pairs (issue -> gold patch) from the dataset zip."
    )
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None, help="emit at most N pairs (smoke run)")
    parser.add_argument("--max-context-chars", type=int, default=DEFAULT_MAX_CONTEXT_CHARS)
    parser.add_argument("--per-file-chars", type=int, default=DEFAULT_PER_FILE_CHARS)
    parser.add_argument(
        "--include-hints",
        action="store_true",
        help="include hints_text in the user turn (default: excluded to match eval)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = Config(
        zip_path=args.zip,
        out_dir=args.out,
        limit=args.limit,
        max_context_chars=args.max_context_chars,
        per_file_chars=args.per_file_chars,
        include_hints=args.include_hints,
    )
    run(cfg, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
