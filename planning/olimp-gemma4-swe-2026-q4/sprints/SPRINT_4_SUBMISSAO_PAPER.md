# SPRINT 4 — Embalagem da submissão e simulação 12h (`T-40..T-46`)

**Status:** 🔵 PLANEJADA
**Janela:** 24–28 nov 2026 · **Gate de saída:** G-SUBMISSAO
**Objetivo:** `submission.zip` final validada, simulação completa ≤12h, **submissão de segurança** no Kaggle (antes da final), contingência pronta.
**Ancoragem:** [ROADMAP M4](../ROADMAP.md) · [SPRINT_3](SPRINT_3_DPO_OTIMIZACAO.md)

**Critério de entrada:** G-DPO FECHADO (DEC-005/DEC plano B decidida com recibo do stress).

## Meta do sprint
`validate_submission.py` PASS no zip final + simulação 12h completa dentro do budget + submissão de segurança entregue com recibo **até 28/nov**.

## Paralelismo (cap calculado)
| Campo | Valor |
|-------|-------|
| Host | máquina de execução (LEVE dominante) + Kaggle (só inferência da simulação) |
| cap_leve_inicial | 6 |
| cap_pesado_inicial | 1 |
| Sprint mista? | sim |

**Waves:** W1 = T-40, T-41 (leve) · W2 = T-42 (PESADO: simulação com inferência real) · W3 = T-43, T-44 · W4 = T-45 (submissão de segurança) · W5 = T-46.

## Tasks

### T-40 — `assemble_agent.py` gera o `submission.zip` final
- **Domínio:** Implementação / entrega
- **Classe:** LEVE
- **Lead:** Apolo
- **Apoio:** Artemis
- **Verificação:** Hefesto
- **kernel-verificado:** Apolo (backend <- packages/agents/profiles/apolo/identity-kernel.md)
- **Contrato de saída:** zip com `agent.yaml`, `configs/`, `prompts/`, `sub_agents/`, `adapters/lora-v{melhor}/`, `skills/` — só o que a spec pede, nada a mais. **Construído de commit promovido a `main`** (ver [GOVERNANCA_PIPELINE](../GOVERNANCA_PIPELINE.md): main = deploy).
- **DoD específico:** zip abre; soma de arquivos confere com a checklist da competição; adapter escolhido pela DEC da S3.
- **Depende de:** S3-T-36
- **Paralelizável com:** T-41

### T-41 — `validate_submission.py` modo estrito (checklist completa)
- **Domínio:** QA / entrega
- **Classe:** LEVE
- **Lead:** Hefesto
- **Apoio:** Musa
- **Verificação:** Atena
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefesto/identity-kernel.md)
- **Contrato de saída:** validador estrito: estrutura, YAML válido, modelo único, prompts genéricos, adapter carregável, tamanho do zip dentro do limite da plataforma.
- **DoD específico:** `python scripts/validate_submission.py --strict submission.zip` PASS com recibo.
- **Depende de:** T-40
- **Paralelizável com:** —

### T-42 — Simulação completa 12h (relógio real ou extrapolado)
- **Domínio:** Avaliação / integração
- **Classe:** PESADO (inferência)
- **Lead:** Hefesto
- **Apoio:** Zeus
- **Verificação:** Afrodite
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefesto/identity-kernel.md)
- **Contrato de saída:** `evidencias/S4_simulacao.md`: 50 issues com o zip final, budget total medido, resolved rate congelado.
- **DoD específico:** total ≤ 12h com margem ≥10%; nenhuma issue consome >30min.
- **Depende de:** T-41
- **Paralelizável com:** —

### T-43 — Auditoria final de policy (anti-hardcode + 9 tools)
- **Domínio:** Segurança / compliance da competição
- **Classe:** LEVE
- **Lead:** Musa
- **Apoio:** Hermes
- **Verificação:** Rafael (root)
- **kernel-verificado:** Musa (security <- packages/agents/profiles/musa/identity-kernel.md)
- **Contrato de saída:** auditoria do zip final: zero termo do dataset de avaliação em prompt/skill; zero tool fora das 9; modelo único.
- **DoD específico:** recibo em `evidencias/S4_policy.md`; qualquer violação bloqueia a submissão (fail-closed).
- **Depende de:** T-40
- **Paralelizável com:** T-42

### T-44 — README de submissão e runbook de rollback
- **Domínio:** Documentação
- **Classe:** LEVE
- **Lead:** Gaia
- **Apoio:** Hera
- **Verificação:** Hermes
- **kernel-verificado:** Gaia (conhecimento <- packages/agents/profiles/gaia/identity-kernel.md)
- **Contrato de saída:** runbook: como regenerar o zip, voltar para adapter anterior, re-submeter; mapeamento task→evidência fechado.
- **DoD específico:** alguém que não escreveu consegue seguir o runbook sem perguntar nada.
- **Depende de:** T-41
- **Paralelizável com:** T-42

### T-45 — **Submissão de segurança no Kaggle (até 28/nov)**
- **Domínio:** Entrega
- **Classe:** LEVE
- **Lead:** Hera
- **Apoio:** Apolo
- **Verificação:** Rafael (root)
- **kernel-verificado:** Hera (fluxo <- packages/agents/profiles/hera/identity-kernel.md)
- **Contrato de saída:** `submission.zip` enviada na plataforma com recibo (data/hora, versão); garante participação mesmo se algo quebre na S5.
- **DoD específico:** recibo em `evidencias/S4_submission_seguranca.md` com **timestamp + SHA do commit promovido + SHA256 do zip + recibo da plataforma**; entry deadline (25/nov) já coberto por estar joined.
- **Depende de:** T-42, T-43
- **Paralelizável com:** T-46

### T-46 — Contingência: adapter backup no zip e rollback testado
- **Domínio:** Estado / continuidade
- **Classe:** LEVE
- **Lead:** Atlas
- **Apoio:** Hera
- **Verificação:** Hefesto
- **kernel-verificado:** Atlas (dados <- packages/agents/profiles/atlas/identity-kernel.md)
- **Contrato de saída:** adapter v2 (backup) embalado conforme spec permitir; rollback do zip v3→v2 testado e cronometrado.
- **DoD específico:** teste de rollback com recibo; se a spec não permitir segundo adapter, DEC registrando o porquê.
- **Depende de:** T-40
- **Paralelizável com:** T-45