# T-05 — Prova de vida Kaggle L4x4: recibo (2026-10-28)

## Caminho executado

1. **API token**: `kaggle.json` criado no Chrome do root (kaggle.com/settings → Legacy API Credentials → Create Legacy API Key), instalado em `~/.kaggle/` sem log de conteúdo. Validação: `kaggle competitions list --search gemma` responde como `rafasdias`.
2. **Kernel probe**: `kaggle/01_data_exploration.py` (no repo, zero Competition Data) empurrado via `kaggle kernels push` para `rafasdias/notebook13c50a51cf` — notebook **anexado à competição** (L4x4 só existe em notebook anexado; A-14).
3. **Acelerador**: `GPU L4 x4` selecionado no editor (exige verificação de identidade Persona — concluída pelo root em 2026-10-28); **Internet OFF** (obrigatório para L4).
4. **Save & Run All (Commit)** → Version 2 → status `COMPLETE`.

## Números medidos (log do run, `nvidia-smi` + torch)

| Métrica | Valor |
|---|---|
| GPUs | **4× NVIDIA L4** (indices 0-3) |
| VRAM por GPU | **23034 MiB** (nvidia-smi) / 22.0 GiB (torch) |
| VRAM total | **≈ 92 GB reais** (4 × 23034 MiB; nominal anunciado: 96 GB) |
| Driver / CUDA (driver) | 580.178.04 / CUDA 13.0 |
| torch | 2.11.0+cu128, `cuda available: True`, runtime CUDA 12.8 |
| `torch.cuda.device_count()` | 4 |
| Disco | `/` 8.0T (1.1T disponível); `/kaggle/working` 20G |
| Tempo do probe | ~10.6s de compute; sessão completa em minutos |

## Quota

- **GPU L4 x4: `00:01 / 30 hrs` semanais** após o probe (praticamente integral).
- Regra da competição (A-14): L4x4 consome quota a **2× a taxa** do T4x2/P100 → orçamento real ≈ **15h semanais de sessão L4x4**.
- A quóta de GPU é compartilhada do pool geral de 30h/semana; "Link to Colab Pro for more Quota" existe como expansão paga (não usada).

## Prova de vida T4x2 (referência)

- Kernel standalone `rafasdias/gemma4-01-data-exploration` (v1): rodou em `GPU T4 x2`, 2× Tesla T4 14.6 GiB, 14s, SUCCESS — confirma o pipeline de push→run→output via CLI de ponta a ponta.

## DoD

- **"recibo em `evidencias/S0_kaggle.md` com VRAM 96GB confirmada e quota restante"** → VRAM confirmada (4× L4, ≈92GB reais de 96GB nominais) e quota medida (00:01/30h → ~15h L4x4 efetivas). ✓

## Pendências anotadas

- Verificação de identidade (Persona) agora concluída — desbloqueia submissão E L4x4.
- `01_data_exploration` como notebook nomeado: o slug atual é `notebook13c50a51cf` (auto-gerado); renomear em kernel futuro se o contrato exigir nome estável.
