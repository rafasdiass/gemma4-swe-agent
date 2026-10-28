# MAPA_DE_CLASSIFICACAO — olimp-gemma4-swe-2026-q4

> Uma linha por task. Classes: LEVE (CPU local) / PESADO (quota Kaggle). Prova = comando executável. Derivado das sprints; conferência: contagem de `### T-` == linhas deste mapa.

| Task | Sprint | Classe | Lead | Prova | Medição |
|---|---|---|---|---|---|
| T-08 | S0 | LEVE | Zeus | `gh pr checks 1` + `kaggle competitions list` + MCP no ar | MEDIDO 2026-10-28: 7/8 DoD ✓ (evidencias/S0_bootstrap_maquina.md); cap sob carga pendente p/ W1 |
| T-01 | S0 | LEVE | Atlas | `ls -lh` zip ≥20GB + `unzip -t` + issue lida | MEDIDO 2026-10-28: PASSA — zip 20.42GB íntegro (testzip OK, 524 entradas) + schema do harness documentado (evidencias/S0_dataset.md); gerou A-12 |
| T-02 | S0 | LEVE | Zeus | `gh pr checks 1` all PASS | MEDIDO 2026-10-28: PR #3 merged, CI SUCCESS em dev (run 40702025010); submit-check virou gate de promoção dev→main; dvc-sync.yml deletado (A-08). Restante: branch protection em main (ação do root na UI) |
| T-03 | S0 | LEVE | Apolo | `python -c "yaml.safe_load(open('agent.yaml'))"` | MEDIDO 2026-10-28: parse PASSA (evidencias/S0_t03_agent_yaml.md) MAS A-12 provou divergência de schema → REWORK migrado pra T-09 |
| T-09 | S0 | LEVE | Atena+Apolo | CI verde + dry-run PASSA + diff campo a campo vs sample_submission | MEDIDO 2026-10-28: PR #4 merged, CI SUCCESS em dev (run 40704184656); zip montado e validado de ponta a ponta; 11 testes; riscos T09_R1/R2/R3/R4 resolvidos, R6/R7 medem no T-04 |
| T-04 | S0 | LEVE | Hefesto | `python scripts/simulate_sandbox.py --issue 1` | MEDIDO 2026-10-28: 4 cenários exit 0 (logs em evidencias/S0_t04_sim_issue{1..4}.log); 27 testes; T09_R6 medido (549t/delegação, binding = tool calls, sem saturação dura) e T09_R7 medido (analyzer folga 0t no boundary = ponto mais apertado); ressalvas T04_5/T04_7 em A-13 |
| T-07 | S0 | LEVE | Yara | `python scripts/prepare_data.py --zip ... --out ...` + varredura de invariantes | MEDIDO 2026-10-28: 128/129 pares (1 sem snapshot), 0 patch vazio, 0 duplicado, teto ≤129 justificado (ceiling_note); 2 pares >32k tokens → filtro no treino; recibo evidencias/S0_t07_pairs.md; 39 testes no repo. **Verificação Afrodite: FECHA COM RESSALVA → ressalva resolvida com probe de leak por arquivo: LIMPO (0/128)** |
| T-05 | S0 | LEVE | Zeus | recibo `evidencias/S0_kaggle.md` | MEDIDO 2026-10-28: 4× NVIDIA L4 (23034 MiB cada ≈ 92GB reais), torch 2.11.0+cu128, CUDA 12.8; quota 00:01/30h → ~15h L4x4 efetivas/semana (2× taxa); Persona KYC concluído pelo root; notebook anexado à competição v2 COMPLETE; recibo evidencias/S0_kaggle.md. FECHADA |
| T-06 | S0 | LEVE | Atena | DEC-005 assinada | NAO-MEDIDO (desbloqueada: T-05 fechou; quota ~15h L4x4/semana alimenta o plano de sessões; A-14 traz as regras de L4x4) |
| T-10 | S1 | LEVE | Yara | output notebook Kaggle | NAO-MEDIDO |
| T-11 | S1 | PESADO | Apolo | log W&B smoke | NAO-MEDIDO |
| T-12 | S1 | PESADO | Apolo | `adapters/lora-v1/*.safetensors` + W&B | NAO-MEDIDO |
| T-13 | S1 | LEVE | Hefesto | `evidencias/S1_eval_ab.md` | NAO-MEDIDO |
| T-14 | S1 | LEVE | Hermes | achados A-NN registrados | NAO-MEDIDO |
| T-15 | S1 | LEVE | Apolo | `validate_submission.py --check-prompts` | NAO-MEDIDO |
| T-16 | S1 | LEVE | Gaia | paper/ esqueleto compilável | NAO-MEDIDO |
| T-20 | S2 | LEVE | Apolo | log de tools de grafo por issue | NAO-MEDIDO |
| T-21 | S2 | LEVE | Hefesto | matriz confusão `S2_testgen.md` | NAO-MEDIDO |
| T-22 | S2 | LEVE | Atena | simulação local ≤12h/50 extrapolado | NAO-MEDIDO |
| T-23 | S2 | PESADO | Apolo | `adapters/lora-v2/` + eval > v1 | NAO-MEDIDO |
| T-24 | S2 | LEVE | Hefesto | `evidencias/S2_eval_abc.md` | NAO-MEDIDO |
| T-25 | S2 | LEVE | Hera | REGISTRO atualizado | NAO-MEDIDO |
| T-26 | S2 | LEVE | Gaia | paper compilável com números | NAO-MEDIDO |
| T-27 | S2 | LEVE | Hera | **recibo paper track ≤ 12/nov** | NAO-MEDIDO |
| T-30 | S3 | LEVE | Yara | `prepare_data.py --mode dpo` | NAO-MEDIDO |
| T-31 | S3 | PESADO | Apolo | `adapters/lora-v3/` + W&B | NAO-MEDIDO |
| T-32 | S3 | LEVE | Yara | grid sampling versionado | NAO-MEDIDO |
| T-33 | S3 | LEVE | Musa | `evidencias/S3_policy.md` | NAO-MEDIDO |
| T-34 | S3 | LEVE | Hefesto | `evidencias/S3_stress.md` ≤12h | NAO-MEDIDO |
| T-35 | S3 | LEVE | Hera | RISK_REGISTER com resposta por risco | NAO-MEDIDO |
| T-36 | S3 | LEVE | Atena | DEC plano B com recibo | NAO-MEDIDO |
| T-40 | S4 | LEVE | Apolo | zip abre + checklist confere | NAO-MEDIDO |
| T-41 | S4 | LEVE | Hefesto | `validate_submission.py --strict` PASS | NAO-MEDIDO |
| T-42 | S4 | PESADO | Hefesto | `evidencias/S4_simulacao.md` ≤12h | NAO-MEDIDO |
| T-43 | S4 | LEVE | Musa | `evidencias/S4_policy.md` | NAO-MEDIDO |
| T-44 | S4 | LEVE | Gaia | runbook segue sem perguntas | NAO-MEDIDO |
| T-45 | S4 | LEVE | Hera | **recibo submissão segurança ≤28/nov** | NAO-MEDIDO |
| T-46 | S4 | LEVE | Atlas | teste rollback com recibo | NAO-MEDIDO |
| T-50 | S5 | LEVE | Hefesto | hash SHA256 registrado | NAO-MEDIDO |
| T-51 | S5 | LEVE | Zeus | log diário leaderboard | NAO-MEDIDO |
| T-52 | S5 | LEVE | Hera | **recibo final ≤29/nov** | NAO-MEDIDO |
| T-53 | S5 | LEVE | Gaia | mapa zero NAO-MEDIDO sem motivo | NAO-MEDIDO |
| T-54 | S5 | LEVE | Hermes | retro com ≥3 lições | NAO-MEDIDO |

**Total: 42 tasks** (S0: 8 · S1: 7 · S2: 8 · S3: 7 · S4: 7 · S5: 5). PESADO: T-11, T-12, T-23, T-31, T-42 (quota Kaggle, serializados). Ordem de execução: W0 = T-08 (bootstrap da máquina de execução, A-05) → W1 = T-01/T-03/T-04 → resto por dependências. PESADO: T-11, T-12, T-23, T-31, T-42 (quota Kaggle, serializados).