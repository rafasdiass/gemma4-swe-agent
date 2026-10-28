# DEC-005 — Estratégia LoRA: QLoRA NF4, r=16/alpha=32, dado pequeno, sessões ≤6h

**Data:** 2026-10-28 · **Decisora:** Atena (lead T-06) · **Aprovação:** Rafael (root, review desta ADR)
**Estado:** EM REVISÃO (substitui o RASCUNHO desta mesma decisão; fecha os pontos que o rascunho condicionava ao T-11)

## Base (o que está medido e de onde)

| Fonte | Números usados |
|---|---|
| `evidencias/S0_kaggle.md` (T-05, medido) | 4× NVIDIA L4, **23034 MiB/GPU (≈92 GB reais)**, torch 2.11.0+cu128, CUDA 12.8 runtime; internet OFF; quota 30h/sem a 2× → **~15h efetivas L4x4/sem**; `/kaggle/working` 20 GB |
| `evidencias/S0_t07_pairs.md` (T-07, medido) | **128 pares SFT** (129 tasks, 1 descarte); tokens est. p50/p90/max = **4797/17209/92582**; **2 pares > 32768**; **18 pares > 16384**; probe de leak **LIMPO** (A-15) |
| `evidencias/S0_dataset.md` (T-01, medido) | multi-LoRA no sandbox: adapters por agente no mesmo base; **rank 16 ≈ 110–220 MB/adapter; 3 GiB descompactado no total; `max_lora_rank` 128**; eval: 32768 tokens de contexto, compaction aos 14336; vLLM com `include_thoughts` + `thinking_budget` |
| `monitoring/REGISTRO_DE_ACHADOS.md` A-13/A-14 | A-14: **teto GLOBAL de 12h** de eval coexiste com 60min/100 calls/500 turns por task; A-13: T09_R6 (tool calls bindam, não contexto) e T09_R7 (analyzer é o ponto mais apertado) |
| `decisoes/DEC-001..004` | DEC-001 (modelo 31B, ACEITA), DEC-002 (zero local; caps de quota por sprint), DEC-003 (pipeline 3 lanes; repo de avaliação não-visto), DEC-004 (paper 12/nov) |

**Não medido (marcado no texto):** tempo/passo e VRAM pico de treino (T-11 mede); presença de `peft`/`trl`/`bitsandbytes` na imagem Kaggle; split train/eval oficial do dataset.

---

## 0. Conflito de premissa — T06_C1 (GATE-ROOT-01, resolve ANTES da SES-1)

O despacho da T-06 declara **Gemma 3 4B-it** como modelo-alvo do treino. A DEC-001 (ACEITA, 2026-10-27, ANTES da T-01 documentar o schema) escolheu **gemma-4-31b-it-qat-w4a16-ct** como modelo do eval. As duas leituras não coexistem num adapter: **LoRA treinado num base só serve no MESMO base** — adapter no base errado é inútil no sandbox (risco catastrófico R-T06-1).

Evidência que triangula a favor do despacho (inferência declarada, não medida):

1. O despacho é o canal do root mais recente (2026-10-28) e fala do harness rodando **modelo local** com multi-LoRA.
2. O número do próprio harness — "rank 16 ≈ 110–220 MB/adapter, cabem 8 no limite de 3 GiB" — é compatível com um base de ~4B (adapter r=16 all-linear de um 4B ≈ 30M params × 2–4 B ≈ 60–120 MB; escalando linear, um 31B daria ~5× isso, e 8 adapters estourariam os 3 GiB). A DEC-001 foi decidida antes do schema ser lido.

**Decisão desta ADR:** as escolhas de **rank/alpha/dado/sessões/plano B são válidas para qualquer um dos dois bases** (justificadas abaixo por dado e serving, não por VRAM) e ficam decididas JÁ. A parte dependente do base (seção 1, variantes A/B) apresenta a matemática dos dois e o **GATE-ROOT-01** fecha qual variante vale antes do primeiro treino. Se o root confirmar Gemma 3 4B-it, a DEC-001 precisa de DEC de supersessão para o campo `model:` da submissão (consequência §7).

---

## 1. Config LoRA

### Variante A — base Gemma 3 4B-it (bf16) com QLoRA NF4 (primária, conforme despacho)

