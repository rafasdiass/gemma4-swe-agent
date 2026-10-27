# DEFINITION_OF_DONE — olimp-gemma4-swe-2026-q4

## DoD geral (vale para toda task)
1. Código mergeado via PR em `main` (push direto é hardDeny).
2. Evidência de execução em `evidencias/` (recibo: log, artefato ou print mensurável).
3. `npm run`-equivalente do repo verde: `ruff check .` + `mypy scripts/` + `pytest` no CI.
4. Nenhuma credencial no repo (Kaggle/Neon/GH só em secrets/env fora do commit).

## DoD por classe de task
- **PESADO** (treino/eval de modelo): recibo do Kaggle (log da sessão + W&B run) + métrica declarada (resolved rate, loss, tempo/sessão).
- **LEVE** (código/planning/docs): comando de prova executável verde (ex.: `python scripts/validate_submission.py --dry-run`).

## Fechamento do plano inteiro (G-FINAL)
- `submission.zip` submetida e confirmada na plataforma (recibo) **antes de 02/dez 23:59 UTC**, com buffer ≥72h.
- Paper submetido até 12/nov (se não, registrar decisão de abandono com rationale).
- Todas as tasks do [MAPA_DE_CLASSIFICACAO](../MAPA_DE_CLASSIFICACAO.md) FECHADA ou NAO-MEDIDO com motivo datado; zero linha sem dono.