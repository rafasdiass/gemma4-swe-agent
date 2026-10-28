# S0 — T-01: Dataset íntegro + schema do harness documentado (recibo)

**Data:** 2026-10-28 · **Executor:** Ayla (host)
**Fonte:** `C:\gemma4-data\gemma-4-developer-agent.zip` (20.42 GB, download Kaggle CLI, wrapper resiliente) · Extração SELETIVA em `C:\gemma4-data\extract\` (fora do repo — regra de visibilidade pública da GOVERNANCA_PIPELINE: conteúdo NUNCA entra no repo, só schema abstrato).

## 1. Integridade e inventário (prova mecânica)

- `zipfile.testzip()` → **OK** (nenhum CRC corrompido nos 20.42 GB)
- **524 entradas**: 129 snapshots de repo (`.tgz`), 127 embeddings (`.npz`), 127 graphs (`.json`), 124 wheels, 10 `sample_submission/*`, 4 `docker/*`, 1 `HARNESS_README.md`, 1 `sandbox`, 1 `tasks.jsonl`

## 2. `tasks.jsonl` — 129 tasks, formato SWE-bench (schema abstrato)

```
instance_id: str · repo: str · base_commit: str · patch: str (gold, NUNCA no repo)
test_patch: str (NUNCA no repo) · problem_statement: str (NUNCA no repo)
hints_text: str · created_at: str
```

## 3. HARNESS_README.md — spec do `swegemma` (pontos que mudam o jogo)

### 3.1 Schema de submissão (adk-submission, declarativo, SEM Python nosso)

Layout canônico (confirmado contra `sample_submission/`):

```
submission/
├── agent.yaml            # OBRIGATÓRIO na raiz (ou agent.yml/root_agent.yaml)
├── eval_config.yaml      # OPCIONAL na RAIZ, chave `evaluation:`
├── configs/sampling.yaml # opcional, via !include
├── prompts/*.md          # via !include
├── sub_agents/*.yaml     # via config_path
├── adapters/<nome>/{adapter_config.json, adapter_model.safetensors}
└── skills/<nome>/SKILL.md
```

Campos do `LlmAgent` (nomes REAIS, divergem do nosso v0.1):

| Nosso v0.1 (ERRADO) | Canônico ADK | Nota |
|---|---|---|
| `agent_id` | **`name`** (str, required) | |
| `system_prompt` | **`instruction`** (str até 1M chars; suporta `{problem_description}`, `{hints}`) | |
| `sampling: !include ...` | **`generate_content_config: !include ...`** | |
| `max_tokens` | **`max_output_tokens`** (1..32768, default 16384) | |
| `repetition_penalty` | **não existe** no allowed_fields | remover |
| `sub_agents:` dict nomeado | **lista** de `{config_path: ...}` OU `tools:` com `agent_tool: {config_path: ..., skip_summarization: true}` | |
| `adapters:` dict na raiz | **`adapter: <nome>` por agente** | |
| — | **`thinking_config.thinking_budget`** (0..32768, default 4096) + `include_thoughts` | ALAVANCA: raciocínio do Gemma 4 |
| `skills` (nomes) | **`skills`: lista de PATHS relativos** (ex.: `skills/repo_navigation`) | |

Sample submission (valores de TESTE): `max_time_minutes: 1`, `max_tool_calls: 10`, `max_turns: 50`, `timeout_seconds: 60`.

### 3.2 Budgets REAIS (por task, não globais) — o nosso eval_config de 12h está morto

| Limite | Default | Fonte |
|---|---|---|
| Tempo por task | **60 min** | `evaluation.max_time_minutes` |
| Tool calls | **100** (`submit_patch` e `get_status` NÃO contam) | |
| Turns de raciocínio | **500** | |
| Timeout por comando | **300 s** | |
| Output de comando/diff/grafos | **5.000 chars** | |
| `read_file` | **150 linhas / 10.000 chars** | |
| Contexto | **32.768 tokens** (compaction automática aos 14.336) | |
| Sandbox | offline, 4 GiB RAM, 2 vCPU, deps pré-instaladas (NUNCA pip install) | |

### 3.3 Regras de scoring que desenham a estratégia

- **Modelo único obrigatório** entre os 4 QAT permitidos — o nosso `gemma-4-31b-it-qat-w4a16-ct` ✓ (`ALLOWED_MODEL_NAMES`)
- **`submit_patch()` encerra a sessão imediatamente**; fallback automático extrai `git diff` mesmo sem chamar (task nunca fica sem patch por esquecimento)
- **Arquivos protegidos**: mudanças em `test_*.py`, `conftest.py`, `pytest.ini`, `pyproject.toml` etc. são **arrancadas do patch** — o agente conserta a lib, nunca os testes
- **3 nudges** de continuação; tool error vira JSON de erro, não aborta a task
- **Multi-LoRA**: adapters diferentes por agente no MESMO modelo base; rank 16 ≈ 110–220 MB/adapter (cabe 8 no limite de 3 GiB); `max_lora_rank` 128
- **Phase 2**: patch aplicado em container limpo + `test_patch` oficial + pytest hermético; `resolved` = exit 0
- Code intelligence: graphs `.json` + embeddings `.npz` existem para 127 dos 129 repos → as 3 tools de grafo valem ouro na navegação

## 4. Consequências nomeadas

- **A-12 (novo):** `agent.yaml` v0.1 + `configs/eval_config.yaml` violam o schema real → T-03 vira REWORK (migração pro schema ADK canônico). O parse/parse-only da T-03 continua válido como prova de sintaxe YAML; a SEMÂNTICA muda.
- `validate_submission.py` precisa realinhar campos obrigatórios (`name`, `instruction`) — pequeno PR seguinte.
- Redesenho de orquestração: orçamento é 60 min/100 calls POR TASK; sub-agentes custam turns do pai. Estratégia vira S1.

## 5. Veredito

**T-01 PASSA** (integridade provada + schema documentado). **T-03 reaberta como rework de schema (A-12).**
