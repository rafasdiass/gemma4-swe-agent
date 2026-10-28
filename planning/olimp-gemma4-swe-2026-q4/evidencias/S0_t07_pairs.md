# T-07 — Pares SFT: recibo de execução (2026-10-28)

## Comandos (host, venv py3.12 via uv)

```
uv run --no-project --python 3.12 --with pyyaml python scripts/prepare_data.py \
    --zip C:\gemma4-data\gemma-4-developer-agent.zip --out C:\gemma4-data\sft_pairs
```

Smoke prévio com `--limit 5`: 6 tasks lidas, 5 pares, 1 descarte `sem_contexto`.

## Números medidos (summary.json)

| Métrica | Valor |
|---|---|
| tasks lidas | 129 |
| pares emitidos | 128 |
| descartes | 1 (`sem_contexto`: snapshot não casado) |
| patch vazio | **0** (invariante: linha com gold patch vazio é descartada, nunca emitida) |
| dedup (sha256 issue+patch) | 128 únicos, 0 duplicados |
| tokens est. (chars/4) p50/p90/max | 4.797 / 17.209 / 92.582 |
| pares > 32.768 tokens (janela do modelo) | **2** — filtrar/truncar no treino |
| pares > 16.384 tokens | 18 |

## DoD

- **"≥1.000 pares válidos OU justificativa do teto real"** → teto real justificado: o dataset tem 129 tasks com 1 gold patch cada; teto honesto ≤129. Nenhum par inventado. `ceiling_note` embutido no `summary.json`.
- **"zero par com patch vazio"** → provado por varredura independente das 128 linhas de `pairs.jsonl` (assistant vazio: 0).

## Mitigações do teto (insumo S1, do ceiling_note)

1. Augmentação de contexto (variantes de subconjunto de arquivos por par).
2. Multi-época no LoRA.
3. Few-shot/LoRA leve dimensionado pra ~100 exemplos.

## Formato do par (pairs.jsonl, fora do repo)

`{id: sft-<sha256[:16]>, instance_id, repo, messages: [system, user(issue+contexto base selecionado), assistant(gold patch verbatim)], meta: {n_context_files, context_chars, est_tokens, dedup_hash}}`

- Contexto do user turn: arquivos tocados pelo gold patch em versão BASE (pré-patch) + vizinhança por imports; orçamento 60.000 chars (≈15k tokens), `--per-file-chars` 8.000.
- `hints_text` EXCLUÍDO por default (no eval o agente só vê a issue; distribuição de treino casa).
- Saída em `C:\gemma4-data\sft_pairs\` — **FORA do repo** (regra dura de visibilidade pública). O script recusa `--out` dentro do repo (`ensure_outside_repo`).
- `summary.json` contém só números agregados: nenhum instance_id, nenhum conteúdo de Competition Data no repo.

## Testes

`tests/test_prepare_data.py`: 12 testes com mini-zip sintético em `tmp_path` (zero dado real): parse, dedup, descarte de patch vazio, seleção de contexto, recusa de out-dentro-do-repo. Suite total do repo: **39 passed**; ruff/mypy limpos.

## Observação de execução

- Matching de snapshot por `instance_id` → `repo` slug funcionou de primeira: 128/129 casados (1 sem snapshot no zip, consistente com os 127/129 de graph+embeddings).