| Item | Valor | Rationale |
|---|---|---|
| Quantização | NF4, double quant, compute dtype bf16 | 4B bf16 ≈ 8 GB → NF4 ≈ 2.2–3.5 GB de pesos; sobra VRAM de sobra num L4 de 23034 MiB |
| **rank** | **16** | Ver justificativa numérica abaixo (dado + serving, NÃO VRAM) |
| **alpha** | **32** (2×r, scaling=2) | Padrão de SFT pequeno; rsLoRA (`alpha/√r`) só vale a partir de r≥64 — rejeitada aqui |
| dropout | 0.05 (sobe para 0.1 no gatilho G3) | regularização leve; dado minúsculo é o maior risco, não underfit |
| target_modules | q, k, v, o, gate, up, down (todos os lineares) | patch generation é tarefa de formato+código; cobertura completa por custo desprezível em VRAM |
| otimizador | paged_adamw_8bit | já no script; estado do otimizador em r=16 é ~100–200 MB → checkpoint completo é barato |
| seq len treino | **16384** (truncando só o lado do CONTEXTO, patch intacto) | p90 = 17209; `max_seq_length=4096` do script atual cortaria o gold patch de 18+ pares — mudança obrigatória |

**VRAM estimada (variante A):** pesos NF4 ~3–4 GB + LoRA/otimizador ~0.2 GB (r=16) + ativações com gradient checkpointing a 16k ~2–4 GB ≈ **6–9 GB em UMA L4** → cabe em 1 GPU com folga; as outras 3 ficam livres para probes paralelos (§3). `[A MEDIR NA S1: s/step e pico real]`

**Por que NÃO r=128/alpha=256 (premissa do roadmap REJEITADA):**

1. **Dado:** 128 pares × ~8k tokens médios ≈ **~1M tokens/época**. Com r=128 em todos os lineares de um 4B são ~240M params treináveis — razão params/tokens de treino da ordem de 240:1 por época. Regime clássico de memorização: o adapter decora o formato dos 128 gold patches e generaliza mal para o repo **não-visto** do eval (DEC-003). O teto de dado é estrutural (`S0_t07_pairs.md` ≤129) — não cresce com mais compute.
2. **Serving:** o limite da submissão é **3 GiB descompactado**. Extrapolando linear do número medido do harness (r=16 ≈ 110–220 MB), r=128 ≈ **0.9–1.7 GB/adapter**. A arquitetura DEC-003/T-09 tem até 4 adapters (root + 3 sub-agentes): 4 × r=128 = 3.6–6.8 GB → **estoura o limite**; 4 × r=16 = 0.44–0.88 GB → cabe.
3. **VRAM NÃO é o argumento** — r=128 cabe na L4 (est. 8–11 GB). Honestidade: a rejeição é por dado e serving.

**r=64:** ~120M params, ~440–880 MB/adapter — 2 adapters cabem, 4 não garantem. Fica como probe (SES-2) e upgrade condicionado à falsificação (§6).

### Variante B — base gemma-4-31b QAT W4A16 (se o GATE-ROOT-01 reconfirmar a DEC-001)

- **QLoRA NF4 por cima de QAT W4A16 é dupla quantização — rejeitado.** O checkpoint QAT já é 4-bit nativo: carrega direto e treina LoRA em cima, **eliminando a dependência de bitsandbytes** (muda o risco R-T06-2).
- VRAM: pesos ~16–18 GB + LoRA r=16 (~0.5 GB de estados) + ativações 16k com checkpointing ~4–8 GB ≈ **22–28 GB > 23034 MiB de UMA L4** → `device_map="auto"` em 2–4 GPUs (pipeline); 92 GB totais comportam folgado.
- Rank/alpha/dado/sessões: idênticos à variante A (as justificativas 1–2 acima não dependem do base).

---

## 2. Estratégia de dado (128 pares)

1. **Filtro:** os **2 pares > 32768 tokens são DESCARTADOS** (1.6% do dataset; truncar um exemplo de 92k para 16k destrói o sinal e ensina patch incompleto). 126 pares úteis.
2. **18 pares > 16384:** truncar **somente o contexto (lado esquerdo do user turn)**, gold patch intacto. `[A MEDIR NA S1: quanto de contexto sobra por par]`
3. **Holdout:** 16 pares (12.5%) estratificados por repo para val loss — é o detector de overfit (gatilho G3). 112 pares de treino.
4. **Augmentação (mitigação nº 1 do ceiling_note):** variantes de subconjunto de contexto, **K=2** por par (contexto completo + contexto reduzido), amostradas por época em vez de pré-expandidas. Efetivo ~224 amostras/época. `[A MEDIR NA S1: ganho real de val loss]`
5. **Multi-época:** **5 épocas máx. com early stopping (paciência 2)** na val loss. Com eff. batch 4: ~28 steps/época × 5 = **~140 optimizer steps** — dataset pequeno pede MUITOS passos de atualização, não batch grande: **grad_accum 16→4** (mudança no script).
6. **LR:** **1e-4** (abaixo do 2e-4 do script), cosine → 0, warmup 5%. Dataset pequeno + r=16: LR agressiva acelera memorização.
7. **Loss só no assistant:** `packing=False` e máscara de completion (o `format_training_data` atual empacota texto cru e treina loss no contexto também — mudança obrigatória; o par já vem no formato `messages`).

