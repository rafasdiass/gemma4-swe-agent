# DEC-005 — Estratégia LoRA: LoRA direto no 31B QAT W4A16, r=16/alpha=32, sessões ≤6h

**Data:** 2026-10-28 · **Decisora:** Atena (lead T-06) · **Aprovação:** Rafael (root)
**Estado:** ACEITA (condicionada à verificação dos números de treino na SES-1; gatilhos G1–G6 permanecem como mecanismo de falsificação)

## Base (o que está medido e de onde)

| Fonte | Números usados |
|---|---|
| `evidencias/S0_kaggle.md` (T-05, medido) | 4× NVIDIA L4, **23034 MiB/GPU (≈92 GB reais)**, torch 2.11.0+cu128, CUDA 12.8 runtime; internet OFF; quota 30h/sem a 2× → **~15h efetivas L4x4/sem**; `/kaggle/working` 20 GB |
| `evidencias/S0_t07_pairs.md` (T-07, medido) | **128 pares SFT** (129 tasks, 1 descarte); tokens est. p50/p90/max = **4797/17209/92582**; **2 pares > 32768**; **18 pares > 16384**; probe de leak **LIMPO** (A-15) |
| `evidencias/S0_dataset.md` (T-01, medido) | multi-LoRA no sandbox: adapters por agente no MESMO base; **rank 16 ≈ 110–220 MB/adapter; 3 GiB descompactado é o limite DOS ADAPTERS da submissão** (o base em si é servido pela infra do Kaggle); `max_lora_rank` 128; eval: 32768 tokens de contexto, compaction aos 14336; vLLM com `include_thoughts` + `thinking_budget` |
| `monitoring/REGISTRO_DE_ACHADOS.md` | A-14: teto GLOBAL de 12h de eval coexiste com 60min/100 calls/500 turns por task; A-16 (registrar): despacho "Gemma 3 4B-it" era erro — permitidos verificados na página oficial 2026-10-28: `gemma-4-{31b,12b,e4b,e2b}-it-qat-w4a16-ct` |
| `decisoes/DEC-001..004` | **DEC-001 CONFIRMADA pelo root (31B QAT W4A16, sem supersessão)**; DEC-002 (zero local; caps de quota por sprint); DEC-003 (pipeline 3 lanes; repo de avaliação não-visto); DEC-004 (paper 12/nov) |

**Não medido (marcado no texto):** tempo/step e VRAM pico de treino; tamanho real do adapter r=16/r=64 no 31B; presença de `peft`/`trl`/`transformers`/`datasets` na imagem Kaggle; split train/eval oficial.

---

## 0. Conflito de premissa — T06_C1 — ENCERRADO

> **GATE-ROOT-01 FECHADO 2026-10-28 pelo root: base = `gemma-4-31b-it-qat-w4a16-ct`. DEC-001 CONFIRMADA, sem supersessão.** O despacho que pediu "Gemma 3 4B-it" era erro (não é variante permitida); registrado como **A-16** no `monitoring/REGISTRO_DE_ACHADOS.md`.

Correção honesta de arquitetura: a inferência desta ADR de que "8 adapters × r=16 só fecham num ~4B" partia da premissa errada de que NÓS serviríamos o base. No eval, **quem serve o 31B é a infra do Kaggle**; os 3 GiB limitam somente os adapters da submissão. Com isso, r=16 no 31B cabe em serving normalmente — e o argumento que restringe rank volta a ser o DADO (seção 1), não o serving.

---

## 1. Config LoRA — decisão (usava variante B; agora É a decisão)

### Base: `gemma-4-31b-it-qat-w4a16-ct` — LoRA direto no checkpoint QAT, **sem bitsandbytes**

| Item | Valor | Rationale |
|---|---|---|
| Quantização | **NENHUMA adicional** — LoRA direto no QAT W4A16 | **QLoRA NF4 por cima de QAT W4A16 é dupla quantização: rejeitado.** O checkpoint já é 4-bit nativo quantization-aware; re-quantizar com NF4 (i) degrada pesos que já nasceram quantizados comawareness de treino, (ii) adiciona dependência de `bitsandbytes` num ambiente offline — e bnb compatível com cu128 é incerto. Bonus de engenharia: sem bnb, o risco R-T06-2 (deps) encolhe para `peft`/`trl`/`transformers`/`datasets` |
| Dtype dos LoRA params | bf16 | padrão do peft sobre checkpoint bf16-compute; masters fp32 do otimizador 8-bit |
| **rank** | **16** | Justificado POR DADO abaixo (serving deixa de ser o argumento restritivo — ver correção §0) |
| **alpha** | **32** (2×r, scaling=2) | padrão de SFT pequeno; rsLoRA (`alpha/√r`) só vale r≥64 — rejeitada aqui |
| dropout | 0.05 (sobe para 0.1 no gatilho G3) | dado minúsculo é o maior risco, não underfit |
| target_modules | q, k, v, o, gate, up, down | cobertura completa dos lineares; patch generation é formato+código |
| otimizador | adamw 8-bit paginado (`paged_adamw_8bit`) | se `bitsandbytes` não entrar no wheels dataset: degradar para `adamw_torch` (estados fp32, +VRAM — cabe no orçamento de 92 GB) |
| seq len treino | **16384**, truncando somente o lado do CONTEXTO (gold patch intacto) | p90 = 17209; `max_seq_length=4096` do script atual cortaria o gold patch de 18+ pares — mudança obrigatória |

