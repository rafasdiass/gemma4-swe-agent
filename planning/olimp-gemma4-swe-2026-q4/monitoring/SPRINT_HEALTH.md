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
| S0 | ✅ fechada | G-BOOTSTRAP | T-01..T-09 fechadas (T-08 7/8 — item restante é o smoke real PESADO, movido pra S1). Recibos: S0_bootstrap_maquina, S0_dataset, S0_kaggle (4× L4 ≈92GB, ~15h/sem), S0_t07_pairs (128 pares, leak LIMPO — A-15). DEC-001..005 assinadas (DEC-005 revisada/ACEITA: 31B QAT W4A16, GATE-ROOT-01 fechado — A-16). Pendências ficadas: branch protection em main (root), `.dvc/config` modificado (root decide) |
| S1 | 🟡 aberta | G-BASELINE | Pre-sprint despachado 2026-10-28: T-11-prep FECHADA (`scripts/train_lora.py` + config DEC-005, PR #11; 2 testes de integração dry-mode verdes em torch CPU; 10 itens [A MEDIR NA S1] no header); `--check-leak` commitado (PR #10); T-16 esqueleto do paper pronto (PR #12, placeholders com dono). Próxima: **T-11 SES-1 (PESADO)** — smoke no Kaggle L4x4, sem consumir browser; depois T-10/T-13. Quota de S1: ≤2 sessões ≤6h |
| S1 | 🔵 planejada | G-BASELINE | — |
| S2 | 🔵 planejada | G-PIPELINE + G-PAPER | paper 12/nov (A-04) |
| S3 | 🔵 planejada | G-DPO | — |
| S4 | 🔵 planejada | G-SUBMISSAO | submissão de segurança 28/nov |
| S5 | 🔵 planejada | G-FINAL | final até 29/nov (folga 72h) |