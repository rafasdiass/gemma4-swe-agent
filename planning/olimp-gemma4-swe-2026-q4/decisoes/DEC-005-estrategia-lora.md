# DEC-005 — Estratégia LoRA: QLoRA 4-bit NF4, r=128, alpha=256, sessões ≤6h

**Data:** (vaga — task T-06 da Sprint 0) · **Decisora:** Atena · **Aprovação:** Rafael (root)
**Estado:** RASCUNHO (fecha na S0 com os números do T-05/T-11)

- QLoRA 4-bit NF4 (peft), r=128, alpha=256, dropout 0.05; alvo `q_proj,v_proj,k_proj,o_proj,gate_up_proj,down_proj`.
- Sessão de treino ≤6h (contorno de desconexão Kaggle); checkpoint intermediário; retomada por checkpoint.
- Plano B se OOM/tempo não fechar: r=64/alpha=128; offload de otimizador para CPU (sdpa).
- **Fecha como DEC quando o smoke (T-11) medir tempo/passo e VRAM real.**