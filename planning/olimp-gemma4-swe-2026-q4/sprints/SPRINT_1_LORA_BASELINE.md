# SPRINT 1 — LoRA v1 baseline + esboço do paper (`T-10..T-16`)

**Status:** 🟡 EM CURSO (2026-10-28)
**Janela:** 03–07 nov 2026 · **Gate de saída:** G-BASELINE

**Despacho 2026-10-28 (pre-sprint):** T-11-prep fechada — `scripts/train_lora.py` + `configs/train_lora_v1.yaml` implementam a DEC-005 (PR #11, 45 passed + 2 testes de integração dry-mode verdes em torch CPU); `--check-leak` commitado no `prepare_data.py` (PR #10, A-15 repetível). Insumo do SES-1: os 10 itens `[A MEDIR NA S1]` no header do `train_lora.py`.
**Objetivo:** primeiro treino LoRA completo em Kaggle L4x4, eval A/B contra baseline em 10 issues, esboço do paper com resultados preliminares.
**Ancoragem:** [ROADMAP M1](../ROADMAP.md) · [SPRINT_0](SPRINT_0_BOOTSTRAP.md) (T-07 define os pares)

**Critério de entrada:** G-BOOTSTRAP FECHADO (dataset + harness + ADR LoRA: sem eles não há treino nem régua).

## Meta do sprint
LoRA v1 treinada (recibo W&B) com resolved rate em 10 issues **≥** baseline sem adapter. Paper esboçado (intro + método + resultados preliminares).

## Paralelismo (cap calculado)
| Campo | Valor |
|-------|-------|
| Host | Kaggle L4x4 (PESADO) + máquina de execução (LEVE) |
| cap_leve_inicial | 6 |
| cap_pesado_inicial | 1 sessão Kaggle por vez (quota serializa) |
| Sprint mista? | sim → PESADO domina: sessões de treino têm prioridade de quota |

**Waves:** W1 = T-11 (PESADO, sessão Kaggle: exploração + smoke SFT) · W2 = T-12 (PESADO: treino v1 completo) · W3 = T-13, T-16 (leve) · W4 = T-14, T-15.
**Quota:** ≤2 sessões de ≤6h nesta sprint (deixa ~3h para S2).

## Tasks

### T-10 — Notebook `01_data_exploration` no Kaggle
- **Domínio:** Dados / análise
- **Classe:** LEVE (sessão curta)
- **Lead:** Yara
- **Apoio:** Atlas
- **Verificação:** Afrodite
- **kernel-verificado:** Yara (analytics <- packages/agents/profiles/yara/identity-kernel.md)
- **Contrato de saída:** notebook rodado com contagem de issues, distribuição de linguagens/repos, tamanho médio de patch, outliers.
- **DoD específico:** recibo (output do notebook) em `evidencias/S1_exploracao.md`; tabela de distribuição no paper.
- **Depende de:** T-07
- **Paralelizável com:** T-16

### T-11 — Smoke test SFT em L4x4 (1k passos)
- **Domínio:** Treino / infra
- **Classe:** PESADO
- **Lead:** Apolo
- **Apoio:** Zeus
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** `02_train_lora_v1` com smoke de 1k passos: loss converge, OOM não ocorre, tempo/passo medido.
- **DoD específico:** log Kaggle + W&B run; VRAM pico < 20 GiB POR GPU (G1 da DEC-005 — não <90GB total); tempo/passo documentado ⇒ extrapolação de sessão ≤6h; probes do 31B precisam ≥2 GPUs (máx 2 probes paralelos).
- **Depende de:** T-06 (DEC-005 pronta: base 31B QAT), T-07
- **Paralelizável com:** — (quota)

### T-12 — Treino LoRA v1 completo (DEC-005: LoRA direto no 31B QAT, r=16/alpha=32)
- **Domínio:** Treino
- **Classe:** PESADO
- **Lead:** Apolo
- **Apoio:** Yara
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Premissas (DEC-005 revisada, ACEITA 2026-10-28):** base `gemma-4-31b-it-qat-w4a16-ct`; LoRA direto no QAT (sem bitsandbytes); r=16/alpha=32/dropout 0.05/7 lineares; seq len 16384 (truncar contexto, patch intacto); drop dos 2 pares >32k; holdout 12.5%; K=2 augmentação; 5 épocas early stop; LR 1e-4; loss só no assistant; ~26–40GB/92GB via device_map; gatilhos G1..G7 de falsificação.
- **Contrato de saída:** `adapters/lora-v1/*.safetensors` + config de treino versionado + W&B run público no repo (DVC/LFS).
- **DoD específico:** adapter carrega no harness local (`simulate_sandbox.py --adapter lora-v1`); loss final < smoke; checkpoint intermediário salvo (rollback); adapter r=16 validado contra `validate_submission.py` antes de qualquer submit (R-T06-8).
- **Depende de:** T-11
- **Paralelizável com:** T-16

### T-13 — Eval A/B: baseline vs LoRA v1 (10 issues)
- **Domínio:** Avaliação / QA
- **Classe:** LEVE (harness local; GPU só para inferência se houver quota — senão mock determinístico)
- **Lead:** Hefesto
- **Apoio:** Yara
- **Verificação:** Afrodite
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefesto/identity-kernel.md)
- **Contrato de saída:** `evidencias/S1_eval_ab.md` com tabela issue×{baseline, lora-v1} resolved rate e tempo.
- **DoD específico:** resolved rate LoRA ≥ baseline; discrepâncias nomeadas por issue.
- **Depende de:** T-12, T-04
- **Paralelizável com:** T-16

### T-14 — Diagnóstico de falhas por issue (top-5)
- **Domínio:** Análise
- **Classe:** LEVE
- **Lead:** Hermes
- **Apoio:** Atena
- **Verificação:** Yara
- **kernel-verificado:** Hermes (auditoria <- packages/agents/profiles/hermes/identity-kernel.md)
- **Contrato de saída:** `monitoring/REGISTRO_DE_ACHADOS.md` atualizado com os 5 padrões de falha mais caros (ex.: patch não aplica, teste errado, desiste cedo demais).
- **DoD específico:** cada achado vira A-NN com task correspondente na S2/S3.
- **Depende de:** T-13
- **Paralelizável com:** T-15

### T-15 — Ajuste de prompts com base nos achados
- **Domínio:** Implementação
- **Classe:** LEVE
- **Lead:** Apolo
- **Apoio:** Atena
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** `prompts/*.md` revisados (genéricos, sem hardcode); regra anti-hardcode conferida (`grep` de termos do dataset proibido).
- **DoD específico:** `scripts/validate_submission.py --check-prompts` PASS; melhora no harness nas issues dos achados.
- **Depende de:** T-14
- **Paralelizável com:** T-16

### T-16 — Esboço do paper (intro, método, preliminares)
- **Domínio:** Documentação / paper track
- **Classe:** LEVE
- **Lead:** Gaia
- **Apoio:** Atena
- **Verificação:** Rafael (root)
- **kernel-verificado:** Gaia (conhecimento <- packages/agents/profiles/gaia/identity-kernel.md)
- **Contrato de saída:** `paper/` no repo: esqueleto LaTeX/Markdown com intro, método (pipeline + LoRA), resultados preliminares do T-13; **deadline real: submissão até 12/nov (S2)**.
- **DoD específico:** seção de método completa; figuras do fluxograma F0 incluídas.
- **Depende de:** T-13 (números) — pode começar paralelo com rascunho
- **STATUS 2026-10-28:** DESPACHADA (Gaia — esqueleto; números entram quando T-13 fechar)
- **Paralelizável com:** T-10..T-15