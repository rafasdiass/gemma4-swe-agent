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
| S0 | 🟡 aberta | G-BOOTSTRAP | T-08 7/8 ✓ (recibo). T-01 ✓ PASSA. T-02 ✓ FECHADA (PR #3; falta branch protection em main — root). T-09 ✓ FECHADA (PR #4). T-04 ✓ FECHADA (PR #5, T09_R6/R7 medidos — A-13). T-07 ✓ FECHADA (PR #6; verificação Afrodite FECHA COM RESSALVA → probe por arquivo: LIMPO 0/128 — A-15). T-05 ✓ FECHADA (4× L4 ≈92GB, quota 00:01/30h, Persona concluída — recibo S0_kaggle.md). T-06 ✓ FECHADA (DEC-005 ACEITA: 31B QAT confirmado pelo root — GATE-ROOT-01/A-16; r=16/alpha=32; gatilhos G1..G7). Pendências: branch protection em main (root); observação: `.dvc/config` modificado fora do fluxo (root decide) |
| S1 | 🔵 planejada | G-BASELINE | — |
| S2 | 🔵 planejada | G-PIPELINE + G-PAPER | paper 12/nov (A-04) |
| S3 | 🔵 planejada | G-DPO | — |
| S4 | 🔵 planejada | G-SUBMISSAO | submissão de segurança 28/nov |
| S5 | 🔵 planejada | G-FINAL | final até 29/nov (folga 72h) |