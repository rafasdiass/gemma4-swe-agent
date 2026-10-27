# PROTOCOLO OLIMPO — GEMMA 4 DEVELOPER AGENT COMPETITION
## Planning: `olimp-gemma4-swe-2026-q4`
## Repositório: `gemma4-swe-agent` (privado, GitHub/GitLab)
## Modelo: **Gemma 4 31B** — **ZERO execução local**

---

## ⏱ CRONOGRAMA (5 semanas até 02/Dez/2026)

| Semana | Período | Marco Entregável |
|--------|---------|------------------|
| **S0** | 27-31 Out | **Setup & Infra** — Kaggle L4x4, repo, CI, dataset versioning |
| **S1** | 03-07 Nov | **Baseline & Arch** — agent.yaml 31B, ADK compliance, first LoRA |
| **S2** | 10-14 Nov | **Multi-Agent** — analyzer/coder/verifier, skills, graph reasoning |
| **S3** | 17-21 Nov | **RL/Optimization** — DPO/RLHF, budget tuning, ensemble |
| **S4** | 24-28 Nov | **Stress & Submit** — 12h sandbox sim, paper draft, final zip |
| **S5** | 29 Nov-02 Dez | **Final Submit** — Main + Paper Track (12 Nov) + Small Model (se 4B) |

---

## 🏗 INFRASTRUTURA (ZERO LOCAL)

| Componente | Onde | Spec |
|------------|------|------|
| **Treino LoRA 31B** | Kaggle Notebook L4x4 (96GB) | 15h/sem quota, `accelerate` + `peft` + `trl` |
| **Inferência/Validação** | Kaggle Notebook L4x4 | Mesmo pool, internet OFF no submit |
| **Dataset/Versioning** | DVC + S3/GCS (remote) | `dvc push/pull` no notebook |
| **CI/CD** | GitHub Actions (self-hosted runner opcional) | Lint, typecheck, test harness |
| **Artifacts (LoRA)** | Git LFS / Hugging Face Hub / S3 | `adapter_model.safetensors` versionados |
| **Monitor/Logs** | Weights & Biases / MLflow (remote) | Tracking runs, comparação |
| **Repo Código** | `git@github.com:rafaeldias/gemma4-swe-agent.git` | Privado, branch `main` + `dev` |

---

## 📦 REPOSITÓRIO: `gemma4-swe-agent`

```
gemma4-swe-agent/
├── .github/workflows/
│   ├── ci.yml              # lint, typecheck, unit tests
│   ├── dvc-sync.yml        # dvc push/pull artifacts
│   └── submit-check.yml    # valida submission.zip structure
├── agent.yaml              # ADK root config (Apolo spec)
├── configs/
│   ├── sampling.yaml       # temp=0.2, top_p=0.95, max_tokens=8192
│   └── eval_config.yaml    # per-task time limits
├── prompts/
│   ├── system.md           # System prompt (Atena/Apolo)
│   ├── analyzer.md         # Repo navigation prompt
│   ├── coder.md            # Patch generation prompt
│   └── verifier.md         # Test validation prompt
├── sub_agents/
│   ├── code_analyzer.yaml  # AgentTool: search + graph
│   ├── patch_generator.yaml # AgentTool: edit + verify
│   └── verifier.yaml       # AgentTool: run tests
├── adapters/
│   ├── main_lora/          # LoRA 31B (git-lfs)
│   │   ├── adapter_config.json
│   │   └── adapter_model.safetensors
│   └── tool_lora/          # LoRA tools (git-lfs)
├── skills/
│   ├── repo_navigation/
│   │   ├── SKILL.md
│   │   ├── scripts/navigate.py
│   │   └── resources/patterns.md
│   ├── test_generation/
│   │   ├── SKILL.md
│   │   └── scripts/gen_tests.py
│   └── patch_validation/
│       ├── SKILL.md
│       └── scripts/validate.py
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_lora_training_31b.ipynb
│   ├── 03_agent_assembly.ipynb
│   ├── 04_sandbox_simulation.ipynb
│   └── 05_final_submission.ipynb
├── planning/
│   ├── olimp-gemma4-swe-2026-q4.md      # Este arquivo
│   ├── sprint_0_setup.md
│   ├── sprint_1_baseline.md
│   ├── sprint_2_multiagent.md
│   ├── sprint_3_optimization.md
│   ├── sprint_4_stress.md
│   └── sprint_5_submit.md
├── scripts/
│   ├── setup_kaggle.sh         # Config Kaggle CLI no notebook
│   ├── download_dataset.sh     # Baixa + DVC add
│   ├── train_lora.py           # Treino LoRA (accelerate launch)
│   ├── assemble_agent.py       # Monta submission.zip
│   └── simulate_sandbox.py     # Simula 12h budget localmente
├── tests/
│   ├── test_agent_yaml.py      # Valida ADK schema
│   ├── test_tools.py           # Mock tools sandbox
│   └── test_patches.py         # Aplica patches + roda pytest
├── dvc.yaml                    # Pipeline DVC
├── .dvc/config                 # Remote storage (S3/GCS)
├── requirements.txt            # Python deps
├── requirements-lora.txt       # Treino deps (bitsandbytes, peft, trl)
├── pyproject.toml              # Ruff, mypy, pytest config
└── README.md
```

