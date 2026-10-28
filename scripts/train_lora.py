#!/usr/bin/env python3
"""T-11-prep — LoRA training scaffold (DEC-005 variant B: LoRA directly on the
Gemma-4-31B QAT W4A16 checkpoint, NO bitsandbytes), offline for Kaggle L4x4
(4x NVIDIA L4 23034 MiB, torch 2.11.0+cu128, internet OFF).

HARD RULES from DEC-005 (the contract, read fully):
- NO additional quantization: the W4A16 QAT checkpoint IS the base; it loads
  as-is. ``BitsAndBytesConfig`` / ``prepare_model_for_kbit_training`` are
  GONE (DEC-005 §7.1 rework items): NF4 over QAT = double quantization,
  rejected. LoRA params bf16 over the bf16-compute checkpoint.
- LoRA r=16, alpha=32 (2x r, scaling=2; rsLoRA rejected: only pays off r>=64),
  dropout 0.05 (-> 0.1 on trigger G3), target modules q/k/v/o/gate/up/down
  (name hypothesis below, confirmed in SES-1), bias="none".
- seq_len 16384; truncation ONLY touches the context side (prompt): the
  assistant turn (gold patch) is never truncated; the prompt is
  middle-truncated (keeps the [ISSUE] head and the nearest-context tail).
- Data: ``pairs.jsonl`` in the format written by ``scripts/prepare_data.py``
  (messages system/user/assistant + meta.est_tokens). Pairs with
  meta.est_tokens > 32768 are DROPPED (DEC-005 §2.1; 2 of 128 measured); the
  leak probe (A-15) already ran at generation time -- not re-done here.
- holdout validation 12.5% stratified by repo, DETERMINISTIC: stable ordering
  and round-robin assignment, no RNG anywhere (a fixed-seed shuffle would
  still be version-stable only for pure-python random; we simply don't draw).
- Loss ONLY on assistant tokens (prompt labels -100), packing off.
- Optimizer: adamw_torch_fused on CUDA (plain AdamW on CPU/dry) — the no-bnb
  path. DEC-005 §1 listed paged_adamw_8bit as the default with this as the
  degradation step; the T-11 dispatch fixes the no-bnb variant as primary
  ( Decomp registered below ).
- 5 epochs max, early-stop patience 2 on val loss, LR 1e-4 cosine, warmup 10%
  (dispatch) — DEC-005 §2.6 recorded 5%: divergence resolved by the dispatch,
  single lever in configs/train_lora_v1.yaml, re-measured in SES-1.
- grad_accum 4, batch 1/GPU, gradient checkpointing, device_map="auto"
  (accelerate model-parallel sharding; NOT DDP — no re-quantized pipeline).

OFFLINE DISCIPLINE (internet OFF in the L4x4 image):
- Dependencies kept to torch + transformers + peft + accelerate (+ pyyaml,
  shipped by Kaggle images). trl and datasets are DROPPED by design here: the
  pairs load with stdlib json and the loop is hand-rolled — fewer wheels to
  attach under G5, fewer version-migration surfaces.
- Minimum library versions (wheels, G5 fallback: pip download on the host):
  torch>=2.5 (measured image: 2.11.0+cu128), transformers>=4.46, peft>=0.13,
  accelerate>=0.30 (device_map="auto" needs it), pyyaml>=6.0.
- ALL heavy imports are LAZY (inside functions) so this module imports and
  every pure-python piece is unit-testable without any of them.
- --dry-mode builds a 1-layer Gemma-shaped micro model (random init, no
  download) plus a deterministic hash tokenizer and runs the REAL pipeline
  (pair loading, masking, context-only truncation, accumulation, val eval,
  checkpoint save/epoch, early-stop logic, VRAM/s-per-step logging) on CPU —
  the host/CI integration gate (test (c) of tests/test_train_lora.py).

DISTINCT OUTPUT ARTIFACTS (adapter-only; base weights are NEVER saved —
DEC-005 R-T06-6: /kaggle/working is 20 GB):
- adapter_config.json + adapter_model.safetensors (the serving deliverable,
  r=16 -> ~110-220 MB on the 31B [A MEDIR NA S1: real size]); trainer_state.pt
  (optimizer/scheduler/step/patience) and weights.pt (resume artifact) nest
  inside each checkpoint dir; resume is EPOCH-granular in this scaffold.
- metrics.json next to the checkpoints: per-GPU VRAM peak, s/step, G1/G2
  flags, best val loss — the SES-1 measurement insumo.

THE [A MEDIR NA S1] REGISTER (numbered, referenced throughout the code; each
one must close in the SES-1 smoke before final training):
[1] pip freeze of the image: transformers/peft/torch/accelerate presence and
    exact versions (bnb NOT expected; not used anywhere here).
[2] Where the QAT checkpoint lives at training time (path under
    /kaggle/input/<competition-snapshot> vs a cached HF id) — the offline
    default is a filesystem path, not a hub name.
[3] Native-QAT load behavior with transformers: real materialized dtype
    (native 4-bit weights vs bf16), whether device_map="auto" shards it
    without extra packages, and whether anything beyond peft is required.
[4] The real device_map split (layers/homework per GPU) — logged at load.
[5] Peak VRAM per GPU (G1: > 20 GiB) at seq 16384, batch 1.
[6] s/step (G2: > 45 s) and supervised tokens/s.
[7] Exact module names of the 31B — hypothesis q_proj/k_proj/v_proj/o_proj/
    gate_proj/up_proj/down_proj — confirmed via named_modules().
[8] The tokenizer chat template of the QAT checkpoint: this scaffold prefers
    the tokenizer's own template when present and falls back to a plaintext
    concatenation; train-prompt must equal serving-prompt, and the
    prompt/assistant token boundary under a template must be re-verified.
[9] Which Gemma config class this transformers build exposes for the
    dry-mode micro model (Gemma4Config -> Gemma3TextConfig ->
    Gemma3Config -> GemmaConfig, first that constructs wins).
[10] Context truncation policy (middle head+tail here) vs plain tail-drop:
    compare val loss on the 18 pairs > 16384.
[Divergência registada] warmup_ratio 10% (dispatch) vs 5% (DEC-005 §2.6).
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import random
import re
import shutil
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "train_lora_v1.yaml"
DEFAULT_DATA_PATH = Path(r"C:\gemma4-data\sft_pairs\pairs.jsonl")
DEFAULT_OUTPUT_DIR = Path("/kaggle/working/gemma4-adapter")
DEFAULT_BASE_MODEL = "google/gemma-4-31b-it-qat-w4a16-ct"

# DEC-005 §1: coverage of all linear projections; name hypothesis confirmed in SES-1.
TARGET_MODULES_HYPOTHESIS: tuple[str, ...] = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)

# Per-epoch shuffling seed base: deterministic on every machine (pure-python
# random.Random on an int seed; no global RNG state touched).
SHUFFLE_SEED = 20261028

MICRO_VOCAB_SIZE = 512  # dry-mode micro model only; ids live in 0..242


class ConfigError(ValueError):
    """configs/train_lora_v1.yaml is malformed for this scaffold."""


class TokenizerLike(Protocol):
    """Minimal tokenizer surface the whole pipeline depends on."""

    eos_token_id: int
    pad_token_id: int

    def encode(self, text: str) -> list[int]: ...


@dataclass(frozen=True)
class LoadedPair:
    """One pairs.jsonl line in the exact prepare_data.py format."""

    pair_id: str
    repo: str
    messages: tuple[dict[str, str], ...]
    est_tokens: int


@dataclass(frozen=True)
class SupervisedExample:
    """Tokenized pair: loss is supervised ONLY on the assistant span."""

    input_ids: tuple[int, ...]
    labels: tuple[int, ...]

    @property
    def length(self) -> int:
        return len(self.input_ids)


@dataclass(frozen=True)
class LoRATuning:
    r: int
    alpha: int
    dropout: float
    target_modules: tuple[str, ...]
    bias: str


@dataclass(frozen=True)
class TrainSettings:
    seq_len: int
    epochs: int
    early_stop_patience: int
    lr: float
    warmup_ratio: float
    grad_accum: int
    per_device_batch: int
    gradient_checkpointing: bool
    optimizer: str
    drop_over_tokens: int
    max_grad_norm: float
    log_steps: int


@dataclass(frozen=True)
class DataSettings:
    holdout_fraction: float


@dataclass(frozen=True)
class CheckpointSettings:
    output_dir: str
    save_steps: int
    save_total_limit: int


@dataclass(frozen=True)
class AlertSettings:
    vram_gib_per_gpu: float
    seconds_per_step: float


@dataclass(frozen=True)
class RunSettings:
    base_model: str
    lora: LoRATuning
    train: TrainSettings
    data: DataSettings
    checkpoints: CheckpointSettings
    alerts: AlertSettings


def parse_pair_line(line: str) -> tuple[LoadedPair | None, str | None]:
    """Validate one pairs.jsonl line; returns (pair, None) or (None, reason)."""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        return None, "json_invalid"
    if not isinstance(raw, dict):
        return None, "schema_invalid"
    instance_id = raw.get("instance_id")
    repo = raw.get("repo")
    messages = raw.get("messages")
    meta = raw.get("meta")
    valid = (
        isinstance(instance_id, str)
        and isinstance(repo, str)
        and isinstance(messages, list)
        and len(messages) >= 3
        and isinstance(meta, dict)
    )
    if not valid:
        return None, "schema_invalid"
    assert isinstance(messages, list)  # narrowed for mypy (validated above)
    assert isinstance(meta, dict)
    text_messages: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, dict):
            return None, "schema_invalid"
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            return None, "schema_invalid"
        text_messages.append({"role": role, "content": content})
    raw_est = meta.get("est_tokens")
    est_tokens = raw_est if isinstance(raw_est, int) and not isinstance(raw_est, bool) else 0
    pair_id = raw.get("id") if isinstance(raw.get("id"), str) else instance_id
    assert isinstance(repo, str)  # narrowed for mypy (validated above)
    pair = LoadedPair(
        pair_id=str(pair_id),
        repo=repo,
        messages=tuple(text_messages),
        est_tokens=est_tokens,
    )
    return pair, None


def load_pairs(path: Path) -> tuple[list[LoadedPair], dict[str, int]]:
    """Stream a pairs.jsonl file; returns (pairs, discard-counter-by-reason)."""
    pairs: list[LoadedPair] = []
    counters: Counter[str] = Counter()
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError:
        return [], {"arquivo_ausente": 1}
    with handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            pair, reason = parse_pair_line(stripped)
            if reason is not None:
                counters[reason] += 1
                continue
            if pair is not None:
                pairs.append(pair)
    return pairs, dict(counters)


def drop_pairs_over_tokens(
    pairs: Sequence[LoadedPair], max_tokens: int
) -> tuple[list[LoadedPair], int]:
    """DEC-005 §2.1: drop pairs whose estimated size exceeds the token cap.

    est_tokens == 0 (unknown) is KEPT and visible in the load counters — the
    honest treatment of a malformed-but-parseable pair is not a silent drop.
    """
    kept = [pair for pair in pairs if pair.est_tokens <= max_tokens]
    return list(kept), len(pairs) - len(kept)


def split_holdout(
    pairs: Sequence[LoadedPair], fraction: float
) -> tuple[list[LoadedPair], list[LoadedPair]]:
    """Deterministic stratified holdout (DEC-005 §2.3, "12.5% por repo").

    Stable ordering by (repo, est_tokens, pair_id); round-robin over repo
    groups assigns pairs to val until the target size is reached. No RNG —
    the same file always produces the same split.
    """
    if not pairs:
        return [], []
    ordered = sorted(pairs, key=lambda pair: (pair.repo, pair.est_tokens, pair.pair_id))
    target = int(round(len(ordered) * fraction))
    groups: dict[str, list[LoadedPair]] = {}
    for pair in ordered:
        groups.setdefault(pair.repo, []).append(pair)
    chosen: set[int] = set()
    val: list[LoadedPair] = []
    round_index = 0
    while len(val) < target:
        took = False
        for group in groups.values():
            if round_index >= len(group):
                continue
            candidate = group[round_index]
            if id(candidate) in chosen or len(val) >= target:
                continue
            chosen.add(id(candidate))
            val.append(candidate)
            took = True
        if not took:
            break
        round_index += 1
    train = [pair for pair in ordered if id(pair) not in chosen]
    return train, sorted(val, key=lambda pair: (pair.repo, pair.est_tokens, pair.pair_id))


# --- Contexto: truncamento e máscara (pura, sem torch) -----------------------


def middle_truncate(ids: list[int], allowed: int) -> list[int]:
    """Keep head (the [ISSUE] block) and tail (nearest context) of the prompt.

    DEC-005: truncation ONLY ever touches the context side; the assistant
    (gold patch) is handled separately and is never cut. No marker token is
    inserted (token-id space stays pristine; the policy itself is
    [A MEDIR NA S1 #10] against plain tail-drop).
    """
    if allowed <= 0:
        return []
    if len(ids) <= allowed:
        return ids
    head = allowed // 2
    tail = allowed - head
    return ids[:head] + ids[len(ids) - tail :]


def build_labels(prompt_len: int, full_ids: Sequence[int]) -> list[int]:
    """Mask every prompt position (-100); supervise the assistant span only."""
    return [-100] * prompt_len + list(full_ids[prompt_len:])


def render_conversation(messages: Sequence[dict[str, str]]) -> tuple[str, str]:
    """Fallback rendering when the tokenizer has no chat template.

    Prompt side ends with a blank separator line; the caller attaches the
    assistant target (plus EOS) directly after. With a real checkpoint the
    tokenizer's own template is preferred (render_prompt_side); the serving
    parity of either path is [A MEDIR NA S1 #8].
    """
    by_role = {message.get("role", ""): message.get("content", "") for message in messages}
    system = by_role.get("system", "")
    user = by_role.get("user", "")
    assistant = by_role.get("assistant", "")
    prompt = (system + "\n\n" if system else "") + user
    return prompt + "\n\n", assistant


def render_prompt_side(messages: Sequence[dict[str, str]], tokenizer: TokenizerLike) -> str:
    """Prompt text; prefers the tokenizer's own chat template when available."""
    apply_template = getattr(tokenizer, "apply_chat_template", None)
    if callable(apply_template):
        prompt_only = [dict(message) for message in messages if message.get("role") != "assistant"]
        try:
            rendered = apply_template(prompt_only, tokenize=False, add_generation_prompt=True)
        except Exception:  # any template failure falls back silently (dry-safe)
            return render_conversation(messages)[0]
        if isinstance(rendered, str):
            return rendered
    return render_conversation(messages)[0]


def build_supervised_example(
    tokenizer: TokenizerLike, messages: Sequence[dict[str, str]], seq_len: int
) -> tuple[SupervisedExample | None, str | None]:
    """Tokenize one pair; mask loss to the assistant turn only.

    Returns (None, 'assistant_overflow') when EVEN with an empty prompt the
    assistant span cannot fit seq_len — the gold patch is never truncated.
    Otherwise (example, None); the prompt is context-truncated as needed.
    """
    prompt_text = render_prompt_side(messages, tokenizer)
    target_text = messages[-1]["content"] if messages else ""
    prompt_ids = tokenizer.encode(prompt_text)
    target_ids = tokenizer.encode(target_text) + [tokenizer.eos_token_id]
    if len(target_ids) > seq_len:
        return None, "assistant_overflow"
    allowed_prompt = seq_len - len(target_ids)
    if len(prompt_ids) > allowed_prompt:
        prompt_ids = middle_truncate(prompt_ids, allowed_prompt)
    input_ids = prompt_ids + target_ids
    labels = build_labels(len(prompt_ids), input_ids)
    return SupervisedExample(input_ids=tuple(input_ids), labels=tuple(labels)), None


def pad_batch(
    examples: Sequence[SupervisedExample], pad_id: int
) -> tuple[list[list[int]], list[list[int]], list[list[int]]]:
    """Right-pad one batch: (input_ids, labels, attention_mask), pure python.

    Padding never leaks into the loss: pad label slots are -100 and the pad
    rows of the attention mask are 0.
    """
    width = max(example.length for example in examples) if examples else 0
    inputs: list[list[int]] = []
    labels: list[list[int]] = []
    attention: list[list[int]] = []
    for example in examples:
        pad_size = width - example.length
        inputs.append(list(example.input_ids) + [pad_id] * pad_size)
        labels.append(list(example.labels) + [-100] * pad_size)
        attention.append([1] * example.length + [0] * pad_size)
    return inputs, labels, attention


def cosine_multiplier(step: int, warmup_steps: int, total_steps: int) -> float:
    """Linear warmup then cosine decay to 0 — pure math (torch-free testable)."""
    if total_steps <= 0:
        return 1.0
    if step < warmup_steps:
        return step / max(1, warmup_steps)
    progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
    return 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))


# --- Micro tokenizer e modelo micro (--dry-mode zero-download) ---------------


class MicroTokenizer:
    """Deterministic hash tokenizer: ONLY for --dry-mode and tests.

    Words map to stable buckets via sha1 (OOV-safe, no corpus bookkeeping).
    It is not a language artifact: it validates pipeline shape end-to-end.
    """

    eos_token_id = 2
    pad_token_id = 0

    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        for word in re.findall(r"\w+", text.lower()):
            digest = hashlib.sha1(word.encode("utf-8")).digest()
            ids.append(int.from_bytes(digest[:2], "big") % 240 + 3)
        return ids or [1]


# --- Settings parsing (pyyaml only, zero heavy imports) ----------------------


def _as_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{context} deve ser um mapping, recebido {type(value).__name__}")
    return value


def _as_int(raw: Any, context: str) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise ConfigError(f"{context} deve ser int, recebido {type(raw).__name__}")
    return raw


def _as_float(raw: Any, context: str) -> float:
    result: float
    if isinstance(raw, bool):
        raise ConfigError(f"{context} deve ser float, recebido bool")
    if isinstance(raw, int):
        result = float(raw)
    elif isinstance(raw, float):
        result = raw
    else:
        raise ConfigError(f"{context} deve ser float, recebido {type(raw).__name__}")
    return result


def _as_bool(raw: Any, context: str) -> bool:
    if not isinstance(raw, bool):
        raise ConfigError(f"{context} deve ser bool, recebido {type(raw).__name__}")
    return raw


def _as_str(raw: Any, context: str) -> str:
    if not isinstance(raw, str):
        raise ConfigError(f"{context} deve ser str, recebido {type(raw).__name__}")
    return raw


def parse_settings(path: Path) -> RunSettings:
    """Parse configs/train_lora_v1.yaml; every value is validated or refused."""
    try:
        raw_doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"não consigo ler {path}: {exc}") from exc
    root = _as_mapping(raw_doc, "raiz")

    base_model = _as_str(root.get("base_model"), "base_model")

    lora_raw = _as_mapping(root.get("lora"), "lora")
    targets_raw = lora_raw.get("target_modules")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise ConfigError("lora.target_modules deve ser lista não vazia")
    if not all(isinstance(item, str) for item in targets_raw):
        raise ConfigError("lora.target_modules deve conter apenas strings")
    lora = LoRATuning(
        r=_as_int(lora_raw.get("r"), "lora.r"),
        alpha=_as_int(lora_raw.get("alpha"), "lora.alpha"),
        dropout=_as_float(lora_raw.get("dropout"), "lora.dropout"),
        target_modules=tuple(targets_raw),
        bias=_as_str(lora_raw.get("bias"), "lora.bias"),
    )

    train_raw = _as_mapping(root.get("train"), "train")
    seq_len = _as_int(train_raw.get("seq_len"), "train.seq_len")
    if seq_len <= 0:
        raise ConfigError("train.seq_len deve ser > 0")
    train = TrainSettings(
        seq_len=seq_len,
        epochs=_as_int(train_raw.get("epochs"), "train.epochs"),
        early_stop_patience=_as_int(
            train_raw.get("early_stop_patience"), "train.early_stop_patience"
        ),
        lr=_as_float(train_raw.get("lr"), "train.lr"),
        warmup_ratio=_as_float(train_raw.get("warmup_ratio"), "train.warmup_ratio"),
        grad_accum=_as_int(train_raw.get("grad_accum"), "train.grad_accum"),
        per_device_batch=_as_int(train_raw.get("per_device_batch"), "train.per_device_batch"),
        gradient_checkpointing=_as_bool(
            train_raw.get("gradient_checkpointing"), "train.gradient_checkpointing"
        ),
        optimizer=_as_str(train_raw.get("optimizer"), "train.optimizer"),
        drop_over_tokens=_as_int(train_raw.get("drop_over_tokens"), "train.drop_over_tokens"),
        max_grad_norm=_as_float(train_raw.get("max_grad_norm"), "train.max_grad_norm"),
        log_steps=_as_int(train_raw.get("log_steps"), "train.log_steps"),
    )

    data_raw = _as_mapping(root.get("data"), "data")
    data = DataSettings(
        holdout_fraction=_as_float(data_raw.get("holdout_fraction"), "data.holdout_fraction"),
    )

    ckpt_raw = _as_mapping(root.get("checkpoints"), "checkpoints")
    checkpoints = CheckpointSettings(
        output_dir=_as_str(ckpt_raw.get("output_dir"), "checkpoints.output_dir"),
        save_steps=_as_int(ckpt_raw.get("save_steps"), "checkpoints.save_steps"),
        save_total_limit=_as_int(ckpt_raw.get("save_total_limit"), "checkpoints.save_total_limit"),
    )

    alerts_raw = _as_mapping(root.get("alerts"), "alerts")
    alerts = AlertSettings(
        vram_gib_per_gpu=_as_float(alerts_raw.get("vram_gib_per_gpu"), "alerts.vram_gib_per_gpu"),
        seconds_per_step=_as_float(alerts_raw.get("seconds_per_step"), "alerts.seconds_per_step"),
    )

    return RunSettings(
        base_model=base_model,
        lora=lora,
        train=train,
        data=data,
        checkpoints=checkpoints,
        alerts=alerts,
    )