**Divisão nas 4 L4s (`device_map="auto"`, sharding por camadas; NÃO é DDP — QLoRA/LoRA num modelo já quantizado não faz DDP padrão):**

- Pesos QAT W4A16 do 31B: ~**16–18 GB** → ~4–4.5 GB/GPU em 4 GPUs `[A MEDIR NA S1: split real do device_map]`.
- Embeddings/lm_head bf16 com vocabulário grande: ~2–3 GB adicionais (aposentado `[A MEDIR]` — depende do vocab real).
- Estados LoRA em r=16 (params + grads bf16 + otimizador 8-bit): ~0.5–1 GB total `[A MEDIR: depende do nº real de params treináveis]`.
- Ativações com gradient checkpointing a 16k seq, batch 1, sharding por camadas: ~1–2 GB/GPU `est.`.
- **Estimativa total: ~26–40 GB dos 92 GB** (~6.5–10 GB por L4) → **folga grande**; o 22–28 GB da versão anterior era a leitura de um GPU-pool menor. `[A MEDIR NA S1: pico por GPU via nvidia-smi no smoke]`

### Por que r=16 e NÃO r=128/alpha=256 (premissa original rejeitada) — argumento CORRIGIDO

1. **Dado (argumento primário e agora único restritivo):** 128 pares × ~8k tokens médios ≈ **~1M tokens/época**. r=128 em todos os lineares do 31B é ainda MAIS parâmetros treináveis que no 4B (~150M+ escalados) — razão params/tokens de treino pior ainda. Memória de superfície dos 128 gold patches, generalização ruim no repo **não-visto** (DEC-003). O teto de dado é estrutural (≤129) e não cresce com compute.
2. **Serving (argumento corrigido): adaptações cabem, então o limite NÃO é o que restringe.** r=16 ≈ 110–220 MB/adapter (número do harness, medido); até 4 adapters = 0.44–0.88 GB ≤ 3 GiB ✓. A correção do root removeu este argumento contra rank alto para UM adapter — mas ele permanece parcialmente para o cenário multi-adapter r=64 (abaixo).

**r=64 sobe ou desce? Honestamente: DESCE de prioridade neste cenário.** Com o serving folgado em r=16, o único custo em subir o rank seria VRAM/throughput (folga existe) — ou seja, no 31B não falta NADA que r=64 mitigasse com o mesmo dado. O que falta é DADO; mais rank sem mais dado só aumenta a capacidade de memorizar. Ele permanece como probe único condicionado (não como grid):

- **Sonda r=64 (condicionada, SES-2):** só executa se a SES-1 mostrar val loss ruim em r=16 por UNDERFIT (val loss alta e estagnada) — improvável em SFT de formato. Se executar e ganhar: validar tamanho do adapter em serving —extrapolando linear do número do harness, r=64 ≈ **4× → ~440–880 MB/adapter `[A MEDIR NA S1: tamanho real]`**; 1 adapter compartilhado cabe nos 3 GiB, **4 adapters por agente provavelmente não** — nesse caso r=64 só vale com adapter compartilhado.

## 2. Estratégia de dado (128 pares)

1. **Filtro:** 2 pares > 32768 tokens **DESCARTADOS** (1.6%; truncar 92k → 16k ensina patch incompleto). 126 úteis.
2. **18 pares > 16384:** truncar somente o contexto (lado esquerdo), gold patch intacto. `[A MEDIR NA S1: contexto remanescente por par]`
3. **Holdout:** 16 pares (12.5%) estratificados por repo — detector de overfit (G3). 112 de treino.
4. **Augmentação (mitigação nº 1 do ceiling_note):** variantes de subconjunto de contexto, **K=2**, amostradas por época. `[A MEDIR NA S1: ganho em val loss]`
5. **Multi-época:** **5 épocas máx., early stopping paciência 2** na val loss. eff. batch: `per_device 1 × grad_accum 4` (mudança no script: 16→4) → ~28 steps/época × 5 ≈ **~140 optimizer steps**. Dataset pequeno pede muitos passos de atualização, não batch grande.
6. **LR:** **1e-4**, cosine → 0, warmup 5%. (Script atual: 2e-4/3 épocas — mudança obrigatória; LR agressiva em dado pequeno acelera memorização.)
7. **Loss só no assistant:** `packing=False` + máscara de completion (o `format_training_data` atual treina loss no contexto cru — mudança obrigatória; input no formato `messages` do `pairs.jsonl`).

