# DEC-006 — Fonte de dado do treino: Neon NÃO entra no V1; método transferido; reasoning-adapter é exploração limitada no S3

**Status:** ACEITA (2026-10-29)
**Proveniência:** questionamento do root ("os pares são só chat? o que vai ser aproveitado pra competição?") → auditoria empírica do banco olímpico.

## Contexto

O root perguntou por que os pares curados no Neon (curados pensando num modelo próprio) não alimentam o treino do agente SWE. Auditoria feita com acesso live ao banco (conexão via `OLIMPO_NEON_DATABASE_URL_DIRECT`, sem log de credencial).

## Evidência (probes no Neon, 2026-10-29)

| Tabela | Linhas | Composição |
|---|---|---|
| `public.training_pairs` | 85.662 | pares prompt→response das sessões reais; **p50=46 chars, p75=157, p99=4.7k** — maioria é ack de orquestração ("Estado salvo no Neon 💙"); `response_provenance`: 80% `human_corpus`, 20% `generated`; `target_agent_adapter` por agente (ayla 65.714, hefesto 1.243, hermes 969, apolo 727…) |
| `public.gold_curation_pairs` | 12.548 | **todos** `track=knowledge`, `included=true`, quality 8–10 — curagem de knowledge/vault, não de SFT; duplicatas por `text_sha256` distintas (dedup de gestão, não de patch) |
| `curation_triage_stage1` / `final_stage2` / `gold_incomplete` | 167.950 / 39.674 / 3.372 | esteira de curagem |

No subconjunto LOGRO (>3k chars, alguns milhares de pares — onde está o "pensamento"): 88% prose estruturada (**negrito**), 58% headers `##`, 33% listas numeradas, 29% código em blocos, 19% tabelas — mas **0% unified diff / gold patch em toda a base**. Os longos são SPEC TÉCNICA, PRE_FLIGHT SCAN, raio-x de war room: **raciocínio real de gestão de projeto, em PT-BR, sobre os produtos do Olimpo**.

## Decisão

1. **V1/V2 (S1–S2): treino usa exclusivamente os pares da competição** (`C:\gemma4-data\sft_pairs\pairs.jsonl`, 128 pares, `prepare_data.py` + `--check-leak`). Os pares do Neon NÃO entram — domínio desigual (PT-BR conversa vs. diff de Python em inglês), risco real de **diluir/rebaixar** o resolved rate, e quebra a tese do paper ("dado honesto do domínio").
2. **Pares do Neon NÃO sobem pra Kaggle**: conteúdo operacional/pessoal do root (amostra contém referência a `.env.local` e decisões de infra). LGPD + hygiene: zero upload.
3. **MÉTODO da curagem já transferido**: a esteira triage→gold→dedup→score do Neon inspirou o research de pipeline idêntico no `prepare_data.py` (probe de leak por arquivo calibrada no A-15; flag `--check-leak` do PR #10). Registro é este ADR.
4. **Reasoning-distill é EXPLORAÇÃO LIMITADA no S3 (T-37, opcional, gate Duplo):** a DEC-005 permite até 8 adapters por submissão. Um adapter auxiliar (`planner_lora`) destilado do subconjunto longo (raciocínio de planejamento/war-room) só entra se: **(a)** as Rules permitirem explicitamente dado de treino externo à competição; **(b)** a eval A/B de S2 mostrar que o adapter não rebaixa o resolved rate do coder. Fail-closed: sem (a), T-37 não roda.
5. **Distinção de produto:** o corpus Neon treina a Ayla (produto existente). O corpus da competição treina o agente SWE (produto desta competição). Não são concorrentes de fonte; são unidades diferentes.

## Consequências

- S1 segue com os 128 pares (SES-1 semi-fechado: modelo montou, peft bloqueou no tipo do módulo — ver A-17).
- Nenhum dado do olimpo/panteão atravessa a borda do paper/dataset da competição.
- T-37 nova no SPRINT_3, marcada opcional/condicionada.
