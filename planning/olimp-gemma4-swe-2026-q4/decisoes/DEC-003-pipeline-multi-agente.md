# DEC-003 — Pipeline multi-agente 3 lanes + skills genéricas

**Data:** 2026-10-27 · **Decisora:** Ayla (com Atena) · **Aprovação:** Rafael (root)
**Estado:** ACEITA

- **Arquitetura:** `code_analyzer` (diagnóstico com tools de grafo) → `patch_generator` (patch + testes) → `verifier` (valida, itera, desiste com rationale) → `submit_patch`.
- **Skills:** `repo_navigation`, `test_generation`, `patch_validation` — genéricas por construção: o repo de avaliação é não-visto e **prompt não pode ser ajustado ao dataset de avaliação** (regra da competição).
- Anti-ataque à régua: auditoria da Musa (S2-T-33, S4-T-43) faz `grep` de termos do dataset nos prompts/skills; violação bloqueia submissão (fail-closed).
- Alternativa considerada e descartada: single-shot monolítico (menos resolved rate esperado; fica como **baseline de comparação** no eval A/B/C da S2).