## 3. Plano de sessões (~15h efetivas/sem; 1h de L4x4 queima 2h de quota)

| Sessão | Sprint | ≤h | Conteúdo |
|---|---|---|---|
| SES-1 | S1 | 3 | **T-11 smoke**: probe de imports offline (`peft`, `trl`, `bitsandbytes`, `transformers`, `datasets` — `pip freeze`); load do base; 20 steps; medir **s/step, VRAM pico, tokens/s**; fecha GATE-ROOT-01 (qual variante) |
| SES-2 | S1 | 6 | **Probe grid em paralelo** (variante A: 1 config por GPU — r=16, r=32, r=64 × 2 épocas; 4ª GPU = r=16 com augmentação). Escolha por val loss |
| SES-3 | S2 | 6 | **Treino final** (config vencedor, 5 épocas, early stop, K=2) → adapter v1 exportado |
| SES-4 | S2 | 3 | Buffer: retreino com correção / adapter de 2º agente / preparo DPO (só se sobrar quota) |

Total ≈ **12–18h** espalhadas em S1+S2 — dentro dos caps da DEC-002 (S1 ≤12h, S2 ≤9h). O treino em si é curto (estimativa ~1.5–3h na variante A; `[A MEDIR]`); as sessões existem para iteração, não para uma maratona única.

**Persistência entre sessões:** `/kaggle/working` tem 20 GB — salvar **somente adapter + trainer state** (~100–200 MB em r=16, cabe o estado completo do otimizador 8-bit), `save_strategy="epoch"`, `save_total_limit=2`; cada `Save & Run All` versiona o output e a sessão seguinte anexa o output anterior como input para `resume_from_checkpoint`. Proibido salvar pesos completos do base.

## 4. Plano B — sequência de degradação com gatilhos medidos

| Gatilho (medido) | Ação |
|---|---|
| **G1** VRAM pico > **20 GiB** (87% de 23034 MiB) | seq 16384→8192 → se persistir: offload de embeddings/otimizador p/ CPU → último recurso: r 16→8 (improvável: r=16 já é pequeno) |
| **G2** s/step > **8 s** (variante A) | seq→8192 + reavaliar augmentação → se > 15 s: 3 épocas em vez de 5 |
| **G3** val loss sobe em 2 avaliações seguidas | dropout 0.05→0.1 e épocas↓ → persiste: r 16→8 |
| **G4** sessão Kaggle morre no meio | resume do checkpoint anexado (G4 barato por design: estado ~200 MB) |
| **G5** `peft`/`trl`/`bitsandbytes` ausentes ou bnb incompatível com cu128 | wheels baixados no host (`pip download`), anexados como Kaggle Dataset, `pip install --no-index --find-links /kaggle/input/gemma4-wheels`; pins de versão compatíveis com torch 2.11. Se bnb cu128 não existir: variante B (QAT nativo, sem bnb) ou `adafactor`/adam 8-bit nativo do torch |
| **G6 (último recurso)** | **submissão SEM adapter** — o schema permite (adapter é opcional por agente); prompt-only baseline garante presença na competição. O treino nunca bloqueia a submissão |

## 5. Integração com o eval (treino ↔ serving)

