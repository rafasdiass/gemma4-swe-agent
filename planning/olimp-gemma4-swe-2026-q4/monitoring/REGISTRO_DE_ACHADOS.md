# REGISTRO_DE_ACHADOS — olimp-gemma4-swe-2026-q4

Todo gap, bug ou surpresa vira achado `A-NN` (com task correspondente ou motivo datado de não ter).

## Abertos

| ID | Data | Achado | Impacto | Task |
|---|---|---|---|---|
| A-01 | 2026-10-27 | Download do dataset caiu em 2.7GB (processo morto); reiniciado com `nohup` (PID 91921) | risco R-03 | monitorar S0/T-01 |
| A-02 | 2026-10-27 | Pares gold do Neon (`gold_curation_pairs`, `training_pairs`) NÃO servem como dados SWE-bench (formato conversa/auditoria ≠ issue→patch) | dados de treino vêm 100% do dataset oficial | T-07 (S0) |
| A-03 | 2026-10-27 | Push direto a `main` é hardDeny (musa); PR obrigatório — PR #1 aberto com workflows, que exigem token com escopo `workflow` (gh keyring tem; keys.env não tem) | fluxo repo só por PR | T-02 (S0) |
| A-04 | 2026-10-27 | Protocolo original colocava o draft do paper na S4; deadline real do paper track é 12/nov (S2) | correção de planejamento | T-16/T-27 |

## Fechados

*(aqui entra o que fechou com evidência)*