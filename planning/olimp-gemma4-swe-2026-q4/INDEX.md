# PLANNING — olimp-gemma4-swe-2026-q4 (índice mestre)

**Data:** 2026-10-27 · **Decisora:** Ayla · **Aprovação:** Rafael (root)
**Objetivo:** Vencer a **Gemma 4 Developer Agent Competition** (Kaggle) com um agente SWE multi-lane sobre `gemma-4-31b-it-qat-w4a16-ct`, **zero execução local**, treino/eval só em Kaggle L4x4.
**Repo:** `rafasdiass/gemma4-swe-agent` (**PÚBLICO desde 2026-10-28** — decisão do root pós-quota Actions: repo público não consome minutos; reversível. REGRA: Competition Data — conteúdo de issue, gold patch, test patch — NUNCA entra no repo, nem em código, nem em evidência, nem em DVC; schema abstrato pode) · **Protocolo original:** [PROTOCOLO_ORIGINAL.md](PROTOCOLO_ORIGINAL.md)

## Contexto e porquê desta planning

**Origem (2026-10-27):** o root pediu pesquisa de hackathons para participar **solo, online, usando os agentes do Panteão** como vantagem. Varredura de calendários ativos (out/nov-dez/2026) comparou: LLM/Prompt Recovery (encerrado), agents/GMGT (grant, encerrado), GenAI (corporate), Healthtech (pré-inscrição, indefinido) e **Gemma 4 Developer Agent Competition**.

**Por que esta:** única ativa com prazo que cabe na janela do root, prêmio real ($110k total: $65k main / $35k paper / $10k small model), **entry gratuita**, e — o decisivo — formato de agente autônomo em sandbox é **exatamente o formato que o Panteão já orquestra** (multi-agente, skills, ADK). A competição não exige treino massivo: aceita prompt engineering sobre o modelo base, com LoRA como teto de vantagem. Ou seja: o custo de entrada é baixo e a vantagem estrutural do nosso ecossistema é alta.

**Restrições do root que moldaram o plano:**
- **Solo:** um participante, apoiado pelo conselho Panteão (Ayla PO; execução via MCP).
- **Zero execução local (DEC-002):** a máquina de quem planeja não roda 31B; treino/eval só em Kaggle L4x4 (grátis, 96GB, quota ~15h/sem efetivas). O orçamento de quota é a restrição mais dura do plano inteiro — por isso cada sprint tem cap de PESADO.
- **Execução em outra máquina (A-05):** a planning foi gerada numa máquina e é **executada em outra**. Por isso a W0/T-08 existe: nada aqui presume ambiente local da máquina de origem.
- **Modelo único 31B (DEC-001):** regra da competição; escolha do root pela capacidade de raciocínio, com custo de perder o small model bonus.
- **Paper track (DEC-004):** $35k por um write-up que o esforço de qualquer jeito produz (métricas do eval são exigência de método) — submeter mesmo parcial até 12/nov.

**O que esta planning NÃO é:** não é um plano de pesquisa em LLM; é um plano de **engenharia de entrega** — chegar ao `submission.zip` válido com a maior resolved rate que a quota Kaggle e o clock permitem, com submissão de segurança cedo (S4) e buffer de 72h no fim (S5).

## Contexto de sessão (o que a máquina de execução precisa saber ao retomar)

**Ambiente Panteão (da sessão de origem, 2026-10-27):**
- Backend local `http://127.0.0.1:8090` (v2.0.5, `/healthz` ok), sessão c7cf5fcf destravada. Panteão root: `/Users/rafaeldias/.olimpo/runtime/panteao`.
- **MCP panteao**: subir SEMPRE por `bash apps/backend/bin/mcp-launch.sh panteao-mcp.ts` (11 tools em 4 corredores, `panteao_invoke_agent`). **Nunca** `node panteao-mcp.ts` direto — quebra `ERR_MODULE_NOT_FOUND` em `stdio-stdout-guard.js` (causa real da sessão: tsx/loader; o launcher resolve node/tsx).
- **Ayla é host-only**: NUNCA `panteao_invoke_agent({agentId:"ayla"})` — a Ayla orquestra, não é orquestrada.
- Argus MCP falha com `ARGUS_HOST_FACTS_ABSENT` (ausente `/Users/rafaeldias/.olimpo/harness-facts/opencode.env`) — bloqueio conhecido, não perder tempo com ele na retomada.

