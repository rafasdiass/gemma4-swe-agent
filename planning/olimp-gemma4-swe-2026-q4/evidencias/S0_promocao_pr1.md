# Evidência — Promoção do PR #1 a `main` (override do root, suite não executada)

**Data:** 2026-10-27T19:49:37Z · **Quem:** Rafael (root), com Ayla registrando
**O que:** PR #1 (`feat/complete-competition-setup`, 5 commits: estrutura ADK completa + planning canônica `olimp-gemma4-swe-2026-q4`) **promovido a `main` por squash**.
**Recibo:** squash `bd9ac301db861c5d46cadd67e0512d716dc79b7e` · state MERGED · `mergedAt` 2026-10-27T19:49:37Z (`gh pr view 1 --json state,mergedAt,mergeCommit`).

## Override do root (trusted principal)
A regra da [GOVERNANCA_PIPELINE.md](../GOVERNANCA_PIPELINE.md) manda a **suite inteira** rodar em toda promoção `dev→main` (`submit-check.yml`). O root decidiu promover **sem** a suite: "já promove essa pr para main, mas sem necessidade de rodar a suite, já que não foi nada de mais".

## Parecer da Ayla (registrado uma vez, informativo)
Promoção sem o gate abre precedente de "é nada de mais" — quem promove sem suite uma vez acha fácil promover sempre. Neste caso específico o risco real é baixo: o PR é docs + estrutura + scripts **que não rodam no sandbox de avaliação**, nenhum dado real de performance em jogo. Mas o `submit-check.yml` existir e não ter rodado nem uma vez na história da `main` é dívida: **a primeira promoção que carregar adapter/zip de submissão roda a suite, sem override barato**.

## Estado resultante
- `main`: `bd9ac30` (squash do PR #1) — **promoção 1**
- `dev`: criada a partir de `main` (`bd9ac30`), por API (ref inexistente), não por push direto — hook musa do clone local bloqueia push de `main`/`dev`, correto por design
- Branch `feat/complete-competition-setup`: deletada pós-merge
- **Dívida registrada:** suite de promoção nunca executada (nada de `submit-check.yml` rodado na promoção 1). Primeira promoção com artefato de submissão roda obrigatória.