# --- Lazy heavy imports (CI has no torch/transformers/peft) -------------------


@functools.cache
def _import_torch() -> Any:
    import torch  # noqa: PLC0415

    return torch


@functools.cache
def _import_transformers() -> Any:
    import transformers  # noqa: PLC0415

    return transformers


def _get_torch() -> Any:
    """Return the torch module or None when absent (CI-safe)."""
    try:
        return _import_torch()
    except ImportError:
        return None


# --- Micro model builder (--dry-mode) -----------------------------------------


def build_micro_model(vocab_size: int, max_positions: int) -> Any:
    """1-layer Gemma-shaped model, random init, CPU, no download.

    Dry-mode is a pipeline probe, not a language artifact: hidden 32,
    4 heads of dim 8, intermediate 64. The first Gemma config class this
    transformers build exposes wins ([A MEDIR NA S1 #9]).
    """
    transformers = _import_transformers()
    torch = _import_torch()
    config: Any = None
    last_error: Exception | None = None
    for name in ("Gemma4Config", "Gemma3TextConfig", "Gemma3Config", "GemmaConfig"):
        attribute = getattr(transformers, name, None)
        if attribute is None:
            continue
        try:
            config = attribute(
                vocab_size=vocab_size,
                hidden_size=32,
                intermediate_size=64,
                num_hidden_layers=1,
                num_attention_heads=4,
                num_key_value_heads=1,
                head_dim=8,
                max_position_embeddings=max_positions,
                rms_norm_eps=1e-6,
            )
            model = transformers.AutoModelForCausalLM.from_config(config)
        except Exception as exc:  # noqa: BLE001 - any config/model variant mismatch is retried
            last_error = exc
            continue
        model = model.float()
        torch.manual_seed(SHUFFLE_SEED)
        torch.nn.init.zeros_(model.lm_head.weight)
        return model
    raise RuntimeError(
        f"nenhuma Gemma config instanciou modelo micro neste transformers "
        f"(último erro: {last_error})"
    )


