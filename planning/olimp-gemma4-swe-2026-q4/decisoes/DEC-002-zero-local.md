# DEC-002 — Zero execução local: treino/eval só no Kaggle L4x4

**Data:** 2026-10-27 · **Decisora:** Ayla · **Aprovação:** Rafael (root)
**Estado:** ACEITA (restrição do root)

- A máquina local não roda o modelo 31B (nem inferência). Orquestração Panteão/planning roda em CPU local; **qualquer** execução do modelo (treino, eval com inferência, simulação) é em Kaggle L4x4 (ou cloud pago só por decisão do root).
- Consequência: harness local (`simulate_sandbox.py`) usa mocks determinísticos das 9 tools; números de resolved rate **reais** só saem de sessão Kaggle.
- Quota: ~15h/sem efetivas (2x). Orçamento por sprint no cap de cada uma: S1 ≤12h, S2 ≤9h, S3 ≤18h, S4 ≤6h. Total ≈ dentro de 4 semanas.