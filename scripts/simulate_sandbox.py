#!/usr/bin/env python3
"""T-04: mock deterministico do sandbox swegemma (as 9 tools, SEM modelo real).

Reimplementa ``scripts/simulate_sandbox.py`` (o v0.1 de 12h globais esta morto:
o budget real do harness e POR TASK — S0_dataset.md, secao 3.2).

Decisoes de design (documentadas conforme pedido na dispatch da T-04):

1. **Deterministico e sem modelo** (regra dura: zero execucao local do 31B,
   zero rede, zero API): o "agente" e um roteiro scripted de tool calls que
   replays o ciclo analyzer -> coder -> verifier contra 1 issue sintetica.
   A mesma execucao sempre produz os mesmos numeros.
2. **MockSandbox** implementa as 9 tools reais (run_command, read_file,
   edit_file, write_file, submit_patch, get_status, get_code_neighbors,
   search_similar_code, get_code_subgraph) sobre um repo-fixture SINTETICO em
   memoria (mini-arvore Python com um bug plantado em ``mini_calc/ops.py``).
   O repo e PUBLICO: nenhum conteudo de Competition Data (issue real, gold
   patch, test patch) entra neste codigo — fixture 100% sintetica.
3. **Contadores fieis ao harness**: budget POR TASK (60 min, 100 tool calls,
   500 turns); ``submit_patch`` e ``get_status`` NAO contam como tool calls;
   300s/comando; 5000 chars de output por comando/diff/grafo; read_file com
   cap de 150 linhas / 10000 chars; contexto de 32768 tokens com compaction
   automatica aos 14336. Tool error volta como JSON de erro, sem abortar a
   task. Sub-agentes custam turns E tool calls do pai (orcamento compartilhado,
   S0_dataset.md secao 5). Arquivos protegidos (test_*.py, conftest.py,
   pytest.ini, pyproject.toml...) recusam edicao e sao stripped do patch.
   submit_patch encerra a sessao; sem submit, o fallback extrai o git diff.
   Os 3 nudges de continuacao do harness NAO sao modelados: agente scripted
   nunca os dispara — gap declarado, nao medido (T04_4).
4. **Tokens = chars / 4** (heuristica documentada, sem tokenizer). A
   compaction e modelada como reset para um piso de 4096 tokens (resumo que
   sobrevive), tambem heuristico — o harness real resume o historico.
5. **1 tool call = 1 turn** no pai e no sub-agente; a delegacao em si custa
   1 turn do pai. Tempo simulado vem de custos fixos por tool
   (``TOOL_COST_SECONDS``) — calibracao grosseira, o perfil real de latencia
   so sera medido na S1 com o modelo no ar. O wall clock do mock aparece no
   relatorio apenas como custo do instrumento, nao como budget.
6. **--issue N** seleciona o cenario em ``ISSUES``; **--verbose** espelha o
   log detalhado no stdout. O log completo vai para
   ``planning/olimp-gemma4-swe-2026-q4/evidencias/`` (exigencia do DoD).
7. **Exit code**: 0 = PASS (nenhum limite estourado), 1 = FAIL (qualquer
   limite estourado), 2 = erro de uso.

Cenarios (--issue):
  1 — caminho dourado: ciclo analyzer->coder->verifier resolve o bug plantado,
      pytest passa e submit_patch fecha a sessao. Instrumento base.
  2 — stress de contexto: ciclos de delegacao repetidos com summaries gordos
      ate o budget de tool calls acabar. Mede T09_R6.
  3 — turnos longos: o mesmo ciclo com perfis de turno no LIMITE da janela de
      saida de cada agente + probes de fronteira. Mede T09_R7.
  4 — fallback de diff: ciclo completo que NUNCA chama submit_patch; cobre o
      ramo de extracao automatica de diff (T04_6).

Numeros que fecham os riscos abertos da T-09:
  T09_R6 (saturacao de contexto do pai): custo medio em tokens por delegacao
    e por ciclo completo no contexto do ROOT; quantas delegacoes cabem entre
    duas compactions (projecao (14336-4096)/custo); se o contexto satura de
    verdade (single message > 28672 tokens) e qual limite binda primeiro
    (tool calls vs contexto). Impresso nas linhas "T09_R6" do relatorio.
  T09_R7 (thinking_budget vs janela de saida): por agente, max_output_tokens,
    thinking_budget, headroom de resposta (max_output - thinking), maior turno
    observado no ciclo e folga restante; probes provam que thinking+resposta
    exatamente no limite cabe e 1 token a mais transborda. Os numeros vem dos
    configs REAIS da submissao (configs/sampling.yaml + sub_agents/*.yaml),
    nao de copias hardcoded.
"""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCIAS_DIR = REPO_ROOT / "planning" / "olimp-gemma4-swe-2026-q4" / "evidencias"

# --- Limites REAIS do harness (HARNESS_README via S0_dataset.md, secao 3.2) ---
CONTEXT_TOKENS = 32768
COMPACTION_THRESHOLD = 14336
MAX_TOOL_CALLS = 100
MAX_TURNS = 500
MAX_TIME_MINUTES = 60
COMMAND_TIMEOUT_SECONDS = 300  # documentado; os comandos do mock sao instantaneos
COMMAND_OUTPUT_CHARS = 5000
READ_FILE_MAX_LINES = 150
READ_FILE_MAX_CHARS = 10000

# --- Heuristicas modeladas (documentadas, nao medidas do harness real) ---
CHARS_PER_TOKEN = 4.0
COMPACTION_FLOOR_TOKENS = 4096
DEFAULT_INSTRUCTION_CHARS = 4000
DEFAULT_TOOL_TURN_THINKING = 256
DEFAULT_TOOL_TURN_RESPONSE = 256

# Custos simulados por tool call (segundos). Calibracao grosseira apenas para
# exercitar o budget de 60 min; perfil real de latencia sera medido na S1.
TOOL_COST_SECONDS: dict[str, int] = {
    "run_command": 45,
    "read_file": 5,
    "edit_file": 10,
    "write_file": 10,
    "submit_patch": 5,
    "get_status": 1,
    "get_code_neighbors": 8,
    "search_similar_code": 8,
    "get_code_subgraph": 8,
}

# Tools que NAO contam no budget de 100 tool calls.
NON_COUNTING_TOOLS = {"submit_patch", "get_status"}

# Mudancas nesses arquivos sao arrancadas do patch (o agente conserta a lib,
# nunca os testes). Match por basename e por caminho completo.
PROTECTED_PATTERNS: tuple[str, ...] = (
    "test_*.py",
    "conftest.py",
    "pytest.ini",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "tox.ini",
)


