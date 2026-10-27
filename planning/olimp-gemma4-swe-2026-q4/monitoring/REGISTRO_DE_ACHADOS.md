# REGISTRO_DE_ACHADOS — olimp-gemma4-swe-2026-q4

Todo gap, bug ou surpresa vira achado `A-NN` (com task correspondente ou motivo datado de não ter).

## Abertos

| ID | Data | Achado | Impacto | Task |
|---|---|---|---|---|
| A-01 | 2026-10-27 | Download do dataset caiu em 2.7GB (processo morto); reiniciado com `nohup` (PID 91921) | risco R-03 | monitorar S0/T-01 |
| A-02 | 2026-10-27 | Pares gold do Neon (`gold_curation_pairs`, `training_pairs`) NÃO servem como dados SWE-bench (formato conversa/auditoria ≠ issue→patch) | dados de treino vêm 100% do dataset oficial | T-07 (S0) |
| A-03 | 2026-10-27 | Push direto a `main` é hardDeny (musa); PR obrigatório — PR #1 aberto com workflows, que exigem token com escopo `workflow` (gh keyring tem; keys.env não tem) | fluxo repo só por PR | T-02 (S0) |
| A-04 | 2026-10-27 | Protocolo original colocava o draft do paper na S4; deadline real do paper track é 12/nov (S2) | correção de planejamento | T-16/T-27 |
| A-05 | 2026-10-27 | **Execução muda de máquina**: a que criou o repo não executa a planning. Download local morto (PID 91921) e zip removido; T-08 (bootstrap da máquina de execução) criada como W0 — tudo da S0 depende dela. Cap do paralelismo se mede LÁ, não aqui | planejamento | T-08 (S0) |

## Fechados

| ID | Data | Fechamento | Evidência |
|---|---|---|---|
| A-03 | 2026-10-27 | Remote limpo (token fora da URL): keyring do `gh` tem escopo `workflow`; push e PR #1 ok | PR #1 no ar |