**Credenciais e contas:**
- GitHub: conta pessoal **`rafasdiass`** (não org). **Lição A-03:** o token de `keys.env` NÃO tem escopo `workflow`; o keyring do `gh` TEM. **Nunca embutir token na URL do remote** — remote limpo (`https://github.com/rafasdiass/gemma4-swe-agent.git`), o `osxkeychain` resolve com o token certo. Sem escopo `workflow`, push de `.github/workflows/*` é rejeitado.
- Kaggle: conta **`rafasdias`**, logada por OAuth (`~/.kaggle/credentials.json`, refresh KGRT_…). O `~/.kaggle/kaggle.json` antigo tem token **inválido** — ignorar. CLI v2.2.5 via pipx. Regras da competição já aceitas.
- Neon (`olimpo`): acessível, mas **os pares de treino de lá NÃO servem** (A-02: formato conversa/auditoria ≠ issue→patch SWE-bench). Dados de treino vêm 100% do dataset oficial da competição (T-07).
- Root (Rafael) é trusted principal: gate da Musa é CONSULTIVO pra ele, blocking pros demais agentes.

**Estado de arte na sessão de origem (2026-10-27):**
- Repo criado (id 1436120602, privado), **PR #1 aberto** com estrutura completa + esta planning: estrutura ADK (`agent.yaml`, `sub_agents/`, `skills/3`, `prompts/4`), scripts (`train_lora.py` QLoRA NF4 r=128 α=256, `simulate_sandbox.py`, `validate_submission.py`, `assemble_agent.py`, `prepare_data.py`, `download_dataset.sh`), workflows CI, `dvc.yaml`, requirements, README. Nada em `main` além do init: **`main` só promove via PR** (ver [GOVERNANCA_PIPELINE.md](GOVERNANCA_PIPELINE.md)).
- Dataset (20.4GB): download iniciado e **caído em 2.7GB** (A-01), reiniciado e morto de novo por decisão de mover pra máquina de execução (A-05). Primeiro ato da S0 lá: T-01.

**Governança do repo:** modelo Panteão — `dev` integra, `main` é promoção congelada, suite inteira SÓ na promoção `dev→main` (submit-check), submissão ao Kaggle só de commit promovido: ver [GOVERNANCA_PIPELINE.md](GOVERNANCA_PIPELINE.md) (régua de CI/CD e "deploy").

## Contratos externos (fonte: página oficial da competição)

- **Modelo ÚNICO obrigatório** (sem mistura): `gemma-4-31b-it-qat-w4a16-ct` (DEC-001).
- **Deliverable:** `submission.zip` = `agent.yaml` (ADK) + `configs/sampling.yaml` + `prompts/*.md` + `sub_agents/*.yaml` + `adapters/*.safetensors` (LoRA) + `skills/`.
- **Sandbox de avaliação:** sem internet, **budget 12h**, 9 tools (`run_command`, `read_file`, `edit_file`, `write_file`, `submit_patch`, `get_code_neighbors`, `search_similar_code`, `get_code_subgraph`, `get_status`).
- **Dataset:** interno estilo SWE-bench, repo não visto, issue → patch válido.
- **Prêmios:** $65k main / $35k paper track / $10k small model (E2B/E4B).
- **Prazos:** Paper Track **12/nov/2026** · Entry **25/nov/2026** · Final **02/dez/2026**.

## Artefatos (PLANNING_FORMAT canônico)

