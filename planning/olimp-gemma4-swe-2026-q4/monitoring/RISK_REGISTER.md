# RISK_REGISTER — olimp-gemma4-swe-2026-q4

| ID | Risco | Prob | Impacto | Resposta | Dono |
|---|---|---|---|---|---|
| R-01 | Quota Kaggle estoura antes da S4 | média | alto | orçamento por sprint (DEC-002); reserva ≥6h para S4; treino v2 opcional é o primeiro corte | Zeus |
| R-02 | Treino 31B não cabe em sessão de 6h | média | alto | plano B DEC-005 (r=64/offload); smoke T-11 decide na S1, não na S3 | Atena |
| R-03 | Download do dataset (20.4GB) cai de novo | alta | médio | retomada parcial do kaggle CLI; alternativa: notebook Kaggle baixa e exporta por API | Zeus |
| R-04 | Violar anti-hardcode (prompts citam dataset) | baixa | crítico | auditoria fail-closed da Musa (T-33/T-43) antes de qualquer submissão | Musa |
| R-05 | Formato ADK rejeitado na plataforma | baixa | crítico | `validate_submission.py --strict` espelha a checklist oficial; submissão de segurança na S4 (T-45) descobre cedo | Hefesto |
| R-06 | Paper perde deadline 12/nov | média | alto ($35k) | T-16 na S1, T-26/T-27 com prioridade absoluta; parcial é aceitável (DEC-004) | Hera |
| R-07 | Sandbox real difere do harness local | média | médio | simulação da S4 (T-42) com inferência real; margem de 10% no budget | Hefesto |
| R-08 | 12h de budget não fecha (~14min/issue) | média | alto | orçamento por issue no sampling (T-22); desistência com rationale; stress 50 issues mede cedo (T-34) | Atena |

> Atualização: [SPRINT_HEALTH](SPRINT_HEALTH.md) diário; achados novos viram linha aqui + task.