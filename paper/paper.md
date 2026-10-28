---
status: ESBOCO (T-16, S1) — esqueleto com metodo completo; numeros de resultado pendentes
track: paper track gemma-4-developer-agent ($35k) — deadline de submissao 2026-11-12
fontes: DEC-001..005, FLUXO_F0, evidencias/S0_*, ACHADOS A-12..A-16
regra-dura: nenhum conteudo de Competition Data neste arquivo (so numeros agregados)
---

# [PREENCHER: titulo final] — Post-training a local SWE agent on an honestly small dataset: LoRA r=16 over a Gemma-4 31B QAT W4A16 within a 12-hour global compute budget

**Autores:** [PREENCHER: lista de autores]

## Abstract

[Tese:] we post-train a Gemma-4 31B (QAT W4A16) developer agent under two hard
constraints that make the usual "more data / bigger adapter" playbook
inapplicable: (i) a single official training pool of 129 issue-to-gold-patch
tasks (128 real pairs emitted — zero pairs fabricated, zero empty patches) and
(ii) a global evaluation budget of 12 hours for the whole task suite, with
per-task budgets of 60 minutes / 100 tool calls / 500 turns. Our answer to the
small-data ceiling is a deliberately small adapter (LoRA r=16, alpha=32,
applied directly on the QAT W4A16 checkpoint — no additional quantization)
plus a multi-agent pipeline (analyzer -> generator -> verifier) served with
per-agent adapters inside the 3 GiB adapter budget. Baseline vs. LoRA v1
resolved rate on 10 tasks: [PREENCHER: T-13]. Position statement of this
draft: honest data engineering (leak-proof training pairs built from pre-patch
repo context) and rank discipline beat rank size when the data ceiling is
structural.

**Level of draft:** results section is placeholder-only until T-13 closes; all
unmeasured quantities are marked [PREENCHER] / [A MEDIR].

## 1. Introduction

**Motivação (do problema, não do protocolo):** the competition requires a
single-model agent to resolve unseen GitHub issues in an offline sandbox using
only 9 native tools, within 12 global hours ([A-14, regras oficiais lidas na
página da competição]). The agent must be produced by post-training one
permitted base among the Gemma-4 QAT W4A16 variants; we commit to the largest
one (31B, ~16–18 GB of quantized weights) — DEC-001 — because code navigation
and patch formatting demand reasoning capacity, and the serving model is
hosted by the competition infrastructure (permitted bases:
gemma-4-{31b,12b,e4b,e2b}-it-qat-w4a16-ct; the same base serves every agent).

O que este paper arreda da rima usual "cliente offline precisa de cloud":

- **Dado honrado:** the official training data is a fixed pool of 129 tasks.
  We therefore design the post-training to *fit* the ceiling instead of
  pretending it does not exist: no augmentation beyond context subsets, no
  synthetic patch paraphrasing, and a leak probe proving that every training
  pair presents the repo in its PRE-patch state (0/128 leak signatures).
- **Rank honrado:** with ~1M training tokens per epoch, adapter capacity is
  bounded by what 128 gold patches can teach: r=16 (alpha=32, 2x r), full
  linear coverage (q,k,v,o,gate,up,down), dropout 0.05 — falsifiable upward
  (r=64 sonde) only on an underfit signal (DEC-005 §6).
- **Compute honrado:** per-task budgets (60 min, 100 tool calls, 500 turns)
  coexist with the 12h global ceiling: 129 tasks x 60 min >> 12h, so
  budget-aware prioritization (which tasks to attempt, when to quit) is itself
  a methodological component, not an afterthought.

### 1.1 Roadmap

Section 2 describes the harness constraints; Section 3 the method (data
pipeline, LoRA recipe, multi-agent serving, budget layer); Section 4 reports
[PREENCHER: T-13] preliminary A/B results; Sections 5–7 collect related work,
limitations and ethics statements.

## 2. System setting: the swegemma harness

Constraints that shape every design decision below (measured from
HARNESS_README + probe receipts, evidencias/S0_dataset.md):

| Constraint (per task, defaults) | Value |
|---|---|
| Time / tool calls / turns | 60 min / 100 calls / 500 turns |
| Global wall-clock for ALL tasks | 12 h (including sandbox setup, excluding patch validation) — task-level and global caps COEXIST |
| Context window / compaction | 32,768 tokens; automatic compaction at 14,336 |
| Command output / read_file | 5,000 chars / 150 lines or 10,000 chars |
| Tools | exactly 9: run_command, read_file, edit_file, write_file, submit_patch, get_code_neighbors, search_similar_code, get_code_subgraph, get_status |
| Submission adapters | LoRA only, 3 GiB uncompressed budget for adapters (base served by infra; max_lora_rank 128) |
| Runtime network | offline (no internet in sandbox) |
| Grading | patch applied to a clean container where the official test patch runs pytest; resolved = exit 0 |
| Protected files | edits to test_*.py, conftest.py, pytest.ini, pyproject.toml etc. are stripped from the patch — the agent must fix the library, never the tests |

