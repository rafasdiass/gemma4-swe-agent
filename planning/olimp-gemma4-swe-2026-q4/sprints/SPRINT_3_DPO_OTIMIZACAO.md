# SPRINT 3 — DPO, sampling e stress 50 issues (`T-30..T-36`)

**Status:** 🔵 PLANEJADA
**Janela:** 17–21 nov 2026 · **Gate de saída:** G-DPO
**Objetivo:** LoRA v3 com DPO sobre trajetórias reais, sampling otimizado, stress test de 50 issues dentro do budget 12h.
**Ancoragem:** [ROADMAP M3](../ROADMAP.md) · [SPRINT_2](SPRINT_2_AGENT_PIPELINE.md)

**Critério de entrada:** G-PIPELINE FECHADO e T-27 resolvido (paper: submetido ou abandono com DEC).

## Meta do sprint
Stress 50 issues: resolved rate LoRA v3 (DPO) **>** v2; tempo total medido **≤ 12h** extrapolado (≤14min/issue médio). Fallback decidido se DPO não bater v2.

## Paralelismo (cap calculado)
| Campo | Valor |
|-------|-------|
| Host | Kaggle L4x4 (PESADO: DPO) + máquina de execução (LEVE) |
| cap_leve_inicial | 6 |
| cap_pesado_inicial | 1 |
| Sprint mista? | sim → PESADO domina |

**Waves:** W1 = T-30 (leve) · W2 = T-31 (PESADO: DPO) · W3 = T-32, T-33 (leve) · W4 = T-34 (leve, medição) · W5 = T-35, T-36.
**Quota:** ≤3 sessões ≤6h; reserva ≥6h para a S4 (simulação final).

## Tasks

### T-30 — Dataset DPO (pares chosen/rejected)
- **Domínio:** Dados
- **Classe:** LEVE
- **Lead:** Yara
- **Apoio:** Afrodite
- **Verificação:** Atlas
- **kernel-verificado:** Yara (analytics <- packages/agents/profiles/yara/identity-kernel.md)
- **Contrato de saída:** `scripts/prepare_data.py --mode dpo` emitindo pares chosen (trajetória que resolveu) / rejected (trajetória que falhou) das 10+50 issues do harness.
- **DoD específico:** ≥200 pares; zero par com chosen==rejected; balanceamento documentado.
- **Depende de:** S2-T-24
- **Paralelizável com:** —

### T-31 — Treino DPO (LoRA v3)
- **Domínio:** Treino
- **Classe:** PESADO
- **Lead:** Apolo
- **Apoio:** Yara
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** `notebooks/03_train_dpo` rodado; `adapters/lora-v3/` + W&B run.
- **DoD específico:** loss DPO converge; eval nas mesmas 10 issues antes do stress (gate de entrada).
- **Depende de:** T-30
- **Paralelizável com:** — (quota)

### T-32 — Grid de sampling (temperature, top_p, max rep)
- **Domínio:** Avaliação / otimização
- **Classe:** LEVE
- **Lead:** Yara
- **Apoio:** Hefesto
- **Verificação:** Atena
- **kernel-verificado:** Yara (analytics <- packages/agents/profiles/yara/identity-kernel.md)
- **Contrato de saída:** grid pequeno (≤9 configs × 10 issues) no harness; melhor config fixada no `configs/sampling.yaml`.
- **DoD específico:** melhora ≥ v2 na mesma régua; config vencedora versionada.
- **Depende de:** S2-T-24
- **Paralelizável com:** T-31

### T-33 — Salvaguardas do sandbox (sem internet, 9 tools só)
- **Domínio:** Segurança / policy
- **Classe:** LEVE
- **Lead:** Musa
- **Apoio:** Artemis
- **Verificação:** Hefesto
- **kernel-verificado:** Musa (security <- packages/agents/profiles/musa/identity-kernel.md)
- **Contrato de saída:** auditoria do pipeline: nenhum tool call fora das 9; nenhum fetch externo; prompts sem termos do dataset de avaliação.
- **DoD específico:** auditoria com recibo em `evidencias/S3_policy.md`; violações viram achados A-NN.
- **Depende de:** T-22
- **Paralelizável com:** T-31

### T-34 — Stress test 50 issues com orçamento medido
- **Domínio:** Avaliação / QA
- **Classe:** LEVE (harness; inferência por subscription se preciso)
- **Lead:** Hefesto
- **Apoio:** Zeus
- **Verificação:** Afrodite
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefesto/identity-kernel.md)
- **Contrato de saída:** `evidencias/S3_stress.md`: 50 issues, resolved rate v3 vs v2, tempo total e por issue, distribuição de desistências.
- **DoD específico:** tempo extrapolado ≤ 12h; resolved rate v3 > v2 **ou** DEC de fallback (ficar na v2).
- **Depende de:** T-31, T-32
- **Paralelizável com:** T-35

### T-35 — Atualização do RISK_REGISTER com riscos da S4
- **Domínio:** Estado / continuidade
- **Classe:** LEVE
- **Lead:** Hera
- **Apoio:** Hermes
- **Verificação:** Atena
- **kernel-verificado:** Hera (fluxo <- packages/agents/profiles/hera/identity-kernel.md)
- **Contrato de saída:** [RISK_REGISTER](../monitoring/RISK_REGISTER.md) com plano de resposta por risco (OOM, quota, rejeição de formato).
- **DoD específico:** todo risco tem resposta datada e dono.
- **Depende de:** T-34
- **Paralelizável com:** —

### T-36 — Plano B de treino (offload/redução) decidido ou descartado
- **Domínio:** Arquitetura / decisão
- **Classe:** LEVE
- **Lead:** Atena
- **Apoio:** Apolo
- **Verificação:** Rafael (root)
- **kernel-verificado:** Atena (arquitetura <- packages/agents/profiles/atena/identity-kernel.md)
- **Contrato de saída:** DEC registrada: manter v3/v2 ou re-treinar com rank menor/offload; deadline interno 21/nov.
- **DoD específico:** decisão com recibo (números do T-34) — não vale "achismo".
- **Depende de:** T-34
- **Paralelizável com:** T-35