# --- Real model loader (Kaggle L4x4) ------------------------------------------


def unwrap_clippable_linear(model: Any) -> int:
    """Replace Gemma4-modulated QAT wrapper modules with their inner nn.Linear.

    The W4A16 checkpoint stores each projection as ``Gemma4ClippableLinear``
    wrapping the real ``nn.Linear`` (A MEDIR NA S1 #3/V2 discovery: the SES-1
    smoke hit ``ValueError: Target module Gemma4ClippableLinear is not
    supported`` from peft). With weights already materialized, swapping the
    wrapper for the inner linear is loss-free for LoRA purposes: the wrapper
    only exists for inference-time clip bounds. Returns how many were swapped.
    """
    swaps = 0
    replacements: list[tuple[Any, str, Any]] = []
    for name, module in model.named_modules():
        if type(module).__name__ != "Gemma4ClippableLinear":
            continue
        inner = getattr(module, "linear", None)
        if inner is None:
            continue
        parent_name, _, attr = name.rpartition(".")
        parent = model.get_submodule(parent_name) if parent_name else model
        replacements.append((parent, attr, inner))
        swaps += 1
    for parent, attr, inner in replacements:
        setattr(parent, attr, inner)
    return swaps


def load_real_model(
    model_path: str,
    lora: LoRATuning,
    gradient_checkpointing: bool,
) -> tuple[Any, Any]:
    """Load the QAT W4A16 base as-is + attach LoRA via peft. NO bitsandbytes.

    The checkpoint IS the base (DEC-005 §7.1): no BitsAndBytesConfig, no
    prepare_model_for_kbit_training, no re-quantization. Load behavior of the
    native-QAT snapshot is [A MEDIR NA S1 #3]; actual sharding is #4.
    """
    torch = _import_torch()
    transformers = _import_transformers()
    import peft  # noqa: PLC0415

    if torch.cuda.is_available():
        dtype: Any = torch.bfloat16
        device_map: str | dict[str, int | str] = "auto"
    else:
        dtype = torch.float32
        device_map = "cpu"
    base = transformers.AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=False,
    )
    base.config.use_cache = not gradient_checkpointing
    if gradient_checkpointing:
        base.gradient_checkpointing_enable()
    swapped = unwrap_clippable_linear(base)
    if swapped:
        print(f"[train_lora] unwrap_clippable_linear: {swapped} módulos QAT desembrulhados")
    lora_config = peft.LoraConfig(
        r=lora.r,
        lora_alpha=lora.alpha,
        lora_dropout=lora.dropout,
        target_modules=list(lora.target_modules),
        bias=lora.bias,
        task_type=peft.TaskType.CAUSAL_LM,
    )
    model = peft.get_peft_model(base, lora_config)
    model.print_trainable_parameters()
    return model, base