def est_tokens(text: str) -> int:
    """Estimate token count as chars / 4 (documented heuristic, no tokenizer)."""
    return int(len(text) / CHARS_PER_TOKEN)


def is_protected(path: str) -> bool:
    """Return True when ``path`` matches a protected-file pattern."""
    name = path.rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(name, pattern)
        for pattern in PROTECTED_PATTERNS
    )


# --- Fixture sintetica: mini-repo Python com um bug plantado -----------------
# 100% sintetica. Nenhum conteudo de Competition Data entra aqui (repo publico).
FIXTURE_BUG_FILE = "mini_calc/ops.py"
FIXTURE_OLD_SNIPPET = "def divide(a, b):\n    _validate(a, b)\n    return a - b"
FIXTURE_NEW_SNIPPET = "def divide(a, b):\n    _validate(a, b)\n    return a / b"
FIXTURE_FIXED_MARKER = "return a / b"

OPS_SOURCE = '''"""Arithmetic operations for the mini_calc fixture."""


def _validate(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a, b


def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def divide(a, b):
    _validate(a, b)
    return a - b


def mean(values):
    total = 0
    for value in values:
        total = add(total, value)
    return divide(total, len(values))
'''

UTILS_SOURCE = '''"""Formatting helpers for the mini_calc fixture."""

from mini_calc.ops import divide


def format_ratio(a, b):
    return f"{divide(a, b):.2f}"


def clamp(value, low, high):
    return max(low, min(high, value))
'''

TESTS_SOURCE = """import pytest

from mini_calc.ops import divide, mean


def test_divide_quotient():
    assert divide(6, 3) == 2.0


def test_divide_by_zero_raises():
    with pytest.raises(ValueError):
        divide(1, 0)


def test_mean():
    assert mean([1, 2, 3]) == 2.0
"""

PYPROJECT_SOURCE = """[project]
name = "mini_calc"
version = "0.1.0"
"""

PYTEST_PASS_STDOUT = (
    "tests/test_ops.py::test_divide_by_zero_raises PASSED\n"
    "tests/test_ops.py::test_divide_quotient PASSED\n"
    "tests/test_ops.py::test_mean PASSED\n"
    "\n"
    "3 passed in 0.03s"
)

PYTEST_FAIL_STDOUT = (
    "tests/test_ops.py::test_divide_by_zero_raises PASSED\n"
    "tests/test_ops.py::test_divide_quotient FAILED\n"
    "tests/test_ops.py::test_mean FAILED\n"
    "\n"
    "FAILED tests/test_ops.py::test_divide_quotient - assert 3 == 2.0\n"
    "FAILED tests/test_ops.py::test_mean - assert 3.0 == 2.0\n"
    "\n"
    "2 failed, 1 passed in 0.05s"
)

# Grafo sintetico de code intelligence (nodes = simbolos; edges = calls etc.).
GRAPH_EDGES: dict[str, list[tuple[str, str]]] = {
    "mini_calc.ops._validate": [],
    "mini_calc.ops.add": [],
    "mini_calc.ops.sub": [],
    "mini_calc.ops.mul": [],
    "mini_calc.ops.divide": [
        ("calls", "mini_calc.ops._validate"),
        ("called_by", "mini_calc.ops.mean"),
        ("called_by", "mini_calc.utils.format_ratio"),
        ("tested_by", "tests.test_ops.test_divide_quotient"),
    ],
    "mini_calc.ops.mean": [
        ("calls", "mini_calc.ops.add"),
        ("calls", "mini_calc.ops.divide"),
    ],
    "mini_calc.utils.format_ratio": [("calls", "mini_calc.ops.divide")],
    "mini_calc.utils.clamp": [],
    "tests.test_ops.test_divide_quotient": [("calls", "mini_calc.ops.divide")],
    "tests.test_ops.test_divide_by_zero_raises": [("calls", "mini_calc.ops._validate")],
    "tests.test_ops.test_mean": [("calls", "mini_calc.ops.mean")],
}


def build_fixture() -> dict[str, str]:
    """Build the synthetic in-memory repo fixture (fresh copy per run)."""
    return {
        "mini_calc/__init__.py": '"""mini_calc fixture package."""\n',
        FIXTURE_BUG_FILE: OPS_SOURCE,
        "mini_calc/utils.py": UTILS_SOURCE,
        "tests/test_ops.py": TESTS_SOURCE,
        "pyproject.toml": PYPROJECT_SOURCE,
    }


# --- Modelos de budget, contexto e janela de saida ---------------------------


@dataclass
class Budget:
    """Counters faithful to the per-task harness budget."""

    tool_calls: int = 0
    turns: int = 0
    seconds: float = 0.0
    output_chars: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "tool_calls": self.tool_calls,
            "turns": self.turns,
            "seconds": self.seconds,
            "output_chars": self.output_chars,
        }


@dataclass
class ContextWindow:
    """Token window with compaction at 14336 (modelled as reset to a floor).

    Peak is recorded BEFORE compaction so the report shows the true
    high-water mark that triggered the compaction.
    """

    label: str
    seed_tokens: int = 0
    tokens: int = 0
    peak_tokens: int = 0
    compactions: int = 0
    saturated: bool = False

    def seed(self, tokens: int) -> None:
        self.seed_tokens = tokens
        self.tokens = tokens
        self.peak_tokens = tokens

    def add(self, text: str) -> int:
        """Add ``text`` to the window; compact when crossing the threshold."""
        added = est_tokens(text)
        self.tokens += added
        self.peak_tokens = max(self.peak_tokens, self.tokens)
        if self.tokens >= COMPACTION_THRESHOLD:
            self.compactions += 1
            self.tokens = COMPACTION_FLOOR_TOKENS + added
        if self.tokens > CONTEXT_TOKENS:
            self.saturated = True
        return added


@dataclass(frozen=True)
class TurnProfile:
    """Declared model-turn size: thinking and visible response tokens."""

    thinking_tokens: int
    response_tokens: int
    label: str


@dataclass(frozen=True)
class AgentWindow:
    """Output window of one agent, loaded from the REAL submission configs."""

    name: str
    max_output_tokens: int
    thinking_budget: int

    @property
    def response_headroom(self) -> int:
        return self.max_output_tokens - self.thinking_budget

    def check(self, profile: TurnProfile) -> list[str]:
        """Return violations: thinking consumes the SAME output window."""
        issues: list[str] = []
        if profile.thinking_tokens > self.thinking_budget:
            issues.append(
                f"{self.name}: turno '{profile.label}' thinking {profile.thinking_tokens}t "
                f"> thinking_budget {self.thinking_budget}t (raciocínio seria truncado)"
            )
        total = profile.thinking_tokens + profile.response_tokens
        if total > self.max_output_tokens:
            issues.append(
                f"{self.name}: turno '{profile.label}' thinking+resposta {total}t "
                f"> max_output_tokens {self.max_output_tokens}t (resposta seria truncada)"
            )
        return issues


