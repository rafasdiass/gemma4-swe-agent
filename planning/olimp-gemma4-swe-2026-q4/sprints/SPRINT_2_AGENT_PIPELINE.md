# SPRINT 2 — Pipeline 3-agente + skills + submissão do paper (`T-20..T-27`)

**Status:** 🔵 PLANEJADA
**Janela:** 10–14 nov 2026 · **Gate de saída:** G-PIPELINE + **G-PAPER (12/nov, imexível)**
**Objetivo:** pipeline multi-agente E2E superando o baseline; skills genéricas exercitadas; **paper submetido no paper track até 12/nov**.
**Ancoragem:** [ROADMAP M2](../ROADMAP.md) · [SPRINT_1](SPRINT_1_LORA_BASELINE.md)

**Critério de entrada:** G-BASELINE FECHADO (LoRA v1 com recibo; sem v1 não há régua de comparação).

## Meta do sprint
Pipeline completo (analyzer→coder→verifier com skills) com resolved rate em 10 issues **>** single-shot baseline (T-13). Paper no ar no paper track **antes de 12/nov 23:59 UTC**.

## Paralelismo (cap calculado)
| Campo | Valor |
|-------|-------|
| Host | Kaggle L4x4 (PESADO: LoRA v2) + máquina de execução (LEVE) |
| cap_leve_inicial | 6 (medido na S0/T-08) |
| cap_pesado_inicial | 1 |
| Sprint mista? | sim → PESADO domina |

**Waves:** W1 = T-20, T-21, T-22 (leve) · W2 = T-23 (PESADO, LoRA v2) · W3 = T-24 (leve) · W4 = T-25, T-26 (leve) · **W5 = T-27 (paper — dependência T-26 fechada; prioridade absoluta na data: deadline 12/nov é imexível; subir o cronograma se W3 atrasar, cortando T-25 primeiro)**.

## Tasks

### T-20 — Skills `repo_navigation` e `patch_validation` exercitadas em issues reais
- **Domínio:** Implementação
- **Classe:** LEVE
- **Lead:** Apolo
- **Apoio:** Artemis
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** skills chamadas pelo pipeline no harness em 10 issues; uso das tools de grafo (`get_code_neighbors`, `search_similar_code`, `get_code_subgraph`) logado.
- **DoD específico:** ≥1 tool de grafo usada por issue no log; nenhuma skill quebra o ciclo.
- **Depende de:** S0-T-04, S1-T-13
- **Paralelizável com:** T-21

### T-21 — `test_generation` calibrada (testes que discriminam patch bom/ruim)
- **Domínio:** QA / dados
- **Classe:** LEVE
- **Lead:** Hefesto
- **Apoio:** Afrodite
- **Verificação:** Atena
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefeto/identity-kernel.md)
- **Contrato de saída:** prompts/skill da skill de teste revisados; no harness, teste gerado falha no patch errado e passa no gold.
- **DoD específico:** matriz confusão (patch bom/ruim × teste pass/fail) em `evidencias/S2_testgen.md`.
- **Depende de:** T-20
- **Paralelizável com:** T-22

### T-22 — Orquestração de budget no `agent.yaml` (12h, priorização de issue)
- **Domínio:** Arquitetura / contrato
- **Classe:** LEVE
- **Lead:** Atena
- **Apoio:** Hera
- **Verificação:** Musa
- **kernel-verificado:** Atena (arquitetura <- packages/agents/profiles/atena/identity-kernel.md)
- **Contrato de saída:** `configs/sampling.yaml` + lógica de orçamento: teto por issue (~10min), ordem de ataque, desistência com rationale.
- **DoD específico:** simulação local com relógio acelerado nunca excede 12h/50 issues.
- **Depende de:** S1-T-14
- **Paralelizável com:** T-20, T-21

### T-23 — LoRA v2 com dados de trajetória do pipeline
- **Domínio:** Treino
- **Classe:** PESADO
- **Lead:** Apolo
- **Apoio:** Yara
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** dataset SFT enriquecido com trajetórias (diagnóstico → patch → verificação) das issues resolvidas pelo pipeline; `adapters/lora-v2/`.
- **DoD específico:** resolved rate v2 > v1 nas mesmas 10 issues (mesma régua).
- **Depende de:** T-20, T-21
- **Paralelizável com:** — (quota)

### T-24 — Eval A/B/C: single-shot vs pipeline vs pipeline+LoRA v2
- **Domínio:** Avaliação
- **Classe:** LEVE
- **Lead:** Hefesto
- **Apoio:** Yara
- **Verificação:** Afrodite
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefesto/identity-kernel.md)
- **Contrato de saída:** tabela comparativa em `evidencias/S2_eval_abc.md`; vencedor escolhido para o DPO da S3.
- **DoD específico:** diferença estatisticamente nomeada (n pequeno: direção + magnitude, sem teatro de p-valor).
- **Depende de:** T-23
- **Paralelizável com:** T-26

### T-25 — Registro de achados da S2 e abertura das tasks da S3
- **Domínio:** Estado / continuidade
- **Classe:** LEVE
- **Lead:** Hera
- **Apoio:** Hermes
- **Verificação:** Gaia
- **kernel-verificado:** Hera (fluxo <- packages/agents/profiles/hera/identity-kernel.md)
- **Contrato de saída:** `monitoring/REGISTRO_DE_ACHADOS.md` atualizado; backlog da S3 conferido contra os achados.
- **DoD específico:** todo achado tem task ou motivo datado de não-ter.
- **Depende de:** T-24
- **Paralelizável com:** T-26

### T-26 — Figuras e números finais do paper
- **Domínio:** Documentação / paper
- **Classe:** LEVE
- **Lead:** Gaia
- **Apoio:** Yara
- **Verificação:** Rafael (root)
- **kernel-verificado:** Gaia (conhecimento <- packages/agents/profiles/gaia/identity-kernel.md)
- **Contrato de saída:** paper com figuras F0 (fluxo), resultados A/B/C e limitações; pronto para submissão.
- **DoD específico:** compila sem erro; referências checadas; autoria conforme regra do paper track.
- **Depende de:** T-24, S1-T-16
- **Paralelizável com:** T-25

### T-27 — **Submissão do paper track (deadline 12/nov)**
- **Domínio:** Entrega / prazo imexível
- **Classe:** LEVE
- **Lead:** Hera
- **Apoio:** Gaia
- **Verificação:** Rafael (root, confirmação final)
- **kernel-verificado:** Hera (fluxo <- packages/agents/profiles/hera/identity-kernel.md)
- **Contrato de saída:** paper submetido no paper track da competição com recibo (ID/url).
- **DoD específico:** recibo salvo em `evidencias/S2_paper_submitted.md` **antes de 12/nov 23:59 UTC**; se não der, DEC-004 registra o abandono com rationale.
- **Depende de:** T-26
- **Paralelizável com:** — (crítico)