def _module_count_by_suffix(model: Any, suffixes: Sequence[str]) -> dict[str, int]:
    """Verify the target-name hypothesis against real named_modules (#7)."""
    counts: Counter[str] = Counter()
    for _, module in model.named_modules():
        name = type(module).__name__.lower()
        for suffix in suffixes:
            if suffix.rstrip("_proj").rstrip("_") in name or name.endswith(suffix):
                counts[suffix] += 1
    return dict(counts)


class HFTokenizerAdapter:
    """Adapt a transformers tokenizer to the TokenizerLike protocol."""

    def __init__(self, tokenizer: Any):
        self._tokenizer = tokenizer
        self.eos_token_id = int(tokenizer.eos_token_id)
        if tokenizer.pad_token_id is None:
            self.pad_token_id = self.eos_token_id
        else:
            self.pad_token_id = int(tokenizer.pad_token_id)

    def encode(self, text: str) -> list[int]:
        return list(self._tokenizer.encode(text, add_special_tokens=False))


def log_device_map(model: Any, logger: Callable[[str], None]) -> None:
    """Log where each weight landed ([A MEDIR NA S1 #4])."""
    dispatch: Counter[str] = Counter()
    for _parameter_name, parameter in model.named_parameters():
        device = getattr(parameter, "device", None)
        dispatch[str(device.type if device is not None else "unknown")] += 1
    total = model.num_parameters()
    summary = ", ".join(f"{key}={value}" for key, value in sorted(dispatch.items()))
    logger(f"device_map: {total} params -> {summary}")


