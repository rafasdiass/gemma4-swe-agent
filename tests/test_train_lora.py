"""T-11-prep tests for scripts/train_lora.py (DEC-005 scaffold).

(a) dataset load + >32k filter + deterministic holdout
(b) loss mask assistant-only on a synthetic pair
(c) --dry-mode micro model runs optimizer steps on CPU (host integration gate)

All of (a)/(b)/helpers are pure Python: the module must import without
torch/transformers (CI has neither). (c) skips cleanly when they are absent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import train_lora as tl  # noqa: E402


def make_pair(pair_id: str, repo: str, est_tokens: int) -> dict:
    return {
        "id": pair_id,
        "instance_id": f"{repo.replace('/', '__')}-issue-{pair_id}",
        "repo": repo,
        "messages": [
            {"role": "system", "content": "Resolve issues."},
            {"role": "user", "content": f"Issue about {repo} number {pair_id} " * 3},
            {"role": "assistant", "content": f"--- a/{pair_id}.py\n+++ b/{pair_id}.py"},
        ],
        "meta": {"est_tokens": est_tokens},
    }


def write_pairs(tmp_path: Path, pairs: list[dict]) -> Path:
    path = tmp_path / "pairs.jsonl"
    path.write_text("\n".join(json.dumps(pair) for pair in pairs) + "\n", encoding="utf-8")
    return path


# --- (a) dataset load, filter, deterministic holdout --------------------------


def test_load_pairs_reads_prepare_data_format(tmp_path: Path) -> None:
    path = write_pairs(tmp_path, [make_pair("p1", "a/b", 100), make_pair("p2", "c/d", 200)])
    pairs, counters = tl.load_pairs(path)
    assert counters == {}
    assert [pair.pair_id for pair in pairs] == ["p1", "p2"]
    assert pairs[0].messages[2]["role"] == "assistant"


def test_load_pairs_counts_discards(tmp_path: Path) -> None:
    path = tmp_path / "pairs.jsonl"
    good = json.dumps(make_pair("p1", "a/b", 10))
    bad_lines = ["{not json", json.dumps({"id": "x2"}), ""]
    path.write_text("\n".join([good, *bad_lines]), encoding="utf-8")
    pairs, counters = tl.load_pairs(path)
    assert len(pairs) == 1
    assert counters["json_invalid"] == 1
    assert counters["schema_invalid"] == 1


def test_drop_pairs_over_tokens_matches_dec005() -> None:
    pairs = [
        tl.LoadedPair(pair_id=f"p{i}", repo="a", messages=(), est_tokens=t)
        for i, t in enumerate([16384, 32000, 32768, 32769])
    ]
    kept, dropped = tl.drop_pairs_over_tokens(pairs, 32768)
    assert dropped == 1
    assert [pair.est_tokens for pair in kept] == [16384, 32000, 32768]


def test_holdout_is_deterministic_and_stratified(tmp_path: Path) -> None:
    pairs = [
        tl.LoadedPair(pair_id=pid, repo=repo, messages=(), est_tokens=size)
        for pid, repo, size in [
            ("p1", "a", 100),
            ("p2", "a", 200),
            ("p3", "a", 300),
            ("p4", "b", 150),
            ("p5", "b", 250),
            ("p6", "b", 350),
            ("p7", "c", 120),
            ("p8", "c", 220),
        ]
    ]
    train_a, val_a = tl.split_holdout(pairs, 0.125)
    train_b, val_b = tl.split_holdout(pairs, 0.125)
    assert [p.pair_id for p in val_a] == [p.pair_id for p in val_b]
    assert [p.pair_id for p in train_a] == [p.pair_id for p in train_b]
    # 12.5% of 8 -> 1 pair in val
    assert len(val_a) == 1
    assert len(train_a) == 7
    assert {p.pair_id for p in val_a}.isdisjoint({p.pair_id for p in train_a})


def test_split_holdout_uses_est_tokens_tiebreak(tmp_path: Path) -> None:
    """Deterministic tie-break: same repo, est_tokens, pair_id ordering."""
    pairs = [
        tl.LoadedPair(pair_id="z", repo="r", messages=(), est_tokens=5),
        tl.LoadedPair(pair_id="a", repo="r", messages=(), est_tokens=5),
    ]
    _, val = tl.split_holdout(pairs, 0.5)
    assert val == [tl.LoadedPair(pair_id="a", repo="r", messages=(), est_tokens=5)]


def test_cosine_multiplier_warmup_then_decay() -> None:
    total, warmup = 100, 10
    assert tl.cosine_multiplier(0, warmup, total) == 0.0
    assert tl.cosine_multiplier(5, warmup, total) == pytest.approx(0.5)
    assert tl.cosine_multiplier(warmup, warmup, total) == pytest.approx(1.0)
    assert tl.cosine_multiplier(total, warmup, total) == pytest.approx(0.0, abs=1e-9)


# --- (b) assistant-only loss mask --------------------------------------------


def test_build_labels_masks_prompt_only() -> None:
    ids = [10, 11, 12, 13]
    assert tl.build_labels(2, ids) == [-100, -100, 12, 13]


def test_middle_truncate_keeps_head_and_tail() -> None:
    ids = list(range(100))
    cut = tl.middle_truncate(ids, 10)
    assert cut == list(range(5)) + list(range(95, 100))
    assert tl.middle_truncate(ids, 200) is ids
    assert tl.middle_truncate([1, 2, 3], 0) == []


def make_tokenizer_pair_example() -> tuple[tl.SupervisedExample, int]:
    tokenizer = tl.MicroTokenizer()
    messages = [
        {"role": "system", "content": "system text"},
        {"role": "user", "content": "the user question about the repo"},
        {"role": "assistant", "content": "the assistant patch"},
    ]
    example, reason = tl.build_supervised_example(tokenizer, messages, seq_len=128)
    assert reason is None
    assert example is not None
    prompt_len = next(i for i, label in enumerate(example.labels) if label != -100)
    return example, prompt_len


def test_loss_mask_is_assistant_only() -> None:
    example, prompt_len = make_tokenizer_pair_example()
    assert prompt_len > 0
    assert all(label == -100 for label in example.labels[:prompt_len])
    supervised = example.labels[prompt_len:]
    assert all(label != -100 for label in supervised)
    assert supervised[-1] == tl.MicroTokenizer.eos_token_id
    assert supervised[:-1] == example.input_ids[prompt_len:-1]


def test_assistant_overflow_is_refused_not_truncated() -> None:
    tokenizer = tl.MicroTokenizer()
    messages = [
        {"role": "user", "content": "x " * 3},
        {"role": "assistant", "content": "gold " * 40},
    ]
    example, reason = tl.build_supervised_example(tokenizer, messages, seq_len=8)
    assert example is None
    assert reason == "assistant_overflow"


def test_pad_batch_never_leaks_into_loss() -> None:
    tokenizer = tl.MicroTokenizer()
    messages = [
        {"role": "user", "content": "short question"},
        {"role": "assistant", "content": "answer"},
    ]
    example, _ = tl.build_supervised_example(tokenizer, messages, seq_len=64)
    assert example is not None
    long_pair = make_pair("plong", "a/b", 50)
    long_example, reason = tl.build_supervised_example(tokenizer, long_pair["messages"], seq_len=64)
    assert reason is None
    inputs, labels, attention = tl.pad_batch([long_example, example], 0)
    width = len(inputs[0])
    assert width > example.length
    padded_labels = labels[1][example.length :]
    assert padded_labels and all(label == -100 for label in padded_labels)
    assert attention[1][: example.length] == [1] * example.length
    assert attention[1][example.length :] == [0] * (width - example.length)


# --- parse_settings on the real lever file -----------------------------------


def test_parse_settings_reads_repo_yaml() -> None:
    settings = tl.parse_settings(
        Path(__file__).resolve().parents[1] / "configs" / "train_lora_v1.yaml"
    )
    assert settings.base_model == "google/gemma-4-31b-it-qat-w4a16-ct"
    assert settings.lora.r == 16
    assert settings.lora.alpha == 32
    assert settings.lora.dropout == 0.05
    assert settings.lora.bias == "none"
    assert settings.lora.target_modules == (
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    )
    assert settings.train.seq_len == 16384
    assert settings.train.epochs == 5
    assert settings.train.early_stop_patience == 2
    assert settings.train.lr == pytest.approx(1e-4)
    assert settings.train.warmup_ratio == pytest.approx(0.10)
    assert settings.train.grad_accum == 4
    assert settings.train.per_device_batch == 1
    assert settings.train.gradient_checkpointing is True
    assert settings.train.optimizer == "adamw_torch_fused"
    assert settings.train.drop_over_tokens == 32768
    assert settings.data.holdout_fraction == pytest.approx(0.125)
    assert settings.checkpoints.output_dir == "/kaggle/working/gemma4-adapter"
    assert settings.alerts.vram_gib_per_gpu == pytest.approx(20.0)
    assert settings.alerts.seconds_per_step == pytest.approx(45.0)


def test_parse_settings_refuses_bad_types(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("base_model: 42\n", encoding="utf-8")
    with pytest.raises(tl.ConfigError):
        tl.parse_settings(bad)


def test_micro_tokenizer_is_deterministic_and_in_vocab() -> None:
    tokenizer = tl.MicroTokenizer()
    first = tokenizer.encode("resolve the bug in module alpha")
    second = tokenizer.encode("resolve the bug in module alpha")
    assert first == second
    assert all(0 <= tid < tl.MICRO_VOCAB_SIZE for tid in first)


# --- (c) dry-mode integration (host gate; skipped without torch/transformers)


torch = pytest.importorskip("torch", reason="dry-mode needs torch")
transformers = pytest.importorskip("transformers", reason="dry-mode needs transformers")


def test_dry_mode_smoke_two_optimizer_steps(tmp_path: Path) -> None:
    """The plan's test (c): micro model, real pipeline, 12 pairs, grad_accum 4
    -> exactly >= 2 optimizer steps at --max-steps 2; artifacts on disk."""
    data = write_pairs(tmp_path, [make_pair(f"sm{i}", f"d/{i % 3}", 40 + i) for i in range(12)])
    out = tmp_path / "out"
    rc = tl.main(
        [
            "--dry-mode",
            "--config",
            str(Path(__file__).resolve().parents[1] / "configs" / "train_lora_v1.yaml"),
            "--data",
            str(data),
            "--out",
            str(out),
            "--max-steps",
            "2",
        ]
    )
    assert rc == 0
    checkpoints = sorted(out.glob("checkpoint-*"))
    assert checkpoints, "dry-mode should persist the resume artifacts"
    assert (checkpoints[-1] / "trainer_state.pt").exists()
    assert (checkpoints[-1] / "weights.pt").exists()
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["global_step"] >= 2
    assert metrics["epochs_run"] >= 1
    assert metrics["g1_triggered"] is False  # never on CPU/dry
    assert metrics["peak_gib_per_gpu"] == {}


def test_dry_mode_resumes_from_checkpoint(tmp_path: Path) -> None:
    data = write_pairs(tmp_path, [make_pair(f"sm{i}", f"d/{i % 3}", 40 + i) for i in range(12)])
    out = tmp_path / "out"
    common = [
        "--dry-mode",
        "--config",
        str(Path(__file__).resolve().parents[1] / "configs" / "train_lora_v1.yaml"),
        "--data",
        str(data),
        "--out",
        str(out),
        "--max-steps",
        "2",
    ]
    assert tl.main(common) == 0
    first = sorted(out.glob("checkpoint-*"))[-1].name
    assert tl.main([*common, "--resume", str(out / first)]) == 0
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["log"], "resume must log what it restored"
    assert any("resume" in line for line in metrics["log"])
