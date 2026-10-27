# ROADMAP — olimp-gemma4-swe-2026-q4

> Marcos com gate binário. Data de hoje: 2026-10-27. Deadline final **imexível**: 02/dez/2026.

## Marcos

| Marco | Data alvo | Gate | Critério binário |
|---|---|---|---|
| M0 | 31/out | **G-BOOTSTRAP** | Dataset 20.4GB extraído com ≥1 issue real inspecionada; `simulate_sandbox.py` PASS em 1 issue; CI verde no PR #1 mergeado |
| M1 | 07/nov | **G-BASELINE** | Notebook Kaggle `02_train_lora_v1` rodou em L4x4 com recibo (W&B); eval harness 10 issues: LoRA v1 ≥ baseline |
| M2 | 12/nov | **G-PIPELINE** + **G-PAPER** | Pipeline 3-agente E2E ≥ baseline em 10 issues; **paper submetido no paper track (deadline 12/nov)** |
| M3 | 21/nov | **G-DPO** | LoRA v3 (DPO) > v2 em stress 50 issues; budget/issue medido < 12h/50 |
| M4 | 28/nov | **G-SUBMISSAO** | `submission.zip` passa `validate_submission.py`; simulação completa ≤ 12h; dry-run no Kaggle ok |
| M5 | 02/dez | **G-FINAL** | Submissão final confirmada (recibo da plataforma); buffer de 72h para rollback |

## Estado e lacunas

- Dataset: download em andamento (reiniciado 2026-10-27 após queda em 2.7GB).
- Quota Kaggle L4x4: ~15h/sem efetivas (2x quota) — **restrição dura**: treinos cabem em ≤4 sessões de 6h.
- Paper track deadline (12/nov) cai NO MEIO da Sprint 2 — o esboço do paper é task da Sprint 1, não da 4 (correção do protocolo original).

## Decisões pendentes

- Estratégia de fallback se LoRA 31B não caber em 6h/sessão na L4x4 (offload CPU vs reduzir r/alpha).
- Se vale concorrer ao small model bonus com E2B paralelo (só se sobrar quota após M3).