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
| A-06 | 2026-10-28 | CI VERMELHO em main/dev — **FECHADO em duas frentes**: (1) quota: repo tornado PÚBLICO (Actions de repo público = minutos ilimitados, $0; rerun provou execução real); (2) código: PR #3 (`fix/ci-green`) merged em dev — tests/test_smoke.py novo (7 testes), mypy escopado em scripts/, ruff --fix (159) + format (inclui blocos de código em SKILL.md — ruff novo formata markdown), validate_submission.py ganha --dry-run (+IncludeLoader pro !include), submit-check.yml virou gate de promoção dev→main, dvc-sync.yml DELETADO (A-08). CI SUCCESS em dev pós-merge (run 40702025010). Restante: branch protection em main (root, UI) | CI verde; gate de promoção correto | fechado 2026-10-28 (T-02) |
| A-07 | 2026-10-28 | Credencial Kaggle AUSENTE na máquina de execução — **FECHADO**: OAuth PKCE completado no browser do root (`rafasdias`, KGRT em `%USERPROFILE%\.kaggle\credentials.json`); `kaggle competitions list` prova auth | — | fechado 2026-10-28 |
| A-08 | 2026-10-28 | `.dvc/config` apontava para bucket placeholder s3 — **FECHADO por REDESENHO**: regras do evento proíbem redistribuir Competition Data a quem não aceitou as regras, e o treino roda no Kaggle com dataset anexado → remote DVC LOCAL (`D:\dvcstore\gemma4-swe-agent`), zero cloud; `dvc-sync.yml` vira no-op na T-02 | governança T-02 ajustada ao desenho | T-02 (S0) |
| A-09 | 2026-10-28 | Paper track (`gemma-4-developer-agent-paper`, $35k, prazo 12/nov) mostra `userHasEntered: False` na conta `rafasdias` — **FECHADO**: root aceitou as regras do paper track em 2026-10-28 | — | fechado 2026-10-28 |
| A-10 | 2026-10-28 | Download do dataset quase lota o D: (53.8GB livres; pico zip+extração ~42GB). Decisão do root: o PESO fica no Kaggle (notebook anexa o dataset, 96GB lá) — cópia local só pra inspeção/dev. Download redirecionado pra `C:\gemma4-data` (97.7GB livres) com wrapper resiliente (loop 40 tentativas, resume automático — o CLI cai ~1×/GB, padrão A-01); extração LOCAL só do necessário pro schema (T-01 ajustada) | disco local preservado; T-01/T-04 seguem com extração seletiva | T-01, T-04 (S0) |
| A-11 | 2026-10-28 | Subagente apolo morreu com `Free usage limit reached` (modelo gratuito do host) — tasks de LLM seguem SERIALIZADAS na anfitria até o limite resetar; quando houver subagente, 1 por vez (lei do root) | throughput de orquestração reduzido; nada bloqueado | contínuo |
| A-12 | 2026-10-28 | **T03_SCHEMA_CONFIRMATION_PENDING fechou como DIVERGÊNCIA REAL**: o schema canônico (HARNESS_README + sample_submission) usa `name`/`instruction`/`generate_content_config`/`max_output_tokens`/`adapter` por agente/`sub_agents` como lista — nosso `agent.yaml` v0.1 usa `agent_id`/`system_prompt`/`sampling`/`max_tokens`/`adapters` dict/`sub_agents` dict → **NÃO submissível**. E o budget é POR TASK (60 min, 100 tool calls, 500 turns), não 12h globais — o eval_config de 2h/6h/2h está morto. Alavancas descobertas: `thinking_config` (reasoning do Gemma 4), submit_patch não conta no budget, fallback automático de diff, arquivos de teste protegidos são arrancados do patch — **FECHADO pela T-09 (PR #4 merged, CI SUCCESS em dev)**: configs migrados, validador realinhado, 11 testes, zip montado+validado ponta a ponta; riscos T09_R1 (stop_sequences bomba em edit_file), T09_R2 (submit_patch em sub-agente), T09_R3 (!include resolvido), T09_R4 (campo fora do schema) resolvidos; T09_R6/R7 medem no T-04 | submissão conforme ao schema; orquestração redesenhada na S1 com budget real | fechado 2026-10-28 (T-09) |

## Fechados

| ID | Data | Fechamento | Evidência |
|---|---|---|---|
| A-03 | 2026-10-27 | Remote limpo (token fora da URL): keyring do `gh` tem escopo `workflow`; push e PR #1 ok | PR #1 no ar |