---

## 🎯 TAREFAS POR SPRINT (Stigmergy-ready)

### **SPRINT 0 — Setup & Infra (27-31 Out)**

| Task ID | Agent | Descrição | Output | Stigmergy Intent |
|---------|-------|-----------|--------|------------------|
| T0.1 | **Atlas** | Criar repo `gemma4-swe-agent`, configurar Git LFS, DVC remote (S3/GCS) | Repo pronto, `dvc remote add` | `intent: repo-bootstrap` |
| T0.2 | **Hera** | Configurar GitHub Actions: CI (ruff, mypy, pytest), DVC sync, submit-check | `.github/workflows/*.yml` | `intent: ci-bootstrap` |
| T0.3 | **Atlas** | Notebook Kaggle: `01_data_exploration` — baixa dataset, explora issues, repos, embeddings | Dataset no DVC, relatório | `intent: dataset-explore` |
| T0.4 | **Apolo** | Definir `agent.yaml` skeleton 31B: modelo, tools, sub-agents, sampling | `agent.yaml` v0.1 | `intent: agent-yaml-skeleton` |
| T0.5 | **Hefesto** | Criar `scripts/simulate_sandbox.py` — mocka tools ADK, valida patch local | Simulador funcional | `intent: sandbox-mock` |
| T0.6 | **Atena** | Decidir estratégia LoRA: full fine-tune vs LoRA (r=64, alpha=128) vs QLoRA 4-bit | ADR em `planning/adr-lora-strategy.md` | `intent: lora-strategy` |

---

### **SPRINT 1 — Baseline & Arch (03-07 Nov)**

| Task ID | Agent | Descrição | Output |
|---------|-------|-----------|--------|
| T1.1 | **Atena/Apolo** | Treino LoRA v1 no Kaggle L4x4: 31B, dataset oficial, 3 epochs, lr=2e-4 | `adapters/main_lora/v1/` |
| T1.2 | **Apolo** | Prompts v1: system.md (role), analyzer.md (graph search), coder.md (patch format) | `prompts/*.md` v1 |
| T1.3 | **Hefesto** | Teste baseline: roda 10 issues no simulador, mede PASS rate | Baseline score |
| T1.4 | **Atlas** | Versiona LoRA v1 no DVC + Git LFS, tag `lora-v1-baseline` | Artifact versionado |
| T1.5 | **Atena** | Análise gaps: quais issues falham? navigation? patch format? test understanding? | Gap report |

---

### **SPRINT 2 — Multi-Agent (10-14 Nov)**

| Task ID | Agent | Descrição | Output |
|---------|-------|-----------|--------|
| T2.1 | **Apolo** | Sub-agents: `code_analyzer.yaml` (search+graph), `patch_generator.yaml` (edit), `verifier.yaml` (test) | `sub_agents/*.yaml` |
| T2.2 | **Iris** | Skills: `repo_navigation` (patterns.md), `test_generation` (pytest templates) | `skills/*/` |
| T2.3 | **Atena** | LoRA v2: multi-task (navigation + coding + verification), r=128 | `adapters/main_lora/v2/` |
| T2.4 | **Hefesto** | Integra sub-agents no simulador, testa fluxo analyzer→coder→verifier | Integration test |
| T2.5 | **Hera** | Ajusta `eval_config.yaml`: time limits por task (navigation=2h, coding=6h, verify=2h) | Budget config |

---

### **SPRINT 3 — RL/Optimization (17-21 Nov)**

| Task ID | Agent | Descrição | Output |
|---------|-------|-----------|--------|
| T3.1 | **Atena** | DPO/RLHF: gera pares (issue, patch_good, patch_bad) via self-play, treina reward model | Reward model + DPO LoRA |
| T3.2 | **Apolo** | Graph reasoning: usa `get_code_subgraph` para multi-file patches, refatoração | Graph-enhanced prompts |
| T3.3 | **Hefesto** | Stress test: 50 issues sequenciais, mede budget consumption, PASS rate | Stress report |
| T3.4 | **Atlas** | Ensemble: combina LoRA v1 + v2 + DPO, seleciona best per issue type | Ensemble strategy |
| T3.5 | **Ayla** | Paper Track draft: arquitetura, LoRA strategy, graph reasoning, resultados | `paper/draft.md` |

---

### **SPRINT 4 — Stress & Submit Prep (24-28 Nov)**

| Task ID | Agent | Descrição | Output |
|---------|-------|-----------|--------|
| T4.1 | **Hefesto** | Simulação 12h completa: roda TODAS issues no sandbox mock, mede PASS% final | Final score estimate |
| T4.2 | **Apolo** | Monta `submission.zip` final: valida schema ADK, todos arquivos presentes | `submission.zip` v1 |
| T4.3 | **Atena** | Paper Track final: submete até 12 Nov (deadline paper) | PDF no Paper Track |
| T4.4 | **Hera** | Checklist submissão: quota L4x4 reservada, notebook pronto, zip testado | Go/No-Go |
| T4.5 | **Iris** | Notebook `05_final_submission.ipynb` pronto pra Submit no Kaggle | Notebook final |

---

### **SPRINT 5 — Final Submit (29 Nov-02 Dez)**

| Task ID | Agent | Descrição | Output |
|---------|-------|-----------|--------|
| T5.1 | **Ayla** | Submit final no Kaggle (Main Competition) | Leaderboard entry |
| T5.2 | **Ayla** | Submit Paper Track (se não fez em S4) | Paper entry |
| T5.3 | **Hera** | Monitora leaderboard, prepara hotfix se necessário | Hotfix plan |
| T5.4 | **Atlas** | Arquiva todos artifacts, tags `submit-final`, documenta lições | Post-mortem |

---

## 🔑 DECISÕES CRÍTICAS (Atena decide, Ayla aprova)

| Decisão | Opções | Recomendação |
|---------|--------|--------------|
| **LoRA Strategy** | Full FT / LoRA r=64 / QLoRA 4-bit / DoRA | **LoRA r=128 + QLoRA 4-bit** (31B em 24GB VRAM efetivo) |
| **Quantization** | QAT W4A16 (oficial) / GPTQ / AWQ | **QAT W4A16 oficial** (já vem quantizado) |
| **Multi-Agent** | Single agent / 2-agent (analyzer+coder) / 3-agent (+verifier) | **3-agent** (separação de concerns, debugável) |
| **Graph Usage** | Só `search_similar_code` / + `get_code_neighbors` / + `get_code_subgraph` | **Todos 3** (embedding + call graph + subgraph) |
| **RL/DPO** | Não / DPO only / PPO / Iterative DPO | **Iterative DPO** (self-play gera dados, 2-3 rodadas) |
| **Ensemble** | Single LoRA / Best-of-N / Router per issue type | **Router per issue type** (bug vs feature vs refactor) |

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Target Mínimo | Target Stretch |
|---------|---------------|----------------|
| **PASS Rate (SWE-bench style)** | 25% | 40%+ |
| **Budget Efficiency** | <10h/12h | <8h/12h |
| **Multi-file Patches** | 30% | 50%+ |
| **First-Patch PASS** | 15% | 25%+ |
| **Paper Track Score** | Top 20% | Top 10% |

---

## 🚀 COMANDOS PARA OUTRA MÁQUINA

```bash
# 1. Clone repo
git clone git@github.com:rafaeldias/gemma4-swe-agent.git
cd gemma4-swe-agent

# 2. Setup DVC (precisa AWS/GCS creds)
dvc pull  # baixa LoRAs, dataset

# 3. Kaggle Notebook (na web)
# - Abre notebooks/02_lora_training_31b.ipynb no Kaggle
# - Seleciona Accelerator: L4x4
# - Roda células → treina LoRA → `dvc push` artifacts

# 4. Local (só orchestration, ZERO modelo)
python scripts/assemble_agent.py  # monta submission.zip
python scripts/simulate_sandbox.py --issues 50  # testa local (mock)

# 5. Submit
# - Anexa submission.zip no notebook 05_final_submission.ipynb
# - Submit no Kaggle
```

---

## 📋 CHECKLIST GO/NO-GO PRÉ-SUBMIT

- [ ] `agent.yaml` passa validação ADK schema
- [ ] Todos sub-agents declarados e testados
- [ ] LoRA final versionado no DVC + Git LFS
- [ ] `submission.zip` < 1GB (limite Kaggle)
- [ ] Simulação 12h roda sem erro no mock
- [ ] Paper Track submetido (se aplicável)
- [ ] Quota L4x4 disponível para submit final
- [ ] Notebook `05_final_submission.ipynb` testado

---

**Planning ID**: `olimp-gemma4-swe-2026-q4`  
**Repo**: `git@github.com:rafaeldias/gemma4-swe-agent.git`  
**Branch base**: `main` → `dev` para PRs  
**Início**: **Imediato (Sprint 0)**  
**Fim**: **02 Dez 2026 23:59 UTC**

---

**Próxima ação**: Disparar agentes do Conselho para Sprint 0.