# --- Trainer (hand-rolled loop; no trl, no datasets) --------------------------


class Trainer:
    """The whole training loop, deliberately hand-rolled (DEC-005 divergence:

    trl/datasets dropped). Owns: epoch shuffle, grad accumulation, cosine
    schedule, early stop, adapter-only checkpoints, VRAM/s-per-step logging,
    G1/G2 alerts, epoch-granular resume.
    """

    def __init__(
        self,
        settings: RunSettings,
        tokenizer: TokenizerLike,
        model: Any,
        optimizer: Any,
        train_pairs: Sequence[LoadedPair],
        val_pairs: Sequence[LoadedPair],
        output_dir: Path,
        max_steps: int | None = None,
        dry: bool = False,
    ) -> None:
        self.settings = settings
        self.tokenizer = tokenizer
        self.model = model
        self.optimizer = optimizer
        self.output_dir = output_dir
        self.max_steps = max_steps
        self.dry = dry
        self.max_grad_norm = settings.train.max_grad_norm
        self.global_step = 0
        self.patience = 0
        self.best_val_loss: float | None = None
        self.peak_gib_per_gpu: dict[int, float] = {}
        self.g1_triggered = False
        self.g2_triggered = False
        self.start_epoch = 0
        self.pend_micro_steps = 0
        self.pending_loss = 0.0
        self._accum_started = 0.0
        self.step_seconds: list[float] = []
        self.log: list[str] = []
        # Materialized examples (tokenized once, reused per epoch).
        self.train_examples = self._tokenize_all(train_pairs)
        self.val_examples = self._tokenize_all(val_pairs)
        total = (
            self.max_steps
            if self.max_steps is not None
            else len(self.train_examples) * settings.train.epochs
        )
        self.total_supervised_steps = max(1, total)
        self.warmup_steps = int(settings.train.warmup_ratio * self.total_supervised_steps)

    # -- tokenization ----------------------------------------------------------

    def _tokenize_all(self, pairs: Sequence[LoadedPair]) -> list[tuple[str, SupervisedExample]]:
        seq_len = self.settings.train.seq_len
        materialized: list[tuple[str, SupervisedExample]] = []
        for pair in pairs:
            example, reason = build_supervised_example(self.tokenizer, pair.messages, seq_len)
            if reason is not None:
                self.log.append(f"descarte {pair.pair_id}: {reason}")
                continue
            assert example is not None  # reason guard above implies pair present
            materialized.append((pair.pair_id, example))
        return materialized

    # -- batching ---------------------------------------------------------------

    def _batches(self, epoch: int, steps_target: int) -> Iterator[list[SupervisedExample]]:
        """Deterministic per-epoch shuffle (Random(SHUFFLE_SEED + epoch))."""
        rng = random.Random(SHUFFLE_SEED + epoch)
        pooled = [example for _, example in self.train_examples]
        rng.shuffle(pooled)
        batch_size = self.settings.train.per_device_batch
        emitted = 0
        for index in range(0, len(pooled), batch_size):
            if emitted >= steps_target:
                return
            yield pooled[index : index + batch_size]
            emitted += 1

    # -- optimizer step ----------------------------------------------------------

    def _maybe_step(self, loss_value: float) -> None:
        """Accumulate a micro-step; at every grad_accum boundary: scale, clip, step, schedule.

        The caller does ``backward()`` on the already-scaled loss; here the
        actual optimizer.step() happens once per accumulated global step.
        """
        torch = _import_torch()
        if self.pend_micro_steps == 0:
            self._accum_started = time.perf_counter()
        self.pending_loss += loss_value
        self.pend_micro_steps += 1
        accum = self.settings.train.grad_accum
        if self.pend_micro_steps < accum:
            return
        loss_avg = self.pending_loss / accum
        elapsed = time.perf_counter() - self._accum_started
        self.pending_loss = 0.0
        self.pend_micro_steps = 0
        multiplier = cosine_multiplier(
            self.global_step, self.warmup_steps, self.total_supervised_steps
        )
        for group in self.optimizer.param_groups:
            group["lr"] = self.settings.train.lr * multiplier
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
        self.optimizer.step()
        self.optimizer.zero_grad(set_to_none=True)
        self.global_step += 1
        self.step_seconds.append(elapsed)
        self._log_step(loss_avg, elapsed)

    # -- logging / alerts ----------------------------------------------------------

    def _log_step(self, loss: float, optimizer_seconds: float) -> None:
        torch = _import_torch()
        log_steps = max(1, self.settings.train.log_steps)
        if self.global_step % log_steps == 0:
            s_per_step = sum(self.step_seconds[-log_steps:]) / max(
                1, len(self.step_seconds[-log_steps:])
            )
            message = (
                f"step={self.global_step}/{self.total_supervised_steps} "
                f"loss={loss:.4f} s/step≈{s_per_step:.2f} (opt {optimizer_seconds:.3f}s)"
            )
            self.log.append(message)
            if (
                not self.dry
                and self.settings.alerts.seconds_per_step > 0
                and s_per_step > self.settings.alerts.seconds_per_step
            ):
                self.g2_triggered = True
                self.log.append(
                    f"G2 TRIGGERED: s/step {s_per_step:.2f} > "
                    f"{self.settings.alerts.seconds_per_step}"
                )
        if not self.dry and torch.cuda.is_available():
            for gpu_index in range(torch.cuda.device_count()):
                raw = torch.cuda.max_memory_allocated(gpu_index)
                gib = raw / (1024**3)
                previous = self.peak_gib_per_gpu.get(gpu_index, 0.0)
                self.peak_gib_per_gpu[gpu_index] = max(previous, gib)
                if gib > self.settings.alerts.vram_gib_per_gpu:
                    self.g1_triggered = True
                    self.log.append(
                        f"G1 TRIGGERED: VRAM pico {gib:.2f} GiB > "
                        f"{self.settings.alerts.vram_gib_per_gpu} GiB (GPU {gpu_index})"
                    )
                torch.cuda.reset_peak_memory_stats(gpu_index)

    # -- evaluation / checkpoints ------------------------------------------------

    def evaluate(self) -> float | None:
        """Mean assistant-token loss on val; None when val is empty."""
        torch = _import_torch()
        if not self.val_examples:
            return None
        self.model.eval()
        pad_id = self.tokenizer.pad_token_id
        total_loss = 0.0
        count = 0
        with torch.no_grad():
            for _pair_id, example in self.val_examples:
                (inputs, labels, attention) = pad_batch([example], pad_id)
                result = self._forward(inputs, labels, attention)
                total_loss += float(result)
                count += 1
        self.model.train()
        return total_loss / max(1, count)

    def _forward(
        self,
        inputs: list[list[int]],
        labels: list[list[int]],
        attention: list[list[int]],
    ) -> Any:
        torch = _import_torch()
        input_ids = torch.tensor(inputs, dtype=torch.long)
        label_ids = torch.tensor(labels, dtype=torch.long)
        mask = torch.tensor(attention, dtype=torch.long)
        output = self.model(
            input_ids=input_ids,
            attention_mask=mask,
            labels=label_ids,
        )
        return output.loss

    # -- checkpoints -----------------------------------------------------------------

    def save_checkpoint(self) -> Path:
        directory = self.output_dir / f"checkpoint-{self.global_step:05d}"
        directory.mkdir(parents=True, exist_ok=True)
        torch = _import_torch()
        resumed = directory / "trainer_state.pt"
        torch.save(
            {
                "global_step": self.global_step,
                "start_epoch": self.start_epoch,
                "best_val_loss": self.best_val_loss,
                "patience": self.patience,
            },
            resumed,
        )
        weights = directory / "weights.pt"
        if self.dry:
            torch.save(self.model.state_dict(), weights)
        else:
            # ADAPTER-ONLY (DEC-005 R-T06-6): the 31B base never lands on disk.
            self.model.save_pretrained(directory, save_embedding_layers="none")
        self._prune_old_checkpoints()
        return directory

    def _prune_old_checkpoints(self) -> None:
        limit = self.settings.checkpoints.save_total_limit
        if limit <= 0:
            return
        existing = sorted(
            (candidate for candidate in self.output_dir.glob("checkpoint-*") if candidate.is_dir()),
            key=lambda candidate: candidate.name,
        )
        for stale in existing[: max(0, len(existing) - limit)]:
            shutil.rmtree(stale, ignore_errors=True)

    def write_metrics(self, final_val: float | None) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        metrics = {
            "global_step": self.global_step,
            "epochs_run": self.start_epoch,
            "best_val_loss": self.best_val_loss,
            "final_val_loss": final_val,
            "peak_gib_per_gpu": self.peak_gib_per_gpu,
            "g1_triggered": self.g1_triggered,
            "g2_triggered": self.g2_triggered,
            "s_per_step_mean": (
                sum(self.step_seconds) / len(self.step_seconds) if self.step_seconds else None
            ),
            "log": self.log,
        }
        path = self.output_dir / "metrics.json"
        path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    # -- resume -----------------------------------------------------------------

    def load_resume(self, directory: Path) -> None:
        """Epoch-granular resume: trainer_state.pt + weights.pt."""
        torch = _import_torch()
        state_path = directory / "trainer_state.pt"
        if not state_path.exists():
            self.log.append(f"resume: {state_path} ausente, começa do zero")
            return
        state = torch.load(state_path, map_location="cpu", weights_only=True)
        self.global_step = state["global_step"]
        self.start_epoch = state["start_epoch"]
        self.best_val_loss = state["best_val_loss"]
        self.patience = state["patience"]
        weights = directory / "weights.pt"
        adapter = directory / "adapter_model.safetensors"
        if weights.exists():
            self.model.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True))
        elif adapter.exists():
            import peft  # noqa: PLC0415

            peft.set_peft_model_state_dict(
                self.model, torch.load(adapter, map_location="cpu", weights_only=True)
            )
        self.log.append(f"resume: etapa {self.global_step}, época {self.start_epoch}")

    # -- epoch loop -----------------------------------------------------------------

    def train_until_stop(self) -> float | None:
        """Run epochs until early stop or --max-steps; returns final val loss."""
        self.model.train()
        accum = self.settings.train.grad_accum
        micro_steps_in_epoch = len(self.train_examples)
        optimizer_steps_per_epoch = max(1, micro_steps_in_epoch // accum)
        if self.max_steps is not None and self.global_step >= self.max_steps:
            # Resume already at the step budget: evaluate and stop cleanly.
            val_now = self.evaluate()
            self._record_epoch_end(self.start_epoch, val_now)
            return val_now
        for epoch in range(self.start_epoch, self.settings.train.epochs):
            for batch in self._batches(epoch, optimizer_steps_per_epoch * accum):
                inputs, labels, attention = pad_batch(batch, self.tokenizer.pad_token_id)
                loss = self._forward(inputs, labels, attention)
                (loss / accum).backward()
                self._maybe_step(float(loss.detach()))
                if (
                    self.settings.checkpoints.save_steps
                    and self.global_step
                    and self.global_step % self.settings.checkpoints.save_steps == 0
                ):
                    self._do_checkpoint()
                    self.model.train()  # save leaves eval-free path; keep train mode
                if self.max_steps is not None and self.global_step >= self.max_steps:
                    val_now = self.evaluate()
                    self._record_epoch_end(epoch, val_now)
                    self._do_checkpoint()
                    return val_now
            epoch_end = self.evaluate()
            self._record_epoch_end(epoch, epoch_end)
            self._do_checkpoint()
            if self.patience >= self.settings.train.early_stop_patience:
                self.log.append(
                    f"early stop: patience={self.patience} "
                    f"(limite {self.settings.train.early_stop_patience}) na época {epoch}"
                )
                break
        final_val = self.evaluate()
        return final_val

    def _record_epoch_end(self, epoch: int, val_loss: float | None) -> None:
        self.start_epoch = epoch + 1
        if val_loss is None:
            self.log.append(f"época {epoch}: sem val — checkpoint gravado")
            return
        if self.best_val_loss is None or val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
            self.patience = 0
            self.log.append(f"época {epoch}: val {val_loss:.4f} (melhor)")
        else:
            self.patience += 1
            self.log.append(
                f"época {epoch}: val {val_loss:.4f} (sem melhorar, patience={self.patience})"
            )

    def _do_checkpoint(self) -> None:
        path = self.save_checkpoint()
        self.log.append(f"checkpoint salvo em {path}")


# --- CLI -----------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LoRA training scaffold (DEC-005 variant B)")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--data", type=str, default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="usar N primeiros pares")
    parser.add_argument("--resume", type=str, default=None, help="dir de checkpoint")
    parser.add_argument(
        "--dry-mode",
        action="store_true",
        help="micro-model 1 camada em CPU, zero download (gate de integração)",
    )
    return parser.parse_args(argv)


def build_torch_optimizer(model: Any, lr: float, optimizer_name: str, dry: bool) -> Any:
    torch = _import_torch()
    if not dry and torch.cuda.is_available() and optimizer_name == "adamw_torch_fused":
        return torch.optim.AdamW(
            [p for p in model.parameters() if p.requires_grad],
            lr=lr,
            fused=True,
        )
    return torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)


