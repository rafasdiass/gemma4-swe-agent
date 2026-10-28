# S0 — T-08: Bootstrap da máquina de execução (recibo)

**Data:** 2026-10-28 · **Executor:** zeus (subagente) + Ayla (host, fechamento com shell)
**Máquina:** Windows 11 + WSL (A-05 — esta É a máquina de execução), repo em `D:\workspaces\gemma4-swe-agent`
**Método:** o runtime do subagente zeus não tem shell (`T08_SHELL_UNAVAILABLE` na 1ª rodada, registrada abaixo por honestidade do recibo); a sessão host executou a receita deixada por ele e **substituiu os BLOQUEADOS item a item** por medição real, mesmo dia.

## DoD da T-08 — status item a item

| # | DoD | Status | Prova |
|---|-----|--------|-------|
| 1 | Clone do repo na máquina | ✓ | `.git/refs/heads/main` = `bd9ac301db861c5d46cadd67e0512d716dc79b7e` (main @ bd9ac30, PR #1 merged 2026-10-27T19:49Z). |
| 2 | `gh auth` com escopo `workflow` | ✓ | `gh auth status`: token `rafasdiass`, scopes `gist, read:org, repo, workflow` (A-03 satisfeito — push de `.github/workflows/*` aceito). |
| 3 | `gh pr checks 1 -R rafasdiass/gemma4-swe-agent` responde | ✓ (com achado) | Comando responde. **ACHADO:** CI do PR #1 (rodando em main pós-merge) está VERMELHO: `Lint & Typecheck` FAIL (1s), `Tests` FAIL (2s), `DVC Sync` e `Validate Submission Structure` skipping. Falha em ≤2s = quebra de setup, não de teste. Registrado no REGISTRO_DE_ACHADOS; afeta T-02. |
| 4 | Kaggle CLI instalado + auth responde | ✓ | CLI **2.2.5** via `uv tool install --python 3.12 kaggle`. OAuth **completado no browser do root** (fluxo `kaggle auth login` PKCE, código de verificação fornecido pelo root): `You are now logged in as [rafasdias]`; credencial em `%USERPROFILE%\.kaggle\credentials.json` (374 bytes, KGRT). Prova: `kaggle competitions list --search gemma-4` responde — `gemma-4-developer-agent` com `userHasEntered: True` (regras aceitas ✓). **ACHADO:** o paper track (`gemma-4-developer-agent-paper`) mostra `userHasEntered: False` — é competição SEPARADA e o prazo é 12/nov; entrar nela é decisão/ação do root. |
| 5 | MCP panteao no ar | ✓ | `GET :8090/healthz` → 200 `{"status":"ok","version":"0.4.6",...}` (2026-10-28T13:16Z). Modo panteão ATIVO no host OpenCode (Ayla anfitria). Obs.: build 0.4.6 aqui vs 2.0.5 na máquina de origem — builds diferentes, sem impacto para esta planning. |
| 6 | DVC instalado (`dvc version` responde) | ✓ | DVC **3.67.1** via `uv tool install --python 3.12 dvc --with dvc-s3` (o repo usa remote s3; sem o plugin, `dvc version` morria com `No module named 'dvc_s3'`). |
| 7 | DVC remote configurado com creds | ✓ (redesenhado pelas regras do evento) | **Decisão 2026-10-28 (root + Ayla): NADA de cloud.** Regras da competição (página oficial): "you must not redistribute the Competition Data (problem statements, patches and test patches) to anyone who has not accepted the rules" — dataset e pares SFT derivados não podem residir em serviço de terceiros; e "Everything happens inside Kaggle" — o treino usa o dataset anexado pela aba Data, não um remote. Configurado: `dvc remote add myremote D:\dvcstore\gemma4-swe-agent -f` (remote LOCAL, versiona artifacts pequenos: métricas, configs). `dvc status` operante. Implicação anotada pra T-02: `dvc-sync.yml` vira no-op ou sai do pipeline. |
| 8 | Cap da máquina medido | PARCIAL | Hardware medido: i5-1235U (12 threads), **15.7 GB RAM**, carga ociosa. **cap_leve provisional = 4** (não 6): com 15.7 GB e enxame node por sessão (~1–2 GB/sessão), 6 sessões simultâneas não cabem com folga de 2 GB — o critério do ritual (RAM livre > 2 GB sob carga) derruba o placeholder. Confirmação sob carga real fica pro primeiro enxame ativo (ritual SPRINT_HEALTH). |

## Bloqueios nomeados (vigentes)

- **PAPER_TRACK_NOT_ENTERED** — a conta `rafasdias` entrou na competição principal mas NÃO no paper track (competição separada; prazo 12/nov). Decisão e clique são do root: kaggle.com/competitions/gemma-4-developer-agent-paper → Join.

## Resolvidos nesta rodada (histórico)

- ~~T08_SHELL_UNAVAILABLE~~ — limitação do runtime do subagente; host fechou com shell.
- ~~KAGGLE_CRED_ABSENT~~ — resolvido via OAuth PKCE no browser do root (credentials.json KGRT válido).
- ~~DVC_REMOTE_PLACEHOLDER~~ — resolvido por REDESENHO: remote local `D:\dvcstore\gemma4-swe-agent`, alinhado às regras do evento (sem redistribuição de Competition Data a terceiros).

## Cap da máquina (alimenta o paralelismo das próximas waves)

- CPU: 12 threads (i5-1235U), RAM: 15.7 GB.
- **cap_leve = 4 (provisional)** — justificativa: RAM é a restrição (não CPU); 4 sessões × ~1.5–2 GB deixa ~6–8 GB livres para o sistema + backend panteao. `cap_pesado = 1` (Kaggle, serializa por construção — inalterado).
- Validação sob carga: primeira wave com 2+ agentes simultâneos, medir RAM livre e CPU sustained (ritual em `monitoring/SPRINT_HEALTH.md`).

## Conclusão

T-08 **7/8 fechados com prova** (clone, gh workflow, gh checks responde, Kaggle CLI + OAuth, MCP panteao, DVC instalado, DVC remote local). Único item aberto: cap sob carga real (validação na primeira wave com enxame ativo). **W1 (T-01, T-03, T-04) pode abrir.**
