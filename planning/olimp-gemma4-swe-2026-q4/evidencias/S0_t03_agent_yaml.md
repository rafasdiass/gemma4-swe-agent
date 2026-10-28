# S0 — T-03: agent.yaml v0.1 validado contra o formato ADK (recibo)

**Data:** 2026-10-28 · **Executor:** Ayla (host; o subagente apolo morreu no limite do modelo gratuito — `Free usage limit reached` — e a task foi absorvida pela anfitria, sem violar a serialização: 1 task de LLM por vez)
**Método:** leitura integral dos artefatos + parse mecânico (PyYAML 3.12 via uv, regex de referências de modelo) — prova de comando real abaixo.

## DoD da T-03 — status

| # | Verificação | Status | Prova |
|---|---|---|---|
| 1 | YAML parse de TODOS os configs | ✓ | `PARSE OK` × 6: `agent.yaml`, `sub_agents/{code_analyzer,patch_generator,verifier}.yaml`, `configs/{sampling,eval_config}.yaml` (com `!include` resolvido na leitura) |
| 2 | Campos obrigatórios presentes | ✓ | `agent.yaml`: agent_id, model, description, sampling, system_prompt, tools, sub_agents, skills, eval_config — todos presentes; 3 sub_agents com model/prompt/tools próprios |
| 3 | Modelo ÚNICO 31B em TODO o repo | ✓ | Regex `gemma[-_]4[-_][a-z0-9\-]+` sobre os 6 YAMLs + 3 SKILL.md: **zero** referência fora de `gemma-4-31b-it-qat-w4a16-ct`. `VEREDITO: PASS` |
| 4 | Tools = as 9 do harness | ✓ | agent.yaml lista exatamente as 9 (run_command, read_file, edit_file, write_file, submit_patch, get_code_neighbors, search_similar_code, get_code_subgraph, get_status); sub_agents usam apenas subconjuntos |
| 5 | Skills com SKILL.md + frontmatter | ✓ | 3 skills (repo_navigation, test_generation, patch_validation), cada uma com SKILL.md com frontmatter YAML (name/version/description) e scripts/ |
| 6 | Budget coerente com as 12h | ✓ | eval_config: 2h análise + 6h patch + 2h verificação = 10h + overhead ≤ 12h (total_budget_seconds: 43200) |

## Achados nomeados (não bloqueiam v0.1, exigem confirmação contra o HARNESS_README.md do dataset)

- **T03_SCHEMA_CONFIRMATION_PENDING** — a competição valida contra o **Google ADK Agent Config** real. Os nomes de campo usados (`agent_id`, `system_prompt`) podem divergir do canônico ADK (`name`, `instruction`); e `sub_agents` aqui é DICT nomeado, o ADK costuma esperar LIST. A spec definitiva está no `HARNESS_README.md` DENTRO do dataset (20.4GB, baixando). Revalidação de campo marcada pra quando o zip chegar — o parse e o modelo único não mudam.
- **T03_ADAPTER_ABSENT** — `agent.yaml` referencia `adapters/main_lora/*` e `adapters/tool_lora/*`, mas `adapters/` está VAZIO. Esperado em v0.1 (LoRA nasce na S1); a sample submission da competição traz adapters dummy que o starter notebook remove se não usados. Risco: submeter zip com referência a adapter inexistente — o `validate_submission.py` da casa precisa cobrir isso (anotado pra T-04/S4).

## Veredito

**T-03 PASSA** no DoD declarado (parse + campos + modelo único). Confirmação de schema ADK pendente ao HARNESS_README.md — vira subtarefa de verificação da T-03 quando o dataset estiver em disco.