Harness behaviors we exploit as levers: 'submit_patch' does not count against
the tool-call budget but terminates the session immediately; an automatic
fallback extracts 'git diff' even without an explicit call; 'thinking_config'
(budget up to 32,768) exposes the model's native reasoning; three continuation
nudges recover near-finished sessions.

## 3. Method

### 3.1 Data pipeline: honest SFT pairs from a canonical zip

'scripts/prepare_data.py' streams a single 20.42 GB zip (integrity proven by
CRC test) and emits chat-format JSONL pairs WITHOUT materializing the archive:

1. **Streaming parse** — tasks.jsonl is read line-by-line inside the zip; each
   line is schema-validated (instance_id, repo, gold patch,
   problem_statement required; malformed lines counted, never coerced).
2. **Context selection** — the user turn contains the issue text plus a
   SELECTED repo context, not the full snapshot: exactly the files the gold
   patch touches (parsed from diff headers), read from the snapshot '.tgz' in
   their BASE (pre-patch) version, extended by import-neighborhood files while
   a character budget lasts (60,000 chars ~= 15k tokens total; 8,000 per file;
   truncated with an explicit marker). The assistant turn is the gold patch
   verbatim. Hints are excluded by default to match the evaluation-time
   distribution (the eval agent sees the issue only).
3. **Snapshot matching** — task-to-snapshot resolution by normalized
   instance-id, falling back to the repo slug; paths inside the tar are
   matched by suffix so any directory prefix is tolerated. Result: 128/129
   tasks paired (1 unpaired: no matching snapshot in the archive).