class SimulationLog:
    """Collects log lines; dumped to evidencias/ at the end of the run."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


# --- Carga dos configs REAIS da submissao (T-09) ------------------------------


class _IncludeLoader(yaml.SafeLoader):
    """SafeLoader that tolerates the custom ``!include`` tag (path string)."""


_IncludeLoader.add_constructor(
    "!include",
    lambda loader, node: loader.construct_scalar(node),
)


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=_IncludeLoader)
    except OSError:
        return None
    return loaded if isinstance(loaded, dict) else None


def load_agent_windows() -> dict[str, AgentWindow]:
    """Load output windows from configs/sampling.yaml and sub_agents/*.yaml.

    Fallback values are the schema defaults (16384/8192 root, 8192/4096 subs),
    used only when the config files are unreadable — documented, not hidden.
    """
    windows = {"root": AgentWindow("root", 16384, 8192)}
    sampling = _load_yaml(REPO_ROOT / "configs" / "sampling.yaml")
    if sampling is not None:
        thinking = sampling.get("thinking_config")
        budget = int(thinking.get("thinking_budget", 8192)) if isinstance(thinking, dict) else 8192
        windows["root"] = AgentWindow("root", int(sampling.get("max_output_tokens", 16384)), budget)
    for sub_path in sorted((REPO_ROOT / "sub_agents").glob("*.yaml")):
        cfg = _load_yaml(sub_path)
        if cfg is None:
            continue
        name = str(cfg.get("name", sub_path.stem))
        gcc = cfg.get("generate_content_config")
        if isinstance(gcc, dict):
            thinking = gcc.get("thinking_config")
            budget = (
                int(thinking.get("thinking_budget", 4096)) if isinstance(thinking, dict) else 4096
            )
            windows[name] = AgentWindow(name, int(gcc.get("max_output_tokens", 8192)), budget)
    return windows


def _file_chars(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8"))
    except OSError:
        return DEFAULT_INSTRUCTION_CHARS


def load_instruction_chars() -> dict[str, int]:
    """Chars of each agent instruction (prompts/*.md via !include targets)."""
    chars: dict[str, int] = {}
    agent_cfg = _load_yaml(REPO_ROOT / "agent.yaml")
    if agent_cfg is not None and isinstance(agent_cfg.get("instruction"), str):
        chars["root"] = _file_chars(REPO_ROOT / str(agent_cfg["instruction"]))
    sub_dir = REPO_ROOT / "sub_agents"
    for sub_path in sorted(sub_dir.glob("*.yaml")):
        cfg = _load_yaml(sub_path)
        if cfg is None or not isinstance(cfg.get("instruction"), str):
            continue
        name = str(cfg.get("name", sub_path.stem))
        chars[name] = _file_chars(sub_dir / str(cfg["instruction"]))
    chars.setdefault("root", DEFAULT_INSTRUCTION_CHARS)
    for known in ("code_analyzer", "patch_generator", "verifier"):
        chars.setdefault(known, DEFAULT_INSTRUCTION_CHARS)
    return chars


# --- MockSandbox: as 9 tools sobre o fixture sintetico ------------------------


class MockSandbox:
    """In-memory sandbox with the 9 real tools and faithful budget counters."""

    def __init__(self, fixture: dict[str, str]) -> None:
        self._files: dict[str, str] = dict(fixture)
        self._snapshot: dict[str, str] = dict(fixture)
        self.budget = Budget()
        self.session_ended = False
        self.command_truncations = 0
        self.last_output_text = ""
        self.read_truncations = 0
        self.tool_errors = 0
        self.protected_attempts = 0
        self.usage_by_tool: dict[str, dict[str, int]] = {}

    def call(self, tool: str, **kwargs: object) -> dict[str, object]:
        """Dispatch one tool call, charging the shared per-task budget."""
        if self.session_ended:
            return {"error": "session already ended by submit_patch"}
        cost = TOOL_COST_SECONDS.get(tool)
        if cost is None:
            return {"error": f"unknown tool: {tool}"}
        self.budget.turns += 1
        self.budget.seconds += cost
        if tool not in NON_COUNTING_TOOLS:
            self.budget.tool_calls += 1
        result = self._dispatch(tool, kwargs)
        text = json.dumps(result, sort_keys=True)
        # Harness caps tool output at 5000 chars (T04_1/T04_2): read_file has its
        # own line/char caps and submit_patch carries the patch payload itself.
        if tool not in ("read_file", "submit_patch") and len(text) > COMMAND_OUTPUT_CHARS:
            self.command_truncations += 1
            result = {"output": text[:COMMAND_OUTPUT_CHARS], "truncated": True}
            text = json.dumps(result, sort_keys=True)
        self.last_output_text = text
        self.budget.output_chars += len(text)
        entry = self.usage_by_tool.setdefault(tool, {"invocations": 0, "chars": 0, "seconds": 0})
        entry["invocations"] += 1
        entry["chars"] += len(text)
        entry["seconds"] += cost
        return result

    def diff(self, include_protected: bool = False) -> str:
        """Unified diff of the fixture against its initial snapshot."""
        return self._diff(include_protected)

    def changed_protected_paths(self) -> list[str]:
        """Protected files whose content changed (must always be empty)."""
        return [
            path
            for path in sorted(self._files)
            if is_protected(path) and self._files[path] != self._snapshot.get(path)
        ]

    def _dispatch(self, tool: str, kwargs: dict[str, object]) -> dict[str, object]:
        if tool == "run_command":
            return self._run_command(self._str(kwargs, "command"))
        if tool == "read_file":
            return self._read_file(
                self._str(kwargs, "path"),
                self._opt_int(kwargs, "start_line"),
                self._opt_int(kwargs, "end_line"),
            )
        if tool == "edit_file":
            return self._edit_file(
                self._str(kwargs, "path"),
                self._str(kwargs, "old_string"),
                self._str(kwargs, "new_string"),
            )
        if tool == "write_file":
            return self._write_file(self._str(kwargs, "path"), self._str(kwargs, "content"))
        if tool == "submit_patch":
            return self._submit_patch()
        if tool == "get_status":
            return self._get_status()
        if tool == "get_code_neighbors":
            return self._neighbors(
                self._str(kwargs, "node"),
                self._opt_str(kwargs, "edge_type"),
                self._opt_int(kwargs, "max_neighbors") or 50,
            )
        if tool == "search_similar_code":
            return self._similar(self._str(kwargs, "query"), self._opt_int(kwargs, "k") or 10)
        if tool == "get_code_subgraph":
            nodes = kwargs.get("nodes")
            names = [str(node) for node in nodes] if isinstance(nodes, list) else []
            return self._subgraph(names)
        return {"error": f"unknown tool: {tool}"}

    @staticmethod
    def _str(kwargs: dict[str, object], key: str) -> str:
        value = kwargs.get(key)
        return value if isinstance(value, str) else ""

    @staticmethod
    def _opt_str(kwargs: dict[str, object], key: str) -> str | None:
        value = kwargs.get(key)
        return value if isinstance(value, str) else None

    @staticmethod
    def _opt_int(kwargs: dict[str, object], key: str) -> int | None:
        value = kwargs.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return None

    def _run_command(self, command: str) -> dict[str, object]:
        stripped = command.strip()
        if "pytest" in stripped:
            return self._pytest()
        if stripped.startswith("git diff"):
            return {"returncode": 0, "stdout": self._diff(include_protected=True)}
        if "py_compile" in stripped or "compileall" in stripped:
            return {"returncode": 0, "stdout": "compilation ok"}
        self.tool_errors += 1
        return {"error": f"unsupported command in mock sandbox (offline): {stripped}"}

    def _pytest(self) -> dict[str, object]:
        if FIXTURE_FIXED_MARKER in self._files.get(FIXTURE_BUG_FILE, ""):
            return {"returncode": 0, "stdout": PYTEST_PASS_STDOUT}
        return {"returncode": 1, "stdout": PYTEST_FAIL_STDOUT}

    def _diff(self, include_protected: bool) -> str:
        chunks: list[str] = []
        for path in sorted(set(self._snapshot) | set(self._files)):
            if not include_protected and is_protected(path):
                continue
            old = self._snapshot.get(path, "")
            new = self._files.get(path, "")
            if old == new:
                continue
            chunks.extend(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                )
            )
        return "".join(chunks)

    def _read_file(
        self, path: str, start_line: int | None, end_line: int | None
    ) -> dict[str, object]:
        if path not in self._files:
            self.tool_errors += 1
            return {"error": f"file not found: {path}"}
        lines = self._files[path].splitlines()
        start = (start_line - 1) if start_line is not None else 0
        end = end_line if end_line is not None else len(lines)
        selected = lines[max(start, 0) : max(end, 0)]
        truncated_lines = len(selected) > READ_FILE_MAX_LINES
        if truncated_lines:
            self.read_truncations += 1
            selected = selected[:READ_FILE_MAX_LINES]
        content = "\n".join(selected)
        truncated_chars = len(content) > READ_FILE_MAX_CHARS
        if truncated_chars:
            self.read_truncations += 1
            content = content[:READ_FILE_MAX_CHARS]
        return {
            "path": path,
            "content": content,
            "truncated": truncated_lines or truncated_chars,
        }

    def _edit_file(self, path: str, old_string: str, new_string: str) -> dict[str, object]:
        if is_protected(path):
            self.protected_attempts += 1
            return {"error": f"protected file, edits are stripped from patches: {path}"}
        if path not in self._files:
            self.tool_errors += 1
            return {"error": f"file not found: {path}"}
        content = self._files[path]
        count = content.count(old_string)
        if count == 0:
            self.tool_errors += 1
            return {"error": "old_string not found"}
        if count > 1:
            self.tool_errors += 1
            return {"error": f"old_string matches {count} locations; provide a unique match"}
        self._files[path] = content.replace(old_string, new_string)
        return {"ok": True, "path": path}

    def _write_file(self, path: str, content: str) -> dict[str, object]:
        if is_protected(path):
            self.protected_attempts += 1
            return {"error": f"protected file, edits are stripped from patches: {path}"}
        self._files[path] = content
        return {"ok": True, "path": path, "chars": len(content)}

    def _submit_patch(self) -> dict[str, object]:
        patch = self._diff(include_protected=False)
        self.session_ended = True
        return {"patch": patch, "patch_chars": len(patch)}

    def _get_status(self) -> dict[str, object]:
        return {
            "budget": self.budget.as_dict(),
            "session_ended": self.session_ended,
        }

    def _neighbors(self, node: str, edge_type: str | None, max_neighbors: int) -> dict[str, object]:
        edges = GRAPH_EDGES.get(node, [])
        filtered = [
            (kind, other) for kind, other in edges if edge_type is None or kind == edge_type
        ][:max_neighbors]
        return {
            "node": node,
            "neighbors": [{"edge_type": kind, "node": other} for kind, other in filtered],
        }

    def _similar(self, query: str, k: int) -> dict[str, object]:
        tokens = [token for token in query.lower().split() if token]
        scored: list[tuple[float, str]] = []
        for node in sorted(GRAPH_EDGES):
            name = node.lower()
            hits = sum(1 for token in tokens if token in name)
            score = hits / max(len(tokens), 1)
            if score > 0:
                scored.append((score, node))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        results = [{"node": node, "score": round(score, 3)} for score, node in scored[:k]]
        return {"query": query, "results": results}

    def _subgraph(self, nodes: list[str]) -> dict[str, object]:
        node_set = set(nodes)
        edges = [
            {"src": node, "edge_type": kind, "dst": other}
            for node in sorted(node_set)
            for kind, other in GRAPH_EDGES.get(node, [])
            if other in node_set
        ]
        return {"nodes": sorted(node_set), "edges": edges}


# --- Runner: scripted agent, contexto do pai e janelas de saida ---------------


class SubAgentHandle:
    """What a sub-agent sees: shared budget, its OWN context window."""

    def __init__(self, runner: Runner, name: str, ctx: ContextWindow, window: AgentWindow) -> None:
        self.runner = runner
        self.name = name
        self.ctx = ctx
        self.window = window

    def tool(self, tool_name: str, profile: TurnProfile | None = None, **kwargs: object) -> dict:
        result = self.runner.sandbox.call(tool_name, **kwargs)
        text = self.runner.sandbox.last_output_text
        self.ctx.add(text)
        self.runner.log.write(
            f"  [{self.name}] {tool_name} -> {len(text)} chars (sub ctx={self.ctx.tokens}t)"
        )
        if profile is None:
            profile = TurnProfile(
                DEFAULT_TOOL_TURN_THINKING,
                DEFAULT_TOOL_TURN_RESPONSE,
                f"{self.name}:tool-turn",
            )
        self.runner.record_turn(self.name, profile)
        self.runner.window_peaks[self.name] = max(
            self.runner.window_peaks.get(self.name, 0), self.ctx.peak_tokens
        )
        return result


class Runner:
    """Drives a scripted scenario: parent context, delegations, violations."""

    def __init__(
        self,
        sandbox: MockSandbox,
        windows: dict[str, AgentWindow],
        instruction_chars: dict[str, int],
        log: SimulationLog,
    ) -> None:
        self.sandbox = sandbox
        self.windows = windows
        self.instruction_chars = instruction_chars
        self.log = log
        self.parent_ctx = ContextWindow("root")
        self.contexts: dict[str, ContextWindow] = {"root": self.parent_ctx}
        self.violations: list[str] = []
        self.notes: list[str] = []
        self.delegation_costs: list[int] = []
        self.delegation_count = 0
        self.window_peaks: dict[str, int] = {}
        self.max_turn_by_agent: dict[str, int] = {}
        self.phases: list[tuple[str, int, int, int]] = []
        self.submit_result: dict[str, object] | None = None
        self.stress_cycles = 0

    def seed_issue(self, problem: str) -> None:
        """Seed the parent context with the root instruction + issue text."""
        seed = self.instruction_chars.get("root", DEFAULT_INSTRUCTION_CHARS) + est_tokens(problem)
        self.parent_ctx.seed(seed)
        self.log.write(f"seed: root instruction + issue = {seed}t")

    def root_tool(
        self, tool: str, profile: TurnProfile | None = None, **kwargs: object
    ) -> dict[str, object]:
        result = self.sandbox.call(tool, **kwargs)
        text = self.sandbox.last_output_text
        self.parent_ctx.add(text)
        self.log.write(f"[root] {tool} -> {len(text)} chars (ctx={self.parent_ctx.tokens}t)")
        if tool == "submit_patch":
            self.submit_result = result
        if profile is not None:
            self.record_turn("root", profile)
        return result

    def delegate(
        self,
        agent: str,
        task: str,
        plan: Callable[[SubAgentHandle], str],
        profile: TurnProfile,
    ) -> str:
        """Run one sub-agent with its own context; charge the parent budget."""
        request = f"delegation->{agent}: {task}"
        request_tokens = est_tokens(request)
        self.parent_ctx.add(request)
        self.sandbox.budget.turns += 1  # a delegação em si é um turn do pai
        sub_ctx = ContextWindow(agent)
        seed = request_tokens + self.instruction_chars.get(agent, DEFAULT_INSTRUCTION_CHARS)
        sub_ctx.seed(seed)
        self.contexts[agent] = sub_ctx
        window = self.windows.get(agent)
        if window is None:
            self.violations.append(f"sem janela de output configurada para {agent}")
            window = AgentWindow(agent, 8192, 4096)
        handle = SubAgentHandle(self, agent, sub_ctx, window)
        summary = plan(handle)
        cost = request_tokens + est_tokens(summary)
        self.delegation_costs.append(cost)
        self.delegation_count += 1
        self.parent_ctx.add(summary)
        self.log.write(
            f"[root] delegate {agent} -> summary {len(summary)} chars, "
            f"custo no pai {cost}t (ctx={self.parent_ctx.tokens}t)"
        )
        self.record_turn(agent, profile)
        return summary

    def record_turn(self, agent: str, profile: TurnProfile) -> None:
        """Check a model turn against the agent's output window (T09_R7)."""
        window = self.windows.get(agent)
        if window is None:
            if f"sem janela de output configurada para {agent}" not in self.violations:
                self.violations.append(f"sem janela de output configurada para {agent}")
            return
        total = profile.thinking_tokens + profile.response_tokens
        self.max_turn_by_agent[agent] = max(self.max_turn_by_agent.get(agent, 0), total)
        for issue in window.check(profile):
            if issue not in self.violations:
                self.violations.append(issue)

    def probe_window(self, agent: str, profile: TurnProfile, expect_ok: bool) -> None:
        """Boundary probe: exactly-at-limit must fit, +1 must overflow."""
        window = self.windows.get(agent)
        if window is None:
            self.violations.append(f"probe sem janela configurada: {agent}")
            return
        issues = window.check(profile)
        fits = not issues
        if fits != expect_ok:
            self.violations.append(
                f"probe {profile.label} em {agent}: esperado "
                f"{'caber' if expect_ok else 'transbordar'}, obteve "
                f"{'caber' if fits else 'transbordar'}"
            )
        self.log.write(
            f"[probe] {agent} {profile.label}: "
            f"{'cabe' if fits else 'transborda'} (esperado "
            f"{'caber' if expect_ok else 'transbordar'})"
        )

    def mark_phase(self, name: str) -> None:
        budget = self.sandbox.budget
        self.phases.append((name, self.parent_ctx.tokens, budget.tool_calls, budget.turns))
        self.log.write(
            f"--- fase {name}: ctx={self.parent_ctx.tokens}t "
            f"calls={budget.tool_calls} turns={budget.turns}"
        )


# --- Roteiros scripted (o "agente" — sem modelo, deterministico) --------------

ISSUE_TEXT = (
    "Issue sintetica #S-1: mini_calc.ops.divide subtrai os operandos em vez de "
    "dividi-los; mean() e utils.format_ratio() herdam o erro. Esperado: "
    "divide(6, 3) == 2.0 e ValueError para divisor zero. Fixture 100% sintetica."
)

ANALYZER_SUMMARY = (
    "Causa raiz: mini_calc.ops.divide subtrai os operandos em vez de dividir "
    "(corpo: 'return a - b'). Pontos de chamada que herdam o bug: ops.mean e "
    "utils.format_ratio. O guard _validate ja levanta ValueError para b == 0. "
    "Sítio do fix: corpo de divide em mini_calc/ops.py; sem mudanca de "
    "assinatura; tests/test_ops.py espera divide(6, 3) == 2.0."
)

CODER_SUMMARY = (
    "Patch aplicado: corpo de divide agora retorna a / b (match unico ancorado "
    "na chamada de _validate). pytest local: 3 passed. Nenhum outro arquivo "
    "tocou; arquivos protegidos intocados."
)

VERIFIER_SUMMARY = (
    "Revisao independente: pytest 3 passed apos o patch; divide(6, 3) == 2.0, "
    "mean([1, 2, 3]) == 2.0 e o caminho de divisor zero ainda levanta "
    "ValueError. Sem regressao em utils.format_ratio. VEREDITO: PASS."
)

STRESS_TASK = "Ciclo periodico de delegacao sob carga (stress de contexto)."


def _stress_summary(agent: str) -> str:
    return f"[{agent}] " + "intermediate finding " * 100


def analyzer_plan(handle: SubAgentHandle) -> str:
    handle.tool("search_similar_code", query="divide quotient ratio")
    handle.tool("get_code_neighbors", node="mini_calc.ops.divide")
    handle.tool("read_file", path=FIXTURE_BUG_FILE)
    return ANALYZER_SUMMARY


def coder_plan(handle: SubAgentHandle) -> str:
    handle.tool("read_file", path=FIXTURE_BUG_FILE)
    handle.tool(
        "edit_file",
        path=FIXTURE_BUG_FILE,
        old_string=FIXTURE_OLD_SNIPPET,
        new_string=FIXTURE_NEW_SNIPPET,
    )
    handle.tool("run_command", command="python -m pytest -q")
    return CODER_SUMMARY


def verifier_plan(handle: SubAgentHandle) -> str:
    handle.tool("run_command", command="python -m pytest -q")
    handle.tool("read_file", path=FIXTURE_BUG_FILE, start_line=20, end_line=32)
    return VERIFIER_SUMMARY


def stress_analyzer_plan(handle: SubAgentHandle) -> str:
    handle.tool("search_similar_code", query="divide")
    handle.tool("get_code_neighbors", node="mini_calc.ops.divide")
    handle.tool("read_file", path=FIXTURE_BUG_FILE)
    return _stress_summary("code_analyzer")


def stress_coder_plan(handle: SubAgentHandle) -> str:
    handle.tool("read_file", path=FIXTURE_BUG_FILE)
    handle.tool(
        "edit_file",
        path=FIXTURE_BUG_FILE,
        old_string=FIXTURE_OLD_SNIPPET,
        new_string=FIXTURE_NEW_SNIPPET,
    )
    return _stress_summary("patch_generator")


def stress_verifier_plan(handle: SubAgentHandle) -> str:
    handle.tool("run_command", command="python -m pytest -q")
    handle.tool("read_file", path=FIXTURE_BUG_FILE, start_line=1, end_line=30)
    return _stress_summary("verifier")


# --- Cenarios (--issue N) ------------------------------------------------------


def scenario_golden_path(runner: Runner) -> None:
    """Issue 1: full analyzer->coder->verifier cycle fixing the planted bug."""
    runner.mark_phase("seed")
    runner.delegate(
        "code_analyzer",
        "Localizar a causa raiz do bug de divide.",
        analyzer_plan,
        TurnProfile(2048, 1024, "analyzer:final-summary"),
    )
    runner.mark_phase("analyze")
    runner.delegate(
        "patch_generator",
        "Aplicar o fix minimo reportado pelo analyzer.",
        coder_plan,
        TurnProfile(4096, 1024, "coder:final-summary"),
    )
    runner.mark_phase("patch")
    runner.delegate(
        "verifier",
        "Revisar independentemente o patch aplicado.",
        verifier_plan,
        TurnProfile(4096, 1024, "verifier:final-summary"),
    )
    runner.mark_phase("verify")
    runner.root_tool(
        "run_command",
        command="python -m pytest -q",
        profile=TurnProfile(2048, 512, "root:confirm-tests"),
    )
    runner.root_tool("get_status")
    runner.root_tool("submit_patch")
    runner.mark_phase("submit")


MAX_STRESS_CYCLES = 30
STRESS_CALLS_PER_CYCLE = 7  # analyzer 3 + coder 2 + verifier 2


def scenario_no_submit(runner: Runner) -> None:
    """Issue 4: golden path that never calls submit_patch (fallback diff, T04_6)."""
    runner.mark_phase("seed")
    runner.delegate(
        "code_analyzer",
        "Localizar a causa raiz do bug de divide.",
        analyzer_plan,
        TurnProfile(2048, 1024, "analyzer:final-summary"),
    )
    runner.mark_phase("analyze")
    runner.delegate(
        "patch_generator",
        "Aplicar o fix minimo reportado pelo analyzer.",
        coder_plan,
        TurnProfile(4096, 1024, "coder:final-summary"),
    )
    runner.mark_phase("patch")
    runner.delegate(
        "verifier",
        "Revisar independentemente o patch aplicado.",
        verifier_plan,
        TurnProfile(4096, 1024, "verifier:final-summary"),
    )
    runner.mark_phase("verify")
    runner.root_tool(
        "run_command",
        command="python -m pytest -q",
        profile=TurnProfile(2048, 512, "root:confirm-tests"),
    )
    runner.root_tool("get_status")
    runner.mark_phase("end-without-submit")


def scenario_context_stress(runner: Runner) -> None:
    """Issue 2: repeated delegation cycles with fat summaries (T09_R6)."""
    runner.mark_phase("seed")
    profile = TurnProfile(1024, 1024, "stress:final-summary")
    cycle = 0
    while cycle < MAX_STRESS_CYCLES:
        if runner.sandbox.budget.tool_calls + STRESS_CALLS_PER_CYCLE > MAX_TOOL_CALLS:
            runner.notes.append(
                f"stress parou no ciclo {cycle}: budget de tool calls seria estourado"
            )
            break
        runner.delegate("code_analyzer", STRESS_TASK, stress_analyzer_plan, profile)
        runner.delegate("patch_generator", STRESS_TASK, stress_coder_plan, profile)
        runner.delegate("verifier", STRESS_TASK, stress_verifier_plan, profile)
        cycle += 1
        if runner.parent_ctx.saturated:
            runner.notes.append(f"contexto do pai saturou apos {cycle} ciclos")
            break
    runner.stress_cycles = cycle
    runner.mark_phase("stress")


def scenario_long_turns(runner: Runner) -> None:
    """Issue 3: worst-case turn profiles at each window boundary (T09_R7)."""
    runner.mark_phase("seed")
    root = runner.windows["root"]
    runner.probe_window(
        "root",
        TurnProfile(root.thinking_budget, root.response_headroom, "root:boundary-exact"),
        expect_ok=True,
    )
    runner.probe_window(
        "root",
        TurnProfile(root.thinking_budget, root.response_headroom + 1, "root:boundary-over"),
        expect_ok=False,
    )
    analyzer = runner.windows["code_analyzer"]
    runner.delegate(
        "code_analyzer",
        "Localizar a causa raiz do bug de divide.",
        analyzer_plan,
        TurnProfile(analyzer.thinking_budget, analyzer.response_headroom, "analyzer:boundary"),
    )
    runner.mark_phase("analyze")
    runner.root_tool(
        "read_file",
        path=FIXTURE_BUG_FILE,
        profile=TurnProfile(4096, 4096, "root:plan-boundary"),
    )
    coder = runner.windows["patch_generator"]
    runner.delegate(
        "patch_generator",
        "Aplicar o fix minimo reportado pelo analyzer.",
        coder_plan,
        TurnProfile(coder.thinking_budget, coder.response_headroom, "coder:boundary"),
    )
    runner.mark_phase("patch")
    verifier = runner.windows["verifier"]
    runner.delegate(
        "verifier",
        "Revisar independentemente o patch aplicado.",
        verifier_plan,
        TurnProfile(verifier.thinking_budget, verifier.response_headroom, "verifier:boundary"),
    )
    runner.mark_phase("verify")
    runner.root_tool(
        "run_command",
        command="python -m pytest -q",
        profile=TurnProfile(root.thinking_budget, 2048, "root:final-synthesis"),
    )
    runner.root_tool("submit_patch")
    runner.mark_phase("submit")


# --- Registro de cenarios e relatorio -----------------------------------------


@dataclass(frozen=True)
class IssueSpec:
    """One registered scenario for --issue N."""

    id: int
    title: str
    problem: str
    plan: Callable[[Runner], None]
    expects_patch: bool


ISSUES: dict[int, IssueSpec] = {
    1: IssueSpec(
        1,
        "caminho dourado: ciclo analyzer->coder->verifier resolve o bug plantado",
        ISSUE_TEXT,
        scenario_golden_path,
        True,
    ),
    2: IssueSpec(
        2,
        "stress de contexto: ciclos de delegacao repetidos (mede T09_R6)",
        ISSUE_TEXT,
        scenario_context_stress,
        False,
    ),
    3: IssueSpec(
        3,
        "turnos longos: thinking_budget vs janela de saida (mede T09_R7)",
        ISSUE_TEXT,
        scenario_long_turns,
        True,
    ),
    4: IssueSpec(
        4,
        "fallback de diff: ciclo completo sem submit_patch (cobre T04_6)",
        ISSUE_TEXT,
        scenario_no_submit,
        False,
    ),
}


@dataclass
class SimulationReport:
    """Everything the verdict and the evidencias log need."""

    issue_id: int
    title: str
    passed: bool
    violations: list[str]
    notes: list[str]
    budget: Budget
    usage_by_tool: dict[str, dict[str, int]]
    command_truncations: int
    read_truncations: int
    tool_errors: int
    protected_attempts: int
    parent_seed: int
    parent_peak: int
    parent_final: int
    parent_compactions: int
    parent_saturated: bool
    window_peaks: dict[str, int]
    delegation_count: int
    delegation_costs: list[int]
    stress_cycles: int
    windows: dict[str, AgentWindow]
    max_turn_by_agent: dict[str, int]
    patch_chars: int
    patch_from_fallback: bool
    protected_in_patch: int
    wall_seconds: float
    phases: list[tuple[str, int, int, int]]
    r6_lines: list[str]
    r7_lines: list[str]
    log_path: str


def build_r6_lines(runner: Runner) -> list[str]:
    """T09_R6 numbers: parent context saturation under delegation load."""
    lines = ["T09_R6 (saturação de contexto do pai):"]
    costs = runner.delegation_costs
    if not costs:
        lines.append("  nenhuma delegação registrada neste cenário")
        return lines
    avg = sum(costs) / len(costs)
    per_compaction = COMPACTION_THRESHOLD - COMPACTION_FLOOR_TOKENS
    lines.append(
        f"  delegações: {len(costs)}; custo médio no pai por delegação: {avg:.0f}t "
        "(heurística chars/4)"
    )
    lines.append(f"  custo médio por ciclo completo (3 delegações): {avg * 3:.0f}t")
    lines.append(
        f"  pai: seed={runner.parent_ctx.seed_tokens}t "
        f"peak={runner.parent_ctx.peak_tokens}t final={runner.parent_ctx.tokens}t "
        f"compactions={runner.parent_ctx.compactions}"
    )
    between = int(per_compaction / avg)
    lines.append(f"  delegações entre duas compactions (projeção (14336-4096)/custo): {between}")
    lines.append(
        f"  saturação dura exige mensagem única > {CONTEXT_TOKENS - COMPACTION_FLOOR_TOKENS}t: "
        f"{'NÃO ocorreu' if not runner.parent_ctx.saturated else 'OCORREU'}"
    )
    if runner.stress_cycles:
        cycles_calls = MAX_TOOL_CALLS // STRESS_CALLS_PER_CYCLE
        lines.append(
            f"  stress: {runner.stress_cycles} ciclos completos executados "
            f"({STRESS_CALLS_PER_CYCLE} tool calls/ciclo)"
        )
        lines.append(
            f"  binding real: tool calls — {cycles_calls} ciclos cabem no teto de 100 calls; "
            f"contexto não é limite duro: compaction recorrente "
            f"({runner.parent_ctx.compactions} compactions, peak {runner.parent_ctx.peak_tokens}t) "
            f"mantém o pai operante; cabem ~{between // 3} ciclos POR janela entre compactions "
            f"(grandeza não comparável com o total da task)"
        )
    lines.append(
        "  RESPOSTA: com compaction aos 14336 o pai não satura duro por acúmulo; "
        "o custo real do ciclo é o budget compartilhado de tool calls — ver números acima."
    )
    return lines


def build_r7_lines(runner: Runner) -> list[str]:
    """T09_R7 numbers: thinking_budget vs output window per agent."""
    lines = ["T09_R7 (thinking_budget vs janela de saída):"]
    lines.append(
        "  modelo: thinking e resposta dividem a MESMA janela max_output_tokens "
        "(semântica ADK/Gemini; números dos configs reais da submissão)"
    )
    for name in ("root", "code_analyzer", "patch_generator", "verifier"):
        window = runner.windows.get(name)
        if window is None:
            continue
        observed = runner.max_turn_by_agent.get(name, 0)
        slack = window.max_output_tokens - observed
        lines.append(
            f"  {name}: max_output={window.max_output_tokens}t "
            f"thinking_budget={window.thinking_budget}t "
            f"headroom_resposta={window.response_headroom}t "
            f"maior_turno={observed}t folga={slack}t"
        )
    lines.append(
        "  probes de fronteira no log ([probe]): thinking+resposta exatamente no "
        "limite cabe; 1 token a mais transborda"
    )
    return lines


def build_report(
    spec: IssueSpec, runner: Runner, wall_seconds: float, log_path: Path
) -> SimulationReport:
    """Assemble the report and the PASS/FAIL verdict."""
    violations = list(runner.violations)
    budget = runner.sandbox.budget
    if budget.tool_calls > MAX_TOOL_CALLS:
        violations.append(f"tool_calls {budget.tool_calls} > {MAX_TOOL_CALLS}")
    if budget.turns > MAX_TURNS:
        violations.append(f"turns {budget.turns} > {MAX_TURNS}")
    if budget.seconds > MAX_TIME_MINUTES * 60:
        violations.append(f"tempo simulado {budget.seconds / 60:.1f}min > {MAX_TIME_MINUTES}min")
    for label, ctx in runner.contexts.items():
        if ctx.saturated:
            violations.append(f"contexto saturado duro: {label}")

    patch_chars = 0
    patch_from_fallback = False
    protected_in_patch = 0
    # The real harness ALWAYS extracts the diff when the session ends without
    # submit (fallback); expects_patch only decides whether an empty patch fails.
    submitted = runner.submit_result
    if isinstance(submitted, dict) and isinstance(submitted.get("patch"), str):
        patch = str(submitted["patch"])
    else:
        patch = runner.sandbox.diff(include_protected=False)
        patch_from_fallback = True
        runner.notes.append("submit_patch não foi chamado; fallback do harness extraiu o git diff")
    patch_chars = len(patch)
    protected_in_patch = len(runner.sandbox.changed_protected_paths())
    if spec.expects_patch and patch_chars == 0:
        violations.append("patch vazio (nada a submeter)")

    return SimulationReport(
        issue_id=spec.id,
        title=spec.title,
        passed=not violations,
        violations=violations,
        notes=list(runner.notes),
        budget=budget,
        usage_by_tool=runner.sandbox.usage_by_tool,
        command_truncations=runner.sandbox.command_truncations,
        read_truncations=runner.sandbox.read_truncations,
        tool_errors=runner.sandbox.tool_errors,
        protected_attempts=runner.sandbox.protected_attempts,
        parent_seed=runner.parent_ctx.seed_tokens,
        parent_peak=runner.parent_ctx.peak_tokens,
        parent_final=runner.parent_ctx.tokens,
        parent_compactions=runner.parent_ctx.compactions,
        parent_saturated=runner.parent_ctx.saturated,
        window_peaks=dict(runner.window_peaks),
        delegation_count=runner.delegation_count,
        delegation_costs=list(runner.delegation_costs),
        stress_cycles=runner.stress_cycles,
        windows=dict(runner.windows),
        max_turn_by_agent=dict(runner.max_turn_by_agent),
        patch_chars=patch_chars,
        patch_from_fallback=patch_from_fallback,
        protected_in_patch=protected_in_patch,
        wall_seconds=wall_seconds,
        phases=list(runner.phases),
        r6_lines=build_r6_lines(runner),
        r7_lines=build_r7_lines(runner),
        log_path=str(log_path),
    )


def render_report(report: SimulationReport) -> str:
    """Render the stdout/evidencias report block."""
    out: list[str] = []
    out.append("=" * 72)
    out.append(f"T-04 simulate_sandbox — issue {report.issue_id}: {report.title}")
    out.append("=" * 72)
    out.append("Budget por task (limites do harness):")
    out.append(
        f"  tool_calls: {report.budget.tool_calls}/{MAX_TOOL_CALLS} "
        "(submit_patch/get_status não contam)"
    )
    out.append(f"  turns: {report.budget.turns}/{MAX_TURNS}")
    out.append(f"  tempo simulado: {report.budget.seconds / 60:.1f}/{MAX_TIME_MINUTES} min")
    out.append(
        f"  output chars: {report.budget.output_chars} "
        f"(cap {COMMAND_OUTPUT_CHARS}/comando; truncamentos: {report.command_truncations})"
    )
    out.append(
        f"  read_file: truncamentos {report.read_truncations} "
        f"(cap {READ_FILE_MAX_LINES} linhas / {READ_FILE_MAX_CHARS} chars)"
    )
    out.append(
        f"  tool errors (JSON, sem abortar): {report.tool_errors}; "
        f"tentativas em arquivo protegido: {report.protected_attempts}"
    )
    out.append("  uso por tool (invocações | chars | s simulados):")
    for tool in sorted(report.usage_by_tool):
        entry = report.usage_by_tool[tool]
        out.append(
            f"    {tool:22s} {entry['invocations']:3d} | {entry['chars']:6d} | {entry['seconds']:4d}"
        )
    out.append("Contexto (janelas; compaction aos 14336):")
    out.append(
        f"  root: seed={report.parent_seed}t peak={report.parent_peak}t "
        f"final={report.parent_final}t compactions={report.parent_compactions}"
    )
    for agent in sorted(report.window_peaks):
        out.append(f"  {agent}: peak={report.window_peaks[agent]}t")
    out.append("Fases (ctx tokens | calls | turns):")
    for name, tokens, calls, turns in report.phases:
        out.append(f"  {name:10s} {tokens:6d}t {calls:3d} calls {turns:3d} turns")
    out.extend(report.r6_lines)
    out.extend(report.r7_lines)
    if report.issue_id != 2:
        out.append(
            f"Patch: {report.patch_chars} chars "
            f"(fallback sem submit: {'sim' if report.patch_from_fallback else 'não'}); "
            f"arquivos protegidos no patch: {report.protected_in_patch}"
        )
    out.append(f"Wall clock do mock: {report.wall_seconds:.2f}s (custo do instrumento)")
    for note in report.notes:
        out.append(f"Nota: {note}")
    out.append("-" * 72)
    out.append("VEREDITO: PASS" if report.passed else "VEREDITO: FAIL")
    for violation in report.violations:
        out.append(f"  [X] {violation}")
    out.append(f"Log: {report.log_path}")
    return "\n".join(out)


def default_log_path(issue_id: int) -> Path:
    return EVIDENCIAS_DIR / f"S0_t04_sim_issue{issue_id}.log"


def run_issue(
    issue_id: int, verbose: bool = False, log_path: Path | None = None
) -> SimulationReport:
    """Run one registered scenario end-to-end and return its report."""
    spec = ISSUES[issue_id]
    started = time.perf_counter()
    log = SimulationLog()
    log.write(f"T-04 sandbox simulation — issue {issue_id}: {spec.title}")
    sandbox = MockSandbox(build_fixture())
    runner = Runner(sandbox, load_agent_windows(), load_instruction_chars(), log)
    runner.seed_issue(spec.problem)
    spec.plan(runner)
    wall_seconds = time.perf_counter() - started
    final_path = log_path or default_log_path(issue_id)
    report = build_report(spec, runner, wall_seconds, final_path)
    text = render_report(report)
    log.lines.append(text)
    log.dump(final_path)
    print(text)
    if verbose:
        print("\n----- log detalhado -----")
        print("\n".join(log.lines))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="T-04: mock deterministico do sandbox swegemma (9 tools, sem modelo)"
    )
    parser.add_argument("--issue", type=int, default=1, help="cenário registrado em ISSUES")
    parser.add_argument("--verbose", action="store_true", help="espelhar o log detalhado no stdout")
    args = parser.parse_args(argv)
    if args.issue not in ISSUES:
        print(f"issue desconhecida: {args.issue}; disponíveis: {sorted(ISSUES)}")
        return 2
    report = run_issue(args.issue, verbose=args.verbose)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