## 3. Plano de sessões — 31B multi-GPU (~15h efetivas/sem; 1h de L4x4 = 2h de quota)

**Tempo por época (estimativa declarada, NÃO medida):** ~1M tokens/época num 31B com grad checkpointing em ~480 TFLOPS nominais de 4×L4 e eficiência real ~30–40% → **~15–45 min/época** `[A MEDIR NA S1]`. Treino completo (5 épocas + avaliações): **~1.3–4 h** → cabe em UMA sessão de 6h. As sessões existem para iteração e contingência, não para uma maratona única.

| Sessão | Sprint | ≤h | Conteúdo |
|---|---|---|---|
| SES-1 | S1 | 3 | **T-11 smoke**: `pip freeze` (peft/trl/transformers/datasets — **bnb não é mais esperado**); load do 31B QAT via `device_map="auto"` nas 4 L4s; 20 steps; medir **s/step, VRAM pico POR GPU, tokens/s, split real do device_map** |
| SES-2 | S1 | 6 | **Sonda r=16 (2 épocas, 2 GPUs)** + **sonda r=64 condicionada (2 GPUs)** — artéria: cada probe do 31B precisa ≥2 GPUs, então NO MÁXIMO 2 probes paralelos (diferente do plano do 4B descartado, que fazia grid em 1 GPU cada) |
| SES-3 | S2 | 6 | **Treino final** (config vencedor, 5 épocas, early stop, K=2) → adapter v1 exportado |
| SES-4 | S2 | 3 | Buffer: retreino / adapter 2º agente / DPO — primeira a ser cortada |

Total ≈ 12–18h de sessão espalhadas em S1+S2 — dentro dos caps da DEC-002 (S1 ≤12h, S2 ≤9h).

**Persistência entre sessões:** adapter + trainer state em r=16 (~200–400 MB no 31B) `save_strategy="epoch"`, `save_total_limit=2`; cada `Save & Run All` versiona o output; sessão seguinte anexa o output anterior como input para `resume_from_checkpoint`. Proibido salvar pesos do base (~17 GB × checkpoint estouraria os 20 GB de `/kaggle/working`).

## 4. Plano B — degradação com gatilhos medidos

| Gatilho (medido) | Ação |
|---|---|
| **G1** VRAM pico > **20 GiB em QUALQUER L4** | seq 16384→8192 (ativação é o termo elástico) → se persistir: reduzir sharding desbalanceado / rebalancear `device_map` manual → último recurso rank 16→8 (improvável) |
| **G2** s/step > **45 s** (projeção: 5 épocas ≤~4h) | seq→8192 + packing off revisado → se >90 s: 3 épocas |
| **G3** val loss sobe 2 avaliações seguidas | dropout→0.1, épocas↓ → persiste: r→8 |
| **G4** sessão Kaggle morre | resume do checkpoint anexado (barato: ~200–400 MB) |
| **G5** `peft`/`trl`/`transformers`/`datasets` ausentes | wheels no host (`pip download`), anexados como Kaggle Dataset, `pip install --no-index --find-links /kaggle/input/gemma4-wheels`, pins compatíveis com torch 2.11+cu128. Sem bnb no treino — um risco a menos |
| **G6 (último recurso)** | submissão **SEM adapter** (schema permite): prompt-only baseline; o treino nunca bloqueia a competição |
| **G7 (escalada ao ROOT)** | se 4×L4 não fechar nem com G1/G2 (OOM estrutural no 31B, o que a aritmética diz ser improvável com 92 GB): descer para **base 12b** — é mudança de DEC-001, decisão EXCLUSIVA do root; esta ADR só a escala, nunca a executa |

## 5. Integração com o eval (treino ↔ serving)

