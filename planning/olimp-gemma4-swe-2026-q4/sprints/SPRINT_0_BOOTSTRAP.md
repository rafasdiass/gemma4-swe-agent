# SPRINT 0 — Bootstrap da máquina de execução, repo e Kaggle (`T-01..T-08`)

**Status:** 🟡 ABERTA (2026-10-27)
**Janela:** 27–31 out 2026 · **Gate de saída:** G-BOOTSTRAP
**Objetivo:** máquina de execução pronta (esta sprint roda **noutra máquina**, não na que criou o repo), dataset oficial extraído e inspecionado, harness de simulação local PASS em 1 issue, arquitetura validada por ADR.
**Ancoragem:** [ROADMAP M0](../ROADMAP.md) · [INDEX](../INDEX.md) · [REQUIREMENTS R1–R4](../requirements/REQUIREMENTS.md)

**Critério de entrada:** repo existe no GitHub (`rafasdiass/gemma4-swe-agent`) com PR #1 aberto — FECHADO (2026-10-27).

## Meta do sprint
Máquina de execução com Panteão + gh + kaggle autenticados; dataset completo em disco; `simulate_sandbox.py` PASS em 1 issue real; `validate_submission.py --dry-run` PASS. Critério binário: os quatro fecham com recibo em `evidencias/`.

## Paralelismo (cap calculado)
> Agente local = CPU (orquestração panteao); PESADO = sessão Kaggle (quota ~15h/sem, serializa por construção). **Host do cap = a máquina de execução** (a de criação do repo não roda nada: A-05). Recheck pré-onda via `panteao_invoke_agent` (hera).

| Campo | Valor |
|-------|-------|
| Host | **máquina de execução (nova)** — medir cap na W0 |
| cap_leve_inicial | 6 (recheckar na W0) |
| cap_pesado_inicial | 1 (Kaggle) |
| Sprint mista? | sim → PESADO domina (só entra na S1) |

**Waves:** **W0 = T-08 (bootstrap da máquina — tudo depende dele)** · W1 = T-01, T-03, T-04 (leve) · W2 = T-02, T-05 (leve) · W3 = T-06, T-07 (leve).
**Regra de arquivo:** mesmo path em write → serializar sempre.

## Tasks

### T-01 — Dataset oficial baixado, extraído e inspecionado (NA MÁQUINA DE EXECUÇÃO)
- **Domínio:** Infra / dados
- **Classe:** LEVE (download; o consumo de GPU é da S1)
- **Lead:** Atlas
- **Apoio:** Yara
- **Verificação:** Hefesto
- **kernel-verificado:** Atlas (dados <- packages/agents/profiles/atlas/identity-kernel.md)
- **Contrato de saída:** `gemma-4-developer-agent.zip` (20.4GB) em disco **na máquina de execução**, extraído, com `evidencias/S0_dataset.md` documentando schema de 1 issue real (campos, formato do gold patch).
- **Comandos de prova (executar na máquina de execução):**
  ```
  nohup kaggle competitions download -c gemma-4-developer-agent > kaggle-download.log 2>&1 &
  # monitorar: ls -lh gemma-4-developer-agent.zip  (alvo: ≥20GB — o download JÁ CAIU uma vez em 2.7GB: R-03/A-01)
  unzip -t gemma-4-developer-agent.zip && unzip -q gemma-4-developer-agent.zip -d dataset/
  ```
- **Retomada (R-03):** se cair de novo, reiniciar o download (o CLI recomeça); alternativa documentada: notebook Kaggle baixa e exporta por API do dataset.
- **DoD específico:** `ls -lh` do zip ≥ 20GB; `unzip -t` PASS; 1 issue real aberta e lida; schema documentado.
- **Depende de:** T-08
- **Paralelizável com:** T-03, T-04

### T-08 — Bootstrap da máquina de execução (clone, auth, Panteão, DVC)
- **Domínio:** Infra / ambiente
- **Classe:** LEVE
- **Lead:** Zeus
- **Apoio:** Hera
- **Verificação:** Musa
- **kernel-verificado:** Zeus (infra <- packages/agents/profiles/zeus/identity-kernel.md)
- **Contrato de saída:** máquina de execução com: clone do repo (`git clone https://github.com/rafasdiass/gemma4-swe-agent.git`), `gh auth login` **com escopo `workflow`** (sem ele o push de `.github/workflows/*` é rejeitado: A-03), `kaggle auth login` (conta `rafasdias`), Panteão ativado (backend :8090 + `bash apps/backend/bin/mcp-launch.sh panteao-mcp.ts`), DVC remote configurado com creds.
- **DoD específico:** `gh pr checks 1 -R rafasdiass/gemma4-swe-agent` responde; `kaggle competitions list --search gemma-4` responde; MCP panteao com 11 tools no ar; recibo único em `evidencias/S0_bootstrap_maquina.md` (cap da máquina medida aqui: alimenta o cap do paralelismo).
- **Depende de:** —
- **Paralelizável com:** — (W0: tudo depende dela)

