# SPRINT_HEALTH — olimp-gemma4-swe-2026-q4

## Ritual diário (Ayla + Hera, via MCP panteao)
1. Recheck de cap antes de cada onda (`cap_leve_vigente`).
2. Download do dataset: `ls -lh` do zip (progresso %).
3. Quota Kaggle restante da semana (log manual da sessão).
4. PRs abertos/checks do repo.
5. Achado novo → `REGISTRO_DE_ACHADOS.md` + linha no `RISK_REGISTER` se aplicável.

## Placar (foto)

| Sprint | Status | Gate | Observação |
|---|---|---|---|
| S0 | 🟡 aberta | G-BOOTSTRAP | T-08 7/8 ✓ (recibo). T-01 ✓ PASSA (zip íntegro + schema do harness: evidencias/S0_dataset.md). T-02 ✓ FECHADA (PR #3 merged, CI SUCCESS em dev; falta branch protection em main — root). T-03 REWORK (A-12: schema ADK canônico diverge do v0.1; budget real é 60 min/100 calls por task). Pendências: rework do agent.yaml; cap sob carga (W1); limite do modelo gratuito (A-11) |
| S1 | 🔵 planejada | G-BASELINE | — |
| S2 | 🔵 planejada | G-PIPELINE + G-PAPER | paper 12/nov (A-04) |
| S3 | 🔵 planejada | G-DPO | — |
| S4 | 🔵 planejada | G-SUBMISSAO | submissão de segurança 28/nov |
| S5 | 🔵 planejada | G-FINAL | final até 29/nov (folga 72h) |