1. **Quem serve o base é a infra do Kaggle** (correção §0); a submissão carrega apenas adapters. `max_lora_rank: 128` do harness é o teto, não a meta.
2. **Regra 1:1:** treina r=16 → serve r=16, direto, sem conversão. Não existe "compressão" r=128→r=16 no serving (SVD degrada; retrinar é mais barato).
3. O harness lê `r`/`alpha`/`target_modules` do **`adapter_config.json`**; o `agent.yaml` aponta `adapter: <nome>` por agente (schema T-09). `base_model_name_or_path` DEVE casar com o modelo servido — checagem obrigatória no `assemble_agent.py`/validador.
4. **Orçamento de serving:** até 4 adapters (root + 3 sub-agentes) × r=16 ≈ 0.44–0.88 GB ≤ 3 GiB ✓ (número do harness). Em r=64, multi-adapter fica arriscado (§1) — r=16 é o cenário por design.
5. **v1: 1 adapter compartilhado** entre agentes; especialização por agente (multi-LoRA) só depois de o adapter único provar ganho no eval.
6. Tamanho real do adapter no 31B é a ÚNICA suposição de serving não medida: **`[A MEDIR NA S1 no export da SES-3]`** — validar ≤3 GiB no `validate_submission.py` antes de qualquer submit.

## 6. Falsificação

- **r=16 é falsificado por UNDERFIT:** val loss alta e estagnada na SES-2 → sonda r=64 (com cuidado de serving, §1).
- **As estimativas de tempo/VRAM são falsificadas na SES-1:** se VRAM pico por GPU > 20 GiB ou s/step > 45 s, os gatilhos G1/G2 disparam e as estimativas desta ADR são corrigidas com dados reais.
- **A augmentação K=2 é falsificada se** não mover val loss → descartar, multi-época puro.

## 7. Consequências

1. `scripts/train_lora.py` rework antes da SES-1: **remover `BitsAndBytesConfig`/`prepare_model_for_kbit_training`** (load direto do QAT); `max_seq_length` 4096→16384; `packing=False` + máscara assistant-only; LR 2e-4→1e-4; `grad_accum` 16→4; épocas 3→5 com early stop; input em `messages`; holdout estratificado; adapter-only checkpoints; remover wandb (offline).
2. T-11 herda as medições: s/step, VRAM por GPU, split do `device_map`, `pip freeze`, **tamanho do adapter exportado**.
3. DEC-001 segue VIGENTE (31B) — `ALLOWED_MODELS` do validador e o `model:` da submissão NÃO mudam. A-16 registra o erro de despacho ("Gemma 3 4B-it") para não ressurgir.
4. **Nota — Small Model Prize (FORA DO ESCOPO desta ADR):** existe prêmio de **US$ 10k exigindo base E2B/E4B**. A DEC-001 já o registrou ("E2B só se sobrar quota após M3"). Qualquer LoRA para E2B/E4B seria uma NOVA decisão do root (e uma variante separada, pois adapter ≠ mesmo base). Não planejado aqui.
5. Quota: 1h de L4x4 = 2h de quota; sessões ≤6h cada; SES-4 é o buffer cortável.
6. Nenhum conteúdo de Competition Data nesta ADR — somente números agregados.

## 8. Riscos (catastrófico primeiro)

| # | Risco | Mitigação |
|---|---|---|
| R-T06-1 | ~~Adapter no base errado~~ **ENCERRADO** — GATE-ROOT-01 fechou 31B; A-16 registra o erro de despacho | adapter_config ↔ modelo servido validado por script (§5.3) como checagem permanente |
| R-T06-2 | Deps offline ausentes (peft/trl/transformers/datasets; bnb descartado do treino) | probe `pip freeze` SES-1; wheels dataset + `--no-index`; degradação p/ `adamw_torch` se otimizador 8-bit indisponível |
| R-T06-3 | **Treinar sobre o conjunto de avaliação** (se tasks.jsonl não for o split de treino) — anti-ataque à régua, desclassificação | `[A MEDIR NA S1: confirmar nas regras o split oficial]`; auditoria Musa pré-submissão (DEC-003) |
| R-T06-4 | **Overfit em 128 pares** no repo não-visto | r=16, early stop paciência 2, holdout 12.5%, dropout escalável (G3) |
| R-T06-5 | Quota 2× estourada | sessões ≤6h, ≤2 probes paralelos (cada um precisa 2 GPUs), SES-4 cortável, caps DEC-002 |
| R-T06-6 | `/kaggle/working` 20 GB | adapter-only + trainer state (~200–400 MB); proibido salvar pesos do base |
| R-T06-7 | Truncamento degrada pares longos (p90 17k, max 92k) | drop dos 2 >32k; truncar só contexto; seq 16384 |
| R-T06-8 | Tamanho real do adapter no 31B > estimativa do harness | `[A MEDIR NA S1]` no export; fallback adapter compartilhado; max_lora_rank do harness dá teto até 128 se necessário (nunca como meta) |