4. **Leak probe (per-file discriminative test)** — for every patch file
   present in the context, REMOVED patch lines must appear in the context and
   ADDED lines must not. Measured: 0/128 pairs with leak signature
   (evidencias/S0_t07_pairs.md; A-15). A naive added-line scan produced 31
   false positives — similar code across neighboring files — the per-file
   analysis is the sound instrument, and it is re-runnable on every dataset
   regeneration ('--check-leak', committed in PR #10).

**Dataset statistics (measured, aggregate only):**

| Statistic | Value |
|---|---|
| Tasks read / pairs emitted / discarded | 129 / 128 / 1 (no matching snapshot) |
| Empty gold patches (invariant) | 0 emitted |
| Duplicates (sha256 of issue+patch) | 0 (128 unique) |
| Estimated pair length (chars/4), p50 / p90 / max | 4,797 / 17,209 / 92,582 tokens |
| Pairs > 32,768 tokens / > 16,384 tokens | 2 / 18 |

### 3.2 LoRA training: rank chosen by data, not by serving

Base: gemma-4-31b-it-qat-w4a16-ct, LoRA applied DIRECTLY on the quantized QAT
checkpoint — no bitsandbytes/NF4 re-quantization (double quantization of an
already QAT-trained 4-bit checkpoint is rejected on quality and dependency
grounds; DEC-005). Configuration:

| Item | Value | Rationale (from DEC-005) |
|---|---|---|
| rank / alpha | 16 / 32 (scaling 2) | ~1M tokens/epoch; more rank buys memorization, not generalization on an unseen repo. r=64 remains a single conditional sonde, only on an underfit signal |
| target_modules | q, k, v, o, gate, up, down | full linear coverage; patch generation is format + code |
| dropout | 0.05 (escalates to 0.1 on trigger G3) | tiny data is the dominant risk, not underfit |
| seq length | 16,384, truncating ONLY the context side (gold patch intact) | p90 = 17,209; the 18 pairs > 16,384 keep their patches whole |
| pair filter | drop the 2 pairs > 32,768 tokens (truncating 92k -> 16k would teach incomplete patches) | 126 usable pairs |
| holdout | 16 pairs (12.5%), stratified by repo | overfit detector (trigger G3); 112 training pairs |
| augmentation | K=2 context-subset variants, resampled per epoch | falsified if it does not move val loss |
| optimization | 5 epochs max, early stopping patience 2; LR 1e-4, cosine, warmup 5%; grad_accum 4 (~140 optimizer steps); loss masked to the assistant turn | small-data recipe: many update steps, capped LR |
| optimizer | paged_adamw_8bit, degrading to adamw_torch if unavailable offline | bf16 LoRA params |

Sessions of <= 6 h frame the whole plan (Kaggle quota: L4x4 consumes GPU quota
at 2x rate, so 30h/week of GPU pool ~= 15h/week of L4x4 session time; DEC-002:
S1 <= 12h, S2 <= 9h). Time/VRAM projections (~15–45 min/epoch; ~26–40 GB of
the measured ~92 GB) are explicitly estimates, falsified at the SES-1 smoke
run: **[PREENCHER: T-11 — s/step, VRAM pico por GPU, tokens/s, split do
device_map, pip freeze]**

**Falsification triggers** (measured, not vibes) — G1: per-GPU VRAM > 20 GiB ->
seq 16,384 -> 8,192; G2: s/step > 45 s -> shrink seq, then 3 epochs; G3: val
loss rising twice -> dropout up / epochs down / r down; G4: session death ->
resume from attached checkpoint; G5: dependency missing offline -> wheel
dataset side-load; G6: fall back to a prompt-only submission (never blocks the
competition); G7: structural OOM -> escalate to root for a base-model decision
(12b).

### 3.3 Multi-agent pipeline and budget layer

Three lanes (DEC-003): 'code_analyzer' (graph tools: get_code_neighbors /
search_similar_code / get_code_subgraph for target-file and hypothesis
diagnosis) -> 'patch_generator' (edit_file / write_file with the
test_generation skill) -> 'verifier' (run_command with the patch_validation
skill) -> submit_patch. The F0 flow (Fig. 1) is the contract: failure loops
back to the generator with a per-issue budget, and desistance is a recorded
rationale, never a silent timeout.

[FIGURA: F0] — Fonte da figura 1: planning/olimp-gemma4-swe-2026-q4/
diagramas/FLUXO_F0.md (renderizar em paper/figures/f0.png —
[PREENCHER: renderizacao do diagrama]). Invariante do diagrama: soma dos
tempos por issue <= 12h global.

Delegation costs turns of the PARENT agent; the mock-measured binding
constraint is the shared tool-call budget, and the per-hop cost hypothesis is
still unmeasured: **[PREENCHER: T04_7 — custo do hop de delegação em calls,
primeiro run real Kaggle]**. Monolithic single-agent is kept as an explicit
A/B baseline. All prompts/skills are generic by construction (the evaluation
repo is unseen; conditioning prompts on the dataset is prohibited by the
rules) — enforced by a fail-closed grep audit (Musa) before any submission.

**Budget-aware prioritization (the 12h layer):** with 129 tasks x 60 min
against a 12h global ceiling, full coverage is arithmetically impossible
(~14 min/issue average ceiling). The submission therefore pairs each
task-group with a budget profile (thinking budget, tool-call allocation, quit
policy) — [PREENCHER: T-13/S1 — perfil escolhido pela distribuição de
dificuldade aparente; contagem de tasks tentadas vs. desistidas].

### 3.4 Serving: train r=16 -> serve r=16, adapters only

The evaluation infrastructure serves the base model; the submission zip
carries only adapters (up to 4 agents x r=16 ~ 0.44–0.88 GB <= 3 GiB, harness
number; per-agent multi-LoRA, with a shared single adapter as v1). Training
rank maps 1:1 to serving rank — no rank compression at serving time. The
adapter export size on the 31B is the one unmeasured serving assumption:
**[PREENCHER: T-12/SES-3 — tamanho real do adapter r=16 no 31B, validado no
'validate_submission.py' antes de qualquer submit]**.

### 3.5 Infrastructure

Kaggle L4x4 (4x NVIDIA L4, 23,034 MiB = ~92 GB measured; torch 2.11.0+cu128;
internet OFF enforced for L4) is the only machine that runs the model — a
root-imposed zero-local rule (DEC-002) that keeps training and evaluation
reproducible in one place. Artifacts are adapter-only (~200–400 MB) with
epoch-saved checkpoints resumed across sessions; base weights are never saved
(20 GB working-disc ceiling). [PREENCHER: T-11 — quota residual por sessão.]

## 4. Preliminary results

**[PREENCHER: T-13 — esta seção é placeholder até o recibo
evidencias/S1_eval_ab.md.]**

- **A/B resolved rate (10 tasks, baseline prompt-only vs. LoRA-v1 + prompts
  v1):** [PREENCHER: T-13 — % por braço, critério do harness: pytest exit 0 no
  container limpo com o test patch oficial].
- **Tempo por task / desistências:** [PREENCHER: T-13 — mediana e p90 de
  tempo por issue; nº de desistências com rationale].
- **Falhas dominantes:** [PREENCHER: T-14 — top-5 padrões de falha (ex.: patch
  não aplica, navegação errada, desiste cedo)].

### 4.1 Training-data distribution (already fixed — from the T-07 receipt)

| Token-bucket (est., chars/4) | Pairs |
|---|---|
| p50 / p90 / max | 4,797 / 17,209 / 92,582 |
| 16,384–32,768 | 18 |
| > 32,768 (descartados no treino) | 2 (126 úteis = 112 treino + 16 holdout) |
| buckets <= 16,384 | [PREENCHER: T-10 — histograma completo sobre os 128 pares] |

[FIGURA: F1 — histograma de comprimento dos pares; fonte: summary.json +
exploração do T-10.]

## 5. Related work

Esqueleto — cada bullet é placeholder de texto a escrever na S2 (T-26), antes
da submissão:

- **SWE-bench e variantes:** benchmark de resolved rate issue->patch;
  [PREENCHER: citação canônica + o que muda no setting swegemma (budget por
  task + teto global + sandbox offline)].
- **LoRA / PEFT:** rank/alpha e razão params/token em regime de dado pequeno:
  [PREENCHER: refs].
- **QAT W4A16:** quantization-aware training como base de adapters:
  [PREENCHER: refs].
- **Multi-agente para SWE:** decomposição analyzer/generator/verifier e
  recomposição: [PREENCHER: refs].
- **Post-training no limite de dado:** few-shot vs. SFT; augmentação de
  contexto vs. multi-época: [PREENCHER: refs — DEC-005 é o fio de argumento].

## 6. Limitations

- **Teto de dado:** 128 pares reais é o máximo honesto do dataset oficial;
  nenhum par é inventado — resultados finais carregam essa variância.
- **Evidência preliminar:** A/B em 10 tasks é amostra fraca; [PREENCHER:
  T-13 — declarar intervalo/confiança ou a falta dele].
- **Instrumento local mockado:** números de resolved rate exibidos antes do
  primeiro run Kaggle real vêm de harness de mocks determinísticos (DEC-002).
- **Custo de delegação não medido (T04_7):** a topologia 3-lanes pode
  subestimar o custo de calls do pai.
- **Truncamento:** 18 pares > 16,384 tokens entram com contexto cortado (patch
  intacto); o efeito dessa perda de contexto não é medido [PREENCHER: T-12 —
  contexto remanescente por par].

## 7. Ethics

- **Conformidade com a regra "prompts cannot be fine-tuned on evaluation
  dataset":** prompts/skills 100% genéricos, auditados por grep fail-closed
  (auditoria da Musa) antes de qualquer submissão.
- **Dado de treino limpo por construção:** probe discriminativa por arquivo
  prova que o contexto de cada par é a versão BASE do repositório (linhas
  removidas do patch presentes no contexto; linhas adicionadas ausentes;
  0/128 leaks). Conteúdo de patch nunca entra no prompt do par.
- **Zero redistribuição de Competition Data:** dataset nunca sai do zip
  canônico; pares emitidos só em storage fora do repositório; o repositório
  contém apenas lógica e números agregados.
- **Credenciais/logging:** nenhum credential em argv/env/log; pipeline
  reproduzível em dois níveis (zip canônico -> pares -> treino).

## 8. Conclusion

[PREENCHER: T-26 — tese final sustentada por A/B real + 3 contribuições
candidatas: (a) rank por razão params/token, (b) probe de leak como
instrumento barato de engenharia de dado, (c) orçamento de 12h global como
alavanca metodológica, não como casualidade.]

## References

[PREENCHER: T-26 — lista de referências; os bullets da seção 5 são os tópicos
candidatos. Nenhuma citação inventada: cada ref entra com DOI/arXiv verificado
ou é removida.]

---

### Apêndice A. Mapa de instrumentos (fonte de cada número)

| Número no paper | Fonte canônica |
|---|---|
| 129 tasks / 128 pares / 0 patch vazio / tokens est. p50/p90/max | evidencias/S0_t07_pairs.md (summary.json) |
| Probe de leak 0/128 | evidencias/S0_t07_pairs.md + A-15 |
| Budgets do harness (global + por task) | HARNESS_README via evidencias/S0_dataset.md; A-12/A-14 |
| L4x4 ~92 GB reais; quota ~15h/sem efetivas | evidencias/S0_kaggle.md |
| LoRA r=16/alpha=32 + gatilhos G1..G7 | decisoes/DEC-005-estrategia-lora.md |
| 3-lane pipeline + compliance anti-hardcode | decisoes/DEC-003-pipeline-multi-agente.md |
| Deadline 12/nov, gate G-PAPER | decisoes/DEC-004-paper-track.md |