def build_model_and_tokenizer(
    settings: RunSettings, dry: bool, model_override: str | None, log: Callable[[str], None]
) -> tuple[Any, TokenizerLike]:
    if dry:
        model = build_micro_model(MICRO_VOCAB_SIZE, settings.train.seq_len)
        return model, MicroTokenizer()
    model, _base = load_real_model(
        model_override or settings.base_model,
        settings.lora,
        settings.train.gradient_checkpointing,
    )
    import transformers  # noqa: PLC0415

    tokenizer_raw = transformers.AutoTokenizer.from_pretrained(
        model_override or settings.base_model
    )
    return model, HFTokenizerAdapter(tokenizer_raw)


def demo_pairs() -> str:
    """Tiny synthetic pairs file used by --dry-mode when --data is absent."""
    rows: list[dict[str, Any]] = []
    for index in range(12):
        patch = (
            f"--- a/file_{index}.py\n+++ b/file_{index}.py\n@@ -1,1 +1,1 @@\n-bug\n+fix {index}\n"
        )
        rows.append(
            {
                "id": f"demo-issue-{index:04d}",
                "repo": f"demo/repo-{index % 3}",
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um agente que resolve issues.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Issue {index} do repo demo: corrigir bug no arquivo {index}."
                        ),
                    },
                    {"role": "assistant", "content": patch},
                ],
                "meta": {"est_tokens": 40 + index},
            }
        )
    return "\n".join(json.dumps(row) for row in rows)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    settings = parse_settings(config_path)
    data_path = Path(args.data)
    log = print

    preview = "\n".join(
        [
            f"base_model={settings.base_model}",
            f"lora r={settings.lora.r} alpha={settings.lora.alpha} "
            f"targets={','.join(settings.lora.target_modules)}",
            f"seq_len={settings.train.seq_len} epochs={settings.train.epochs} "
            f"lr={settings.train.lr} warmup={settings.train.warmup_ratio}",
        ]
    )
    log(f"[train_lora] settings: {preview}")

    if args.dry_mode:
        log("[train_lora] DRY MODE: modelo micro 1 camada em CPU, sem download")
    elif _get_torch() is None or not _import_torch().cuda.is_available():
        log(
            "[train_lora] AVISO: sem CUDA disponível fora de --dry-mode; "
            "rodando fallback CPU mesmo assim (não é o caminho do Kaggle)"
        )
    data_text = ""
    if args.dry_mode and not data_path.exists():
        log("[train_lora] --dry-mode sem --data: demo pairs sintéticos")
        data_text = demo_pairs()
    else:
        if args.dry_mode:
            log(f"[train_lora] DRY com --data real: {data_path}")

    if data_text:
        pairs, counters = load_pairs_from_text(data_text)
    else:
        pairs, counters = load_pairs(data_path)
    if counters:
        log(f"[train_lora] descartes no load: {counters}")

    if args.limit is not None:
        pairs = pairs[: args.limit]

    filtered, dropped = drop_pairs_over_tokens(pairs, settings.train.drop_over_tokens)
    if dropped:
        log(f"[train_lora] drop est_tokens > {settings.train.drop_over_tokens}: {dropped} pares")
    if not filtered:
        log("[train_lora] 0 pares úteis após filtros, nada a treinar")
        return 1

    train_pairs, val_pairs = split_holdout(filtered, settings.data.holdout_fraction)
    log(f"[train_lora] holdout: train={len(train_pairs)} val={len(val_pairs)}")
    if args.dry_mode or _import_torch().cuda.device_count() > 1:
        log(
            f"[A MEDIR NA S1] device_count={_import_torch().cuda.device_count() if not args.dry_mode else 0}"
        )

    output_dir = Path(args.out) if args.out else Path(settings.checkpoints.output_dir)
    model, tokenizer = build_model_and_tokenizer(settings, args.dry_mode, args.model, log)

    if _module_count_by_suffix(model, settings.lora.target_modules) is not None:
        log(
            "[train_lora] hipótese de target_modules: "
            f"'{','.join(settings.lora.target_modules)}' [A MEDIR NA S1 #7]"
        )

    trainer = Trainer(
        settings=settings,
        tokenizer=tokenizer,
        model=model,
        optimizer=build_torch_optimizer(
            model, settings.train.lr, settings.train.optimizer, args.dry_mode
        ),
        train_pairs=train_pairs,
        val_pairs=val_pairs,
        output_dir=output_dir,
        max_steps=args.max_steps,
        dry=args.dry_mode,
    )
    if args.resume is not None:
        trainer.load_resume(Path(args.resume))

    final_val = trainer.train_until_stop()
    metrics = trainer.write_metrics(final_val)
    log(f"[train_lora] métricas em {metrics}")
    return 0


def load_pairs_from_text(text: str) -> tuple[list[LoadedPair], dict[str, int]]:
    """Parse a pairs.jsonl body already in memory (demo_pairs path)."""
    pairs: list[LoadedPair] = []
    counters: Counter[str] = Counter()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pair, reason = parse_pair_line(stripped)
        if reason is not None:
            counters[reason] += 1
        elif pair is not None:
            pairs.append(pair)
    return pairs, dict(counters)


if __name__ == "__main__":
    sys.exit(main())
