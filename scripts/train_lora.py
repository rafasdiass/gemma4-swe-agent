#!/usr/bin/env python3
"""
LoRA Training Script for Gemma 4 31B
Supports single-task, multi-task, and DPO training modes.
"""

import argparse
import json
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import DPOTrainer, SFTTrainer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LoRA for Gemma 4 31B")
    parser.add_argument("--version", required=True, choices=["v1", "v2", "dpo", "final"])
    parser.add_argument("--model", default="google/gemma-4-31b-it-qat-w4a16-ct")
    parser.add_argument("--data_path", default="data/processed/train_issues.json")
    parser.add_argument("--output_dir", default="adapters/main_lora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--rank", type=int, default=128)
    parser.add_argument("--alpha", type=int, default=256)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=16)
    parser.add_argument("--multi_task", action="store_true")
    parser.add_argument("--base_lora", type=str, help="Path to base LoRA for DPO")
    parser.add_argument("--wandb", action="store_true")
    return parser.parse_args()


def load_model_and_tokenizer(model_name: str, rank: int, alpha: int) -> tuple:
    """Load Gemma 4 31B with QLoRA 4-bit quantization."""

    # 4-bit quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Load model with 4-bit quantization
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )

    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)

    # LoRA config
    lora_config = LoraConfig(
        r=rank,
        lora_alpha=alpha,
        target_modules=[
            "q_proj",
            "v_proj",
            "k_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer


def format_training_data(example: dict) -> dict:
    """Format issue data for SFT training."""
    # This would be customized based on the actual dataset format
    # Expected: issue_text, repo_context, gold_patch
    prompt = f"""<|user|>
Issue: {example.get("issue_text", "")}

Repository: {example.get("repo_name", "")}
Base commit: {example.get("base_commit", "")}

Generate a patch that fixes this issue.
<|assistant|>
{example.get("gold_patch", "")}"""

    return {"text": prompt}


def main() -> None:
    args = parse_args()

    # Setup output directory
    output_dir = Path(args.output_dir) / args.version
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load model and tokenizer
    print(f"Loading model: {args.model}")
    model, tokenizer = load_model_and_tokenizer(args.model, args.rank, args.alpha)

    # Load dataset
    print(f"Loading data from: {args.data_path}")
    dataset = load_dataset("json", data_files=args.data_path, split="train")

    # Format data
    dataset = dataset.map(format_training_data, remove_columns=dataset.column_names)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        report_to="wandb" if args.wandb else "none",
        remove_unused_columns=False,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
    )

    # Trainer
    if args.version == "dpo" and args.base_lora:
        # Load base LoRA for DPO
        # This is simplified - actual implementation would load the base LoRA
        trainer = DPOTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            beta=0.1,
            max_length=4096,
            max_prompt_length=2048,
        )
    else:
        trainer = SFTTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            max_seq_length=4096,
            packing=True,
            dataset_text_field="text",
        )

    # Train
    print("Starting training...")
    trainer.train()

    # Save final model
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Save adapter config
    adapter_config = {
        "base_model_name_or_path": args.model,
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "r": args.rank,
        "lora_alpha": args.alpha,
        "target_modules": [
            "q_proj",
            "v_proj",
            "k_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "lora_dropout": 0.05,
        "bias": "none",
    }

    with open(output_dir / "adapter_config.json", "w") as f:
        json.dump(adapter_config, f, indent=2)

    print(f"Training complete. Model saved to {output_dir}")


if __name__ == "__main__":
    main()