- [ROADMAP.md](ROADMAP.md) · [DESIGN.md](DESIGN.md) · [GOVERNANCA_PIPELINE.md](GOVERNANCA_PIPELINE.md) (main/dev, PRs, suite inteira só na promoção dev→main, regras de deploy/submissão)
- requirements: [REQUIREMENTS](requirements/REQUIREMENTS.md) · [PRODUCT_BACKLOG](requirements/PRODUCT_BACKLOG.md) · [DEFINITION_OF_DONE](requirements/DEFINITION_OF_DONE.md)
- sprints: [S0](sprints/SPRINT_0_BOOTSTRAP.md) · [S1](sprints/SPRINT_1_LORA_BASELINE.md) · [S2](sprints/SPRINT_2_AGENT_PIPELINE.md) · [S3](sprints/SPRINT_3_DPO_OTIMIZACAO.md) · [S4](sprints/SPRINT_4_SUBMISSAO_PAPER.md) · [S5](sprints/SPRINT_5_ENTREGA_FINAL.md)
- decisoes: [DEC-001 modelo 31B](decisoes/DEC-001-modelo-31b.md) · [DEC-002 zero-local](decisoes/DEC-002-zero-local.md) · [DEC-003 pipeline multi-agente](decisoes/DEC-003-pipeline-multi-agente.md) · [DEC-004 paper track](decisoes/DEC-004-paper-track.md)
- monitoring: [SPRINT_HEALTH](monitoring/SPRINT_HEALTH.md) · [RISK_REGISTER](monitoring/RISK_REGISTER.md) · [REGISTRO_DE_ACHADOS](monitoring/REGISTRO_DE_ACHADOS.md)
- mapa das tasks: [MAPA_DE_CLASSIFICACAO.md](MAPA_DE_CLASSIFICACAO.md) — uma linha por task (classe, prova, data)
- saída: [evidencias/](evidencias/) · [diagramas/](diagramas/) (fluxograma F0 obrigatório)

## Sprints (resumo)

| Sprint | Janela | Tema | Gate de saída |
|---|---|---|---|
| 0 | 27–31 out | Bootstrap da **máquina de execução** (T-08/W0): clone, gh (workflow), kaggle, Panteão, DVC; dataset, agent.yaml v0.1 | **G-BOOTSTRAP**: dataset extraído + harness mock PASS + CI verde |
| 1 | 03–07 nov | LoRA v1 baseline + dados SFT + esboço do paper | **G-BASELINE**: LoRA v1 ≥ baseline no harness mock (10 issues) |
| 2 | 10–14 nov | Pipeline 3-agente + skills + **paper submetido (12/nov)** | **G-PIPELINE**: pipeline E2E ≥ baseline; **paper no ar** |
| 3 | 17–21 nov | DPO + sampling + stress 50 issues | **G-DPO**: resolved rate > LoRA v2 no stress |
| 4 | 24–28 nov | submission.zip + simulação 12h + dry-run | **G-SUBMISSAO**: validate_submission PASS + simulação 12h dentro do budget |
| 5 | 29 nov–02 dez | Entrega final + contingência | **G-FINAL**: submissão no Kaggle confirmada com recibo |

## Status
🟡 Em execução — S0 fechando. **T-08: 7/8** (recibo). **T-01: PASSA. T-02: FECHADA** (PR #3). **T-09: FECHADA** (PR #4). **T-04: FECHADA** (PR #5; A-13). **T-07: FECHADA** (PR #6; verificação Afrodite FECHA COM RESSALVA → probe por arquivo LIMPO 0/128; A-15). **T-05: FECHADA** (L4x4 provada: 4× NVIDIA L4 ≈92GB, quota 00:01/30h → ~15h/semana; Persona concluída pelo root). **T-06: FECHADA** (DEC-005 ACEITA: base gemma-4-31b QAT confirmado pelo root — GATE-ROOT-01/A-16; LoRA r=16/alpha=32 direto no QAT sem bitsandbytes; gatilhos G1..G7). Pendências: branch protection em main (root), cap sob carga (W1), limite do modelo gratuito no host (A-11), `.dvc/config` modificado fora do fluxo (root decide). Small Model Prize ($10k, E2B/E4B) registrado como decisão futura. PRs entram por review; main só por PR.