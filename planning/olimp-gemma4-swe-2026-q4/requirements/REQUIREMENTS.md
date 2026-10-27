# REQUIREMENTS — olimp-gemma4-swe-2026-q4

Fonte: overview oficial da competição (`kaggle.com/competitions/gemma-4-developer-agent`) + regras aceitas pela conta `rafasdias`.

## R1 — Submissão (obrigatório)
- R1.1: `submission.zip` com `agent.yaml` no formato ADK especificado.
- R1.2: prompts genéricos — **proibido** hardcode do dataset de avaliação (regra: "prompts cannot be fine-tuned on evaluation dataset").
- R1.3: UM modelo Gemma 4 (sem mistura de modelos/tamanhos): `gemma-4-31b-it-qat-w4a16-ct`.
- R1.4: adapters LoRA `.safetensors` sobre o modelo base escolhido.
- R1.5: sub_agents e skills versionadas no zip.

## R2 — Sandbox de avaliação (obrigatório)
- R2.1: sem internet em runtime.
- R2.2: budget **12h** por submissão.
- R2.3: só as 9 tools nativas; nenhum tool call fora da lista.
- R2.4: scratch disk permitido (AGENTS.md, grafos pré-computados) — mas repo de avaliação é não-visto ⇒ skills genéricas.

## R3 — Métrica
- R3.1: resolved rate (issues → patch válido aplicável e testes passando) é a métrica primária.
- R3.2: paper track avalia qualidade técnica do write-up (deadline 12/nov).

## R4 — Infra (decisão interna)
- R4.1: zero execução local do modelo (DEC-002).
- R4.2: treino/eval em Kaggle L4x4, quota ~15h/sem efetivas.
- R4.3: main só entra por PR; push direto é hardDeny (musa).

## R5 — Prazos (imexível)
- R5.1: entry deadline 25/nov/2026 (join até essa data; já feito).
- R5.2: paper track 12/nov/2026.
- R5.3: submissão final 02/dez/2026 23:59 UTC.