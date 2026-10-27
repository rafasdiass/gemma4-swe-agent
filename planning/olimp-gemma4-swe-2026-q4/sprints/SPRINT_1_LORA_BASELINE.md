# SPRINT 1 — LoRA v1 baseline + esboço do paper (`T-10..T-16`)

**Status:** 🔵 PLANEJADA
**Janela:** 03–07 nov 2026 · **Gate de saída:** G-BASELINE
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
- **DoD específico:** log Kaggle + W&B run; VRAM pico < 90GB; tempo/passo documentado ⇒ extrapolação de sessão ≤6h.
- **Depende de:** T-06, T-07
- **Paralelizável com:** — (quota)

### T-12 — Treino LoRA v1 completo (QLoRA r=128)
- **Domínio:** Treino
- **Classe:** PESADO
- **Lead:** Apolo
- **Apoio:** Yara
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** `adapters/lora-v1/*.safetensors` + config de treino versionado + W&B run público no repo (DVC/LFS).
- **DoD específico:** adapter carrega no harness local (`simulate_sandbox.py --adapter lora-v1`); loss final < smoke; checkpoint intermediário salvo (rollback).
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
- **Paralelizável com:** T-10..T-15