1. **Regra 1:1:** treina r=16 → serve r=16. `max_lora_rank: 128` do harness é o TETO aceito, não meta. Adapter r=16 carrega direto; **não existe "compressão" de r=128 para r=16 no serving** (SVD truncation degrada e retrinar em r=16 é mais barato e mais honesto).
2. O harness lê `r`/`alpha`/`target_modules` do **`adapter_config.json`** do adapter; o `agent.yaml` só aponta `adapter: <nome>` por agente (schema T-09). O `base_model_name_or_path` do adapter_config DEVE casar com o modelo que o sandbox carrega — checagem obrigatória no `assemble_agent.py`/validador (consequência §7.3).
3. **Orçamento de serving:** até 4 adapters × 110–220 MB (número medido do harness para r=16) = **0.44–0.88 GB ≤ 3 GiB** ✓. Se medido acima: adapters compartilhados (root+patch_generator usam o mesmo; analyzer e verifier próprios) — degradação graciosa, não bloqueio.
4. Multi-LoRA por agente é a especialização natural do pipeline DEC-003 (analyzer mais frio/leve, coder mais pesado) — mas **v1 sai com 1 adapter compartilhado**; especialização por agente só depois de o adapter único provar ganho no eval (não gastar quota em especulação).

## 6. Falsificação

- **r=16 é falsificado se** o probe grid da SES-2 mostrar r=64 com val loss claramente inferior E sem sinal de overfit nas 5 épocas → upgrade para r=64 (serving aguenta 2 adapters; revalidar orçamento de 3 GiB antes de exportar).
- **A variante A é falsificada se** o GATE-ROOT-01 confirmar o 31B QAT → variante B, mesmas decisões de rank/dado.
- **A estratégia de augmentação é falsificada se** K=2 não mover val loss na SES-2 → descartar e ficar no multi-época puro (menos complexidade de pipeline).

## 7. Consequências

1. `scripts/train_lora.py` precisa de rework antes da SES-1: `max_seq_length` 4096→16384; `packing=False` + máscara assistant-only; LR 2e-4→1e-4; `grad_accum` 16→4; épocas 3→5 com early stopping; input no formato `messages` do `pairs.jsonl` (o `format_training_data` atual espera campos que não existem); holdout estratificado; `save_only_model`/adapter-only; remover wandb (offline).
2. T-11 (smoke) herda 3 medições obrigatórias: s/step, VRAM pico, `pip freeze` de deps — alimenta G1/G2/G5.
3. Se o root confirmar Gemma 3 4B-it: **DEC-001 vira superseded** (DEC nova para o campo `model:` da submissão) e `ALLOWED_MODELS` do validador é reavaliado contra o registry real; o `assemble_agent.py` ganha a checagem base↔adapter_config (§5.2).
4. Orçamento de quota: SES-1..4 consomem ≤12h de quota (24h a taxa 2×... não: 12h de sessão × 2 = 24h de quota — **acima dos 15h/sem se comprimidas numa semana**; por isso estão espalhadas em S1+S2 conforme DEC-002, e a SES-4 é a primeira a ser cortada).
5. Nenhum conteúdo de Competition Data nesta ADR — só números agregados (128 pares, percentis, contagens).

## 8. Riscos (catastrófico primeiro)

| # | Risco | Mitigação |
|---|---|---|
| R-T06-1 | **Adapter treinado no base errado** (conflito T06_C1) — inútil no sandbox, quota queimada | GATE-ROOT-01 fecha o base ANTES da SES-1; smoke valida o adapter carregando no sandbox antes do treino final |
| R-T06-2 | **Deps offline ausentes/incompatíveis** (bnb/peft/trl na imagem Kaggle; bnb×cu128) | probe `pip freeze` na SES-1; wheels como dataset com `--no-index`; variante B dispensa bnb |
| R-T06-3 | **Treinar sobre o conjunto de avaliação** (se tasks.jsonl for o eval set e não o train split) — anti-ataque à régua, desclassificação | `[A MEDIR NA S1: confirmar nas regras que o eval usa tasks held-out]`; auditoria Musa pré-submissão (DEC-003) |
| R-T06-4 | **Overfit em 128 pares** → generalização ruim no repo não-visto | r=16, early stop paciência 2, holdout 12.5%, dropout escalável (G3) |
| R-T06-5 | **Quota 2× estourada** | sessões ≤6h, probes paralelos intra-sessão (grátis em tempo), SES-4 como buffer cortável, caps DEC-002 |
| R-T06-6 | `/kaggle/working` 20 GB estoura com checkpoints | adapter-only + trainer state (~200 MB); proibido salvar pesos do base |
| R-T06-7 | Truncamento degrada pares longos (p90 17k, max 92k) | drop dos 2 >32k; truncar só contexto; seq 16384 |
| R-T06-8 | Multi-LoRA × 3 GiB no serving | medir tamanho real do adapter na SES-3; fallback adapters compartilhados |
