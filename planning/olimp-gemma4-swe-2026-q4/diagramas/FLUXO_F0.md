# FLUXO F0 — ciclo de resolução do agente no sandbox

```
                 ┌──────────────────────────────────────────────┐
                 │ issue (repo não-visto, sem internet, 12h)    │
                 └──────────────────┬───────────────────────────┘
                                    ▼
        ┌───────────────┐   get_code_neighbors / search_similar /
        │ code_analyzer │──▶get_code_subgraph/read_file (skill:
        └───────┬───────┘   repo_navigation) ⇒ diagnóstico
                │           (arquivo/função alvo, hipótese)
                ▼
        ┌────────────────┐  edit_file/write_file (skill:
        │ patch_generator│─▶test_generation) ⇒ patch + testes
        └───────┬────────┘
                ▼
        ┌──────────┐ run_command (skill: patch_validation)
        │ verifier │──FAIL──▶ volta ao generator (≤N iterações,
        └────┬─────┘           budget/issue ~10min, desiste com
             │ PASS            rationale)                    │
             ▼                                                 ▼
        submit_patch ──────────────────────▶ próxima issue (ordem
                                              por orçamento, configs/
                                              sampling.yaml)
```

**Invariante de budget:** soma(issues) ≤ 12h ⇒ ~14min/issue teto; desistência registrada (`get_status`).

**Regra anti-hardcode (DEC-003):** prompts/skills genéricos; zero termo do dataset de avaliação; auditoria fail-closed da Musa antes de qualquer submissão.