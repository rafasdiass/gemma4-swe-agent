# PRODUCT_BACKLOG — olimp-gemma4-swe-2026-q4

Épicos → sprints. Prioridade: E1 > E2 > E3 (paper) > E4 (otimização) > E5 (contingência).

| Épico | Tema | Sprint | Tasks |
|---|---|---|---|
| E1 | Agente funcional (pipeline + skills + LoRA) | S0–S2 | T-01..T-27 |
| E2 | Qualidade (DPO, sampling, stress) | S3 | T-30..T-36 |
| E3 | Paper track ($35k) | S1–S2 | T-16, T-24 (paper no 12/nov) |
| E4 | Embalagem e submissão | S4–S5 | T-40..T-54 |
| E5 | Contingência (fallback, rollback, buffer) | S3–S5 | T-36, T-46, T-54 |

## Histórias por épico (resumo)

### E1 — Agente funcional
- Agente resolve 1 issue real de ponta a ponta no harness local (mock das 9 tools).
- LoRA v1 treinada em Kaggle com recibo; eval A/B contra baseline.
- Pipeline 3-agente com skills e grafo de código integrados.

### E2 — Qualidade
- DPO com pares chosen/rejected das trajetórias do pipeline.
- Stress 50 issues com medição de tempo/issue (budget 12h ⇒ ~14min/issue teto).

### E3 — Paper track
- Esboço na S1 (método + resultados preliminares), submissão até 12/nov (S2).

### E4 — Embalagem
- `assemble_agent.py` + `validate_submission.py` com checklist completo; dry-run no Kaggle.

### E5 — Contingência
- Plano B: reduzir rank LoRA / offload se treino não caber em sessão de 6h.
- Buffer de 72h antes do deadline final; submissão de segurança na S4 (antes da final).