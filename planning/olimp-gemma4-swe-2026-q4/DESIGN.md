# DESIGN — olimp-gemma4-swe-2026-q4

## Arquitetura do agente (entregável da competição)

```
submission.zip
├── agent.yaml                 # raiz ADK: modelo ÚNICO gemma-4-31b-it-qat-w4a16-ct + sampling
├── configs/sampling.yaml      # temperature, top_p, max_tokens, budget 12h
├── prompts/                   # system, analyzer, coder, verifier (genéricos, sem hardcode do dataset)
├── sub_agents/                # code_analyzer → patch_generator → verifier
├── adapters/                  # LoRA safetensors (QLoRA 4-bit NF4, r=128, alpha=256)
└── skills/                    # repo_navigation, test_generation, patch_validation
```

### Pipeline de resolução (runtime no sandbox)

1. **code_analyzer**: lê a issue, navega o repo (`get_code_neighbors`, `search_similar_code`, `get_code_subgraph`), produz diagnóstico com arquivo/função alvo.
2. **patch_generator**: gera patch mínimo + testes (`test_generation`).
3. **verifier**: roda testes (`patch_validation`), itera até PASS ou desistir com rationale; `submit_patch`.

### Decisões técnicas

- **DEC-001:** modelo único 31B (QAT W4A16, ~24GB VRAM) — cabe em L4x4 (96GB).
- **DEC-002:** zero execução local: treino/eval só no Kaggle; local só orquestração/planning (Panteão em CPU).
- **DEC-003:** multi-agente 3 lanes + skills genéricas; prompts sem hardcode do dataset (regra da competição: prompt não pode ser "fine-tuned" no dataset de avaliação).
- **DEC-004:** paper track submetido em 12/nov mesmo que parcial (bônus $35k, custo marginal).
- **Treino:** QLoRA 4-bit NF4 (peft), r=128, alpha=256, SFT em pares issue→patch; DPO na Sprint 3 (trl).
- **Dados SWE-bench:** os pares gold do Neon (`gold_curation_pairs`, `training_pairs`) NÃO servem (formato auditoria/conversa, não issue→patch). Fonte: dataset oficial da competição + síntese a partir de repos públicos.
- **Anti-dedo-duro:** scratches (AGENTS.md, grafo de código) permitidos no sandbox, mas o repo de avaliação é não-visto: skills têm que ser genéricas.

## Infra

- Kaggle Notebook L4x4 (quota 2x = ~15h/sem): `notebooks/01_data_exploration`, `02_train_lora_v1`, `03_train_dpo`.
- DVC + remote S3/GCS para adapters (Git LFS para safetensors no repo).
- W&B tracking de treino/eval.
- CI local + GitHub Actions (mirror); main só entra por PR (regra musa: hardDeny push direto).

## Riscos técnicos conhecidos

1. 12h de budget para ~50 issues ⇒ ~14min/issue alvo (com margem, ~10min).
2. Sem internet no sandbox: nenhuma dependência pode ser baixada em runtime.
3. Modelo único: não há fallback de tamanho na submissão (mudar de modelo = nova submissão).