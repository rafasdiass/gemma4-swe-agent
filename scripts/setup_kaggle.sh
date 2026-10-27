#!/bin/bash
# Setup Kaggle CLI in notebook environment
set -euo pipefail

echo "Setting up Kaggle CLI..."

# Install kaggle if not present
if ! command -v kaggle &> /dev/null; then
    pip install kaggle --quiet
fi

# Configure credentials (assumes KAGGLE_API_TOKEN or kaggle.json is set)
if [ -n "${KAGGLE_API_TOKEN:-}" ]; then
    mkdir -p ~/.kaggle
    echo "{\"username\":\"${KAGGLE_USERNAME}\",\"key\":\"${KAGGLE_API_TOKEN}\"}" > ~/.kaggle/kaggle.json
    chmod 600 ~/.kaggle/kaggle.json
    echo "Kaggle credentials configured from environment"
elif [ -f ~/.kaggle/kaggle.json ]; then
    chmod 600 ~/.kaggle/kaggle.json
    echo "Kaggle credentials found in ~/.kaggle/kaggle.json"
else
    echo "WARNING: No Kaggle credentials found. Run 'kaggle auth login' manually."
fi

# Verify access
kaggle competitions list --max-size 1 > /dev/null 2>&1 && echo "Kaggle CLI ready" || echo "Kaggle CLI needs authentication"

# Install competition-specific dependencies
pip install -r requirements-lora.txt --quiet

echo "Setup complete"
