# DEC-001 — Modelo único: gemma-4-31b-it-qat-w4a16-ct

**Data:** 2026-10-27 · **Decisora:** Ayla · **Aprovação:** Rafael (root)
**Estado:** ACEITA

A competição exige UM modelo único (sem mistura). Opções: 31B, 12B, E4B, E2B (it-qat-w4a16-ct).

- **Escolha: 31B** (QAT W4A16, ~24GB VRAM).
- Por quê: maior capacidade de raciocínio para leitura de repo + grafo de código; cabe folgado na L4x4 (96GB); quota Kaggle só aguenta 1 modelo grande de qualquer forma.
- Custo: perde o small model bonus ($10k, só E2B/E4B). Registrar: tentativa paralela E2B **só se** sobrar quota após M3 (ver ROADMAP "decisões pendentes").
- Plano B (se OOM/sessão não fechar): reduzir rank/alpha do LoRA, não o modelo.