### T-02 — CI verde no PR #1 e merge em main
- **Domínio:** Infra / CI / CD
- **Classe:** LEVE
- **Lead:** Zeus
- **Apoio:** Hera
- **Verificação:** Musa
- **kernel-verificado:** Zeus (infra <- packages/agents/profiles/zeus/identity-kernel.md)
- **Contrato de saída:** workflows `ci.yml`, `dvc-sync.yml`, `submit-check.yml` rodando verdes no PR #1; main atualizada por merge.
- **DoD específico:** `gh pr checks 1` all PASS; main contém o merge.
- **Depende de:** T-03, T-08
- **Paralelizável com:** T-05

### T-03 — agent.yaml v0.1 validado contra o formato ADK
- **Domínio:** Implementação / contrato
- **Classe:** LEVE
- **Lead:** Apolo
- **Apoio:** Artemis
- **Verificação:** Atena
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** `agent.yaml` + `sub_agents/*.yaml` + `skills/*` conforme spec da competição (modelo único 31B, 9 tools, sampling).
- **DoD específico:** YAML parse + campos obrigatórios presentes + nenhuma referência a modelo que não seja o 31B.
- **Depende de:** —
- **Paralelizável com:** T-01, T-04

### T-04 — Harness de simulação local (mock das 9 tools)
- **Domínio:** Testes / QA
- **Classe:** LEVE
- **Lead:** Hefesto
- **Apoio:** Apolo
- **Verificação:** Atena
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefesto/identity-kernel.md)
- **Contrato de saída:** `scripts/simulate_sandbox.py` executa o ciclo analyzer→coder→verifier em 1 issue real com as 9 tools em mock, medindo tempo.
- **DoD específico:** `python scripts/simulate_sandbox.py --issue 1` PASS (exit 0) com log em `evidencias/`.
- **Depende de:** T-01
- **Paralelizável com:** T-02

### T-05 — Prova de vida Kaggle L4x4 (quota + GPU)
- **Domínio:** Infra / quota
- **Classe:** LEVE (só verificação de ambiente)
- **Lead:** Zeus
- **Apoio:** Hera
- **Verificação:** Hefesto
- **kernel-verificado:** Zeus (infra <- packages/agents/profiles/zeus/identity-kernel.md)
- **Contrato de saída:** notebook `01_data_exploration` criado no Kaggle, sessão L4x4 com `nvidia-smi` em log, quota da semana medida.
- **DoD específico:** recibo em `evidencias/S0_kaggle.md` com VRAM 96GB confirmada e quota restante.
- **Depende de:** T-08
- **Paralelizável com:** T-02, T-04

### T-06 — ADR da estratégia LoRA (QLoRA 4-bit, r/alpha, sessões)
- **Domínio:** Arquitetura / análise
- **Classe:** LEVE
- **Lead:** Atena
- **Apoio:** Yara
- **Verificação:** Rafael (root, review)
- **kernel-verificado:** Atena (arquitetura <- packages/agents/profiles/atena/identity-kernel.md)
- **Contrato de saída:** [DEC-005 no diretório decisoes](../decisoes/): QLoRA NF4 r=128 alpha=256, plano de sessões ≤6h dentro da quota.
- **DoD específico:** ADR com plano B (offload/redução de rank) explícito.
- **Depende de:** T-05
- **Paralelizável com:** T-07

### T-07 — Estrutura de pares SFT definida (issue→patch)
- **Domínio:** Dados / pipeline
- **Classe:** LEVE
- **Lead:** Yara
- **Apoio:** Atlas
- **Verificação:** Afrodite
- **kernel-verificado:** Yara (analytics <- packages/agents/profiles/yara/identity-kernel.md)
- **Contrato de saída:** `scripts/prepare_data.py` lendo o dataset oficial e emitindo pares SFT em formato chat (issue, repo snapshot, gold patch), com contagem e dedup.
- **DoD específico:** ≥1.000 pares válidos ou justificativa do teto real; zero par com patch vazio.
- **Depende de:** T-01
- **Paralelizável com:** T-06