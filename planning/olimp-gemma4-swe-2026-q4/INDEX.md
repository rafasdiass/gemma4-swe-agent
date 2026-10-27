# PLANNING — olimp-gemma4-swe-2026-q4 (índice mestre)

**Data:** 2026-10-27 · **Decisora:** Ayla · **Aprovação:** Rafael (root)
**Objetivo:** Vencer a **Gemma 4 Developer Agent Competition** (Kaggle) com um agente SWE multi-lane sobre `gemma-4-31b-it-qat-w4a16-ct`, **zero execução local**, treino/eval só em Kaggle L4x4.
**Repo:** `rafasdiass/gemma4-swe-agent` (privado) · **Protocolo original:** [PROTOCOLO_ORIGINAL.md](PROTOCOLO_ORIGINAL.md)

## Contratos externos (fonte: página oficial da competição)

- **Modelo ÚNICO obrigatório** (sem mistura): `gemma-4-31b-it-qat-w4a16-ct` (DEC-001).
- **Deliverable:** `submission.zip` = `agent.yaml` (ADK) + `configs/sampling.yaml` + `prompts/*.md` + `sub_agents/*.yaml` + `adapters/*.safetensors` (LoRA) + `skills/`.
- **Sandbox de avaliação:** sem internet, **budget 12h**, 9 tools (`run_command`, `read_file`, `edit_file`, `write_file`, `submit_patch`, `get_code_neighbors`, `search_similar_code`, `get_code_subgraph`, `get_status`).
- **Dataset:** interno estilo SWE-bench, repo não visto, issue → patch válido.
- **Prêmios:** $65k main / $35k paper track / $10k small model (E2B/E4B).
- **Prazos:** Paper Track **12/nov/2026** · Entry **25/nov/2026** · Final **02/dez/2026**.

## Artefatos (PLANNING_FORMAT canônico)

- [ROADMAP.md](ROADMAP.md) · [DESIGN.md](DESIGN.md)
- requirements: [REQUIREMENTS](requirements/REQUIREMENTS.md) · [PRODUCT_BACKLOG](requirements/PRODUCT_BACKLOG.md) · [DEFINITION_OF_DONE](requirements/DEFINITION_OF_DONE.md)
- sprints: [S0](sprints/SPRINT_0_BOOTSTRAP.md) · [S1](sprints/SPRINT_1_LORA_BASELINE.md) · [S2](sprints/SPRINT_2_AGENT_PIPELINE.md) · [S3](sprints/SPRINT_3_DPO_OTIMIZACAO.md) · [S4](sprints/SPRINT_4_SUBMISSAO_PAPER.md) · [S5](sprints/SPRINT_5_ENTREGA_FINAL.md)
- decisoes: [DEC-001 modelo 31B](decisoes/DEC-001-modelo-31b.md) · [DEC-002 zero-local](decisoes/DEC-002-zero-local.md) · [DEC-003 pipeline multi-agente](decisoes/DEC-003-pipeline-multi-agente.md) · [DEC-004 paper track](decisoes/DEC-004-paper-track.md)
- monitoring: [SPRINT_HEALTH](monitoring/SPRINT_HEALTH.md) · [RISK_REGISTER](monitoring/RISK_REGISTER.md) · [REGISTRO_DE_ACHADOS](monitoring/REGISTRO_DE_ACHADOS.md)
- mapa das tasks: [MAPA_DE_CLASSIFICACAO.md](MAPA_DE_CLASSIFICACAO.md) — uma linha por task (classe, prova, data)
- saída: [evidencias/](evidencias/) · [diagramas/](diagramas/) (fluxograma F0 obrigatório)

## Sprints (resumo)

| Sprint | Janela | Tema | Gate de saída |
|---|---|---|---|
| 0 | 27–31 out | Bootstrap: repo, CI, Kaggle, dataset, agent.yaml v0.1 | **G-BOOTSTRAP**: dataset extraído + harness mock PASS + CI verde |
| 1 | 03–07 nov | LoRA v1 baseline + dados SFT + esboço do paper | **G-BASELINE**: LoRA v1 ≥ baseline no harness mock (10 issues) |
| 2 | 10–14 nov | Pipeline 3-agente + skills + **paper submetido (12/nov)** | **G-PIPELINE**: pipeline E2E ≥ baseline; **paper no ar** |
| 3 | 17–21 nov | DPO + sampling + stress 50 issues | **G-DPO**: resolved rate > LoRA v2 no stress |
| 4 | 24–28 nov | submission.zip + simulação 12h + dry-run | **G-SUBMISSAO**: validate_submission PASS + simulação 12h dentro do budget |
| 5 | 29 nov–02 dez | Entrega final + contingência | **G-FINAL**: submissão no Kaggle confirmada com recibo |

## Status
🟡 Em execução — S0 aberta. PR #1 (estrutura do repo) aberto. Dataset (20.4GB) em download (reiniciado 2026-10-27, PID 91921). MCP panteao no ar (11 tools). PRs entram por review; main só por PR.