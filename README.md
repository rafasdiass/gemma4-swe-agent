# Gemma 4 SWE Agent

**Autonomous Software Engineering Agent for the Gemma 4 Developer Agent Competition**

[![CI](https://github.com/rafasdiass/gemma4-swe-agent/workflows/CI/badge.svg)](https://github.com/rafasdiass/gemma4-swe-agent/actions/workflows/ci.yml)
[![DVC](https://img.shields.io/badge/DVC-enabled-blue)](https://dvc.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

This repository contains the complete implementation of an autonomous software engineering agent built on **Gemma 4 31B** for the [Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent).

### Competition Goal
Post-train Gemma 4 into a reliable autonomous agent that:
- Navigates complex codebases independently
- Diagnoses issues (bugs, features, refactors)
- Generates correct patches that pass validation tests
- Runs on consumer hardware (31B in 24GB VRAM)

### Prize Pool
- **Main Competition**: $65,000 (1st: $37k, 2nd: $18k, 3rd: $10k)
- **Paper Track**: $35,000 (deadline: Nov 12, 2026)
- **Small Model Bonus**: $10,000 (for E2B/E4B variants)

## Architecture

```
gemma4-swe-agent/
├── agent.yaml                 # ADK root configuration
├── configs/
│   ├── sampling.yaml          # Generation parameters
│   └── eval_config.yaml       # Per-task time budgets
├── prompts/
│   ├── system.md              # System prompt (role, principles)
│   ├── analyzer.md            # Code analyzer prompt
│   ├── coder.md               # Patch generator prompt
│   └── verifier.md            # Verifier prompt
├── sub_agents/
│   ├── code_analyzer.yaml     # Repo navigation specialist
│   ├── patch_generator.yaml   # Patch implementation specialist
│   └── verifier.yaml          # Test execution specialist
├── adapters/
│   ├── main_lora/             # LoRA for main coder (git-lfs)
│   └── tool_lora/             # LoRA for tools (git-lfs)
├── skills/
│   ├── repo_navigation/       # Code search & graph navigation
│   ├── test_generation/       # Regression test templates
│   └── patch_validation/      # Pre-submission quality checks
├── notebooks/                 # Kaggle notebooks (L4x4)
├── scripts/                   # Automation scripts
└── planning/                  # Sprint planning docs
```

## Multi-Agent Orchestration (Panteão)

This agent is developed using the **Panteão** multi-agent framework:

| Agent | Role |
|-------|------|
| **Atena** | Architecture, LoRA strategy, RL decisions |
| **Apolo** | ADK spec compliance, agent.yaml, sandbox constraints |
| **Hefesto** | Test harness, CI, patch validation |
| **Hera** | Sprint planning, GPU quota management |
| **Atlas** | Dataset versioning, DVC, artifact management |
| **Iris** | Monitoring UI, skill development |
| **Ayla** | Orchestration, decisions, integration |

## Quick Start

### Prerequisites
- Python 3.11+
- Git LFS (`git lfs install`)
- DVC (`pip install dvc[s3]`)
- Kaggle account with verified phone
- Access to Kaggle L4x4 (96GB VRAM) or equivalent GPU

### Local Setup (Orchestration Only - No Model)
```bash
# Clone repo
git clone git@github.com:rafasdiass/gemma4-swe-agent.git
cd gemma4-swe-agent

# Install dependencies
pip install -r requirements.txt

# Pull DVC artifacts (LoRA weights, dataset)
dvc pull

# Validate submission structure
python scripts/validate_submission.py
```

### Kaggle Notebook Training (Model Training)
1. Open `notebooks/02_lora_training_31b.ipynb` on Kaggle
2. Select **Accelerator: L4x4 (GPU)**
3. Run cells sequentially:
   - Setup environment
   - Load dataset
   - Train LoRA v1 → `dvc push`
   - Train LoRA v2 → `dvc push`
   - Train DPO → `dvc push`

### Submission
```bash
# Assemble final submission.zip
python scripts/assemble_agent.py --version final

# Validate before submit
python scripts/validate_submission.py

# Submit via Kaggle notebook 05_final_submission.ipynb
```

## Development Workflow

### Sprint Structure (5 weeks)
| Sprint | Focus | Deliverable |
|--------|-------|-------------|
| **S0** (Oct 27-31) | Setup & Infra | Repo, CI, Kaggle, agent.yaml skeleton |
| **S1** (Nov 3-7) | Baseline | LoRA v1, first PASS rate |
| **S2** (Nov 10-14) | Multi-Agent | 3-agent pipeline, skills |
| **S3** (Nov 17-21) | Optimization | DPO, graph reasoning, ensemble |
| **S4** (Nov 24-28) | Stress Test | 12h simulation, paper draft |
| **S5** (Nov 29-Dec 2) | Final Submit | Leaderboard entry, paper track |

### Git Workflow
- `main` - Protected, only via PR
- `dev` - Integration branch
- Feature branches: `feat/*`, `fix/*`, `exp/*`
- Tags: `lora-v1-baseline`, `submit-final`

### DVC Artifacts
- `adapters/main_lora/v1/` - Baseline LoRA
- `adapters/main_lora/v2/` - Multi-task LoRA
- `adapters/main_lora/dpo/` - DPO-optimized LoRA
- `data/raw/gemma4_dataset/` - Competition dataset
- `data/processed/` - Processed training data

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Model** | Gemma 4 31B | Max quality for main track |
| **Quantization** | QLoRA 4-bit NF4 | Fits 31B in 24GB VRAM |
| **LoRA Rank** | 128 | Capacity for complex coding |
| **Multi-Agent** | 3-agent (analyzer/coder/verifier) | Separation of concerns |
| **Graph Usage** | All 3 tools | Embedding + call graph + subgraph |
| **RL Strategy** | Iterative DPO | Self-play generates preference data |

## Competition Constraints

| Constraint | Value |
|------------|-------|
| **Model** | Must be Gemma 4 variant (31B/12B/4B/2B) |
| **Budget** | 12 hours total for all issues |
| **Internet** | Disabled during scoring |
| **Tools** | Only 7 ADK tools allowed |
| **Submission** | Single `submission.zip` via Kaggle notebook |
| **Scoring** | % issues resolved (PASS/FAIL on tests) |

## Resources

- **Competition**: [Kaggle Gemma 4 Developer Agent](https://www.kaggle.com/competitions/gemma-4-developer-agent)
- **ADK Spec**: [Google ADK Agent Config](https://adk.dev/agents/config/)
- **Dataset**: `kaggle competitions download -c gemma-4-developer-agent`
- **Models**: [Kaggle Models - Gemma 4](https://www.kaggle.com/models/google/gemma-4)
- **Planning**: `planning/olimp-gemma4-swe-2026-q4.md`

## License

MIT License - See [LICENSE](LICENSE)

## Acknowledgments

- Google DeepMind for Gemma 4 and the competition
- Panteão framework for multi-agent orchestration
- Kaggle for L4x4 GPU access
