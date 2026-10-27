# SPRINT 5 — Entrega final e buffer de 72h (`T-50..T-54`)

**Status:** 🔵 PLANEJADA
**Janela:** 29 nov–02 dez 2026 · **Gate de saída:** G-FINAL
**Objetivo:** submissão final confirmada com recibo **com folga de 72h**, monitoração do leaderboard, encerramento.
**Ancoragem:** [ROADMAP M5](../ROADMAP.md) · [SPRINT_4](SPRINT_4_SUBMISSAO_PAPER.md)

## Meta do sprint
Submissão final no ar até **29/nov 23:59 UTC** (folga de 72h para o deadline de 02/dez). Zero mudança estrutural depois disso — só hotfix blocker.

## Paralelismo (cap calculado)
| Campo | Valor |
|-------|-------|
| Host | local CPU (LEVE) |
| cap_leve_inicial | 4 (sprint curta de contenção) |
| cap_pesado_inicial | 0 (sem treino novo — freeze) |
| Sprint mista? | não |

**Waves:** W1 = T-50, T-51 (leve) · W2 = T-52 · W3 = T-53, T-54.
**Regra de freeze:** depois da submissão final, nenhuma task reabre o zip salvo incidente blocker nomeado.

## Tasks

### T-50 — Freeze do zip e conferência final de integridade
- **Domínio:** QA / entrega
- **Classe:** LEVE
- **Lead:** Hefesto
- **Apoio:** Musa
- **Verificação:** Atena
- **kernel-verificado:** Hefesto (qa <- packages/agents/profiles/hefesto/identity-kernel.md)
- **Contrato de saída:** hash SHA256 do zip final registrado; `validate_submission.py --strict` PASS de novo no artefato congelado.
- **DoD específico:** hash em `evidencias/S5_freeze.md`; zip imutável daqui em diante.
- **Depende de:** S4-T-45
- **Paralelizável com:** T-51

### T-51 — Monitor do leaderboard e janela de re-submissão
- **Domínio:** Infra / observabilidade
- **Classe:** LEVE
- **Lead:** Zeus
- **Apoio:** Hera
- **Verificação:** Hermes
- **kernel-verificado:** Zeus (infra <- packages/agents/profiles/zeus/identity-kernel.md)
- **Contrato de saída:** checagem diária do leaderboard/site da competição; janela de re-submissão mapeada (até 02/dez).
- **DoD específico:** log diário com data; qualquer atualização da plataforma registrada.
- **Depende de:** S4-T-45
- **Paralelizável com:** T-50

### T-52 — Submissão FINAL confirmada (até 29/nov)
- **Domínio:** Entrega / prazo imexível
- **Classe:** LEVE
- **Lead:** Hera
- **Apoio:** Rafael (root, executa/valida)
- **Verificação:** Rafael (root)
- **kernel-verificado:** Hera (fluxo <- packages/agents/profiles/hera/identity-kernel.md)
- **Contrato de saída:** submissão final (ou confirmação da de segurança) no ar com recibo oficial.
- **DoD específico:** recibo em `evidencias/S5_final.md` com timestamp ≤ 29/nov 23:59 UTC.
- **Depende de:** T-50
- **Paralelizável com:** — (crítico)

### T-53 — Encerramento do mapa de tasks (zero NAO-MEDIDO sem motivo)
- **Domínio:** Estado / continuidade
- **Classe:** LEVE
- **Lead:** Gaia
- **Apoio:** Hermes
- **Verificação:** Hera
- **kernel-verificado:** Gaia (conhecimento <- packages/agents/profiles/gaia/identity-kernel.md)
- **Contrato de saída:** [MAPA_DE_CLASSIFICACAO](../MAPA_DE_CLASSIFICACAO.md) com toda task FECHADA ou NAO-MEDIDO com motivo datado; post-mortem curto.
- **DoD específico:** conferência `grep "### T-" sprints/*.md` == linhas do mapa.
- **Depende de:** T-52
- **Paralelizável com:** T-54

### T-54 — Handoff pós-competição (retroativo ABA)
- **Domínio:** Documentação / retroativo
- **Classe:** LEVE
- **Lead:** Hermes
- **Apoio:** Afrodite
- **Verificação:** Ayla (PO)
- **kernel-verificado:** Hermes (auditoria <- packages/agents/profiles/hermes/identity-kernel.md)
- **Contrato de saída:** retro com o que o pipeline de agente SWE ensina para o produto ABA (avaliação funcional, trajetória, verificação); lições no repo.
- **DoD específico:** documento de lições com ≥3 achados aplicáveis.
- **Depende de:** T-52
- **Paralelizável com:** T-53