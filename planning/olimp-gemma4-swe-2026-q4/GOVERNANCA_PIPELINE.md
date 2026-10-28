# GOVERNANCA_PIPELINE.md — olimp-gemma4-swe-2026-q4

> Modelo **igual ao do monorepo do Panteão** (`aylalabs/panteao`), adaptado a um repo solo de competição. Este doc é a régua: CI que não segue isto aqui é dívida, não decoração.

## Branches

| Branch | Papel | Quem escreve |
|---|---|---|
| `main` | **Promoção congelada.** Só recebe o que vai pra submissão. Rollback = voltar a promoção anterior. | ninguém direto (PR de `dev`, hardDeny push) |
| `dev` | Integração contínua do trabalho. Tasks fecham aqui por PR. | PRs de `feat/*` e `fix/*` |
| `feat/*`, `fix/*` | Lanes de task (uma lane, um escopo declarado). | agente Lead da task |

## Fluxo (regra de ouro)

1. Task nasce de lane `feat/tarefa-escopo` (ou `fix/`), a partir de `dev`.
2. PR **lane → `dev`**: CI leve (lint, mypy, unit, validate_submission `--dry-run`). Merged = task fechada **com evidência**.
3. Promoção **`dev` → `main`**: **SÓ AQUI roda a suite inteira** (ruff, mypy, pytest tudo, `validate_submission.py --strict`, dvc repro pipeline completo, simulação de budget). É o gate de promoção, não o do dia a dia.
4. **Promoção `main` = deploy.** O "deploy" deste repo é o `submission.zip`: uma promoção `dev→main` marca o zip elegível pra submissão. Submissão no Kaggle só de artefato cujo commit está em `main` (recibo: SHA + hash do zip na evidência).
5. `main` **nunca** recebe hotfix direto: hotfix entra por `fix/* → dev → promoção`. Se é blocker de submissão, a promoção é imediata e a evidência diz porquê.

## CI/CD (workflows do repo)

| Workflow | Gatilho | Papel | Regra |
|---|---|---|---|
| `ci.yml` | PR → `dev` | **Gate de lane:** lint (ruff), tipos (mypy em `scripts/`), unit (pytest), `validate_submission.py --dry-run` | PR vermelho não mergeia. Sem exceção, sem "é só warning". |
| `submit-check.yml` | PR **`dev` → `main`** | **Gate de promoção:** a suite inteira + `--strict` + `dvc repro --force-all` + conferência de orçamento extrapolado | Único lugar onde a suite inteira roda. Verde = elegível a "deploy" (submissão). |
| `dvc-sync.yml` | merge em `main` | Empurra adapters/artefatos DVC pro remote S3/GCS | **OBSOLETO por A-08 (2026-10-28): remote DVC agora é LOCAL** (`D:\dvcstore\gemma4-swe-agent`) — vira no-op ou sai do pipeline na T-02. Falha aqui NÃO bloqueia submissão se o zip já foi construído; bloqueia a próxima. |

## Regra de visibilidade pública (2026-10-28, decisão do root)

O repo é **PÚBLICO** (decisão pós-quota Actions: repo público não consome minutos CI, $0; reversível). Com a visibilidade pública, a regra de redistribuição do evento vira lei dura deste pipeline:

- **NUNCA entra no repo** (código, evidência, DVC, planning): conteúdo de **issue** real (problem statement), **gold patch**, **test patch** — o Competition Data. 
- **Pode entrar:** schema abstrato (nomes de campo, tipos, contagens), estatísticas, hashes, trechos de código PRÓPRIO.
- Quem escreve evidência com dataset na mão descreve a FORMA, nunca o CONTEÚDO. Achado que exija mostrar conteúdo vai para o vault privado, não pro repo.

## Regras de deploy (submissão ao Kaggle)

- **Artefato único:** só se submete zip construído de um commit **promovido a `main`**, com SHA registrado na evidência da submissão.
- **Recibo obrigatório:** toda submissão (de segurança S4/T-45 e final S5/T-52) grava timestamp, SHA do commit, SHA256 do zip e o recibo da plataforma em `evidencias/`.
- **Janela de re-submissão:** até 02/dez 23:59 UTC. Depois da final (T-52, alvo 29/nov), zero mudança estrutural: só rollback (T-46) por incidente blocker nomeado.
- **Ordem de corte sob pressão de tempo:** corta-se primeiro o que não bloqueia o zip (T-25, T-54, T-35); **nunca** o gate de promoção (suite inteira) — zip sem gate é submissão de cega.

## Conformidade com o Panteão (mapeamento)

| Panteão | Este repo |
|---|---|
| `main` protegida por hardDeny (musa) | igual: push direto a `main` é recusado no hook local + branch protection via GitHub |
| PR é a única porta de `dev` | igual |
| Suite inteira na promoção `dev→main` | `submit-check.yml` |
| `sync-audit` por caminho script-relativo | scripts do repo carregam helpers relativos ao próprio repo (nada de `$HOME/` externo) |
| Evidência de entrega com SHA + PASS/FAIL | `evidencias/` com recibo por submissão |