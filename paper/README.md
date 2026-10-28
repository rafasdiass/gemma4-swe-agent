# paper/

Esboço do paper track (T-16, S1). Deadline REAL de submissão: **12/nov/2026**,
meio da Sprint 2 (DEC-004) — figuras/números fecham na S2 (T-26) e a submissão
é a T-27 com gate G-PAPER.

## Estrutura

- `paper.md` — esqueleto completo. A seção de MÉTODO (§3) já está no nível DoD
  da T-16 ("seção completa"); resultados (§4) e toda lacuna restante estão
  marcados `[PREENCHER: ...]` — nada é inventado: só número medido entra, com
  fonte apontada no Apêndice A.
- `figures/` — a criar: Figura 1 (F0) nasce de
  `planning/olimp-gemma4-swe-2026-q4/diagramas/FLUXO_F0.md` (renderizar em
  PNG); F1 (histograma de comprimento dos pares) sai do recebido do T-10.

## O que falta (checklist até 12/nov)

1. `[PREENCHER: T-13]` — resolved rate A/B (baseline vs LoRA v1), tempo,
   desistências — seção 4 inteira.
2. `[PREENCHER: T-11]` — s/step, VRAM pico/GPU, tokens/s, split do
   device_map, pip freeze — seções 3.2 e 3.5.
3. `[PREENCHER: T-12]` — tamanho real do adapter r=16 no 31B (seção 3.4).
4. `[PREENCHER: T-14]` — top-5 padrões de falha (seção 4, "falhas
   dominantes").
5. `[PREENCHER: T-26]` — related work com citações verificadas, conclusão,
   referências finais.
6. `[A MEDIR]` — formato de submissão do paper track (LaTeX/PDF? page limit?
   língua?): esqueleto em Markdown simples, pronto para pandoc -> LaTeX;
   língua em inglês por default de write-up técnico — decisão explícita na S2
   se o track exigir outra.

## Regra dura

Nenhum conteúdo de Competition Data (texto de issue, nome de repo do dataset,
patch) entra neste diretório. Só número agregado medido, sempre com fonte
canônica nomeada. Convenção: quando um `[PREENCHER]` é preenchido, a fonte
(evidencia/DEC que o mediu) entra no mesmo parágrafo.

## Conversão para o formato final

Markdown simples (headers, tabelas, listas) — conversão mecânica direta para
LaTeX/PDF via pandoc na S2, conforme o formato que o track exigir.
