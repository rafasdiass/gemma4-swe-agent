#!/bin/bash
# Download and extract Kaggle competition dataset
set -euo pipefail

COMPETITION="gemma-4-developer-agent"
OUTPUT_DIR="data/raw/gemma4_dataset"

echo "Downloading dataset for $COMPETITION..."

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Download
kaggle competitions download -c "$COMPETITION" --force

# Extract
echo "Extracting dataset..."
unzip -o "${COMPETITION}.zip"

# Clean up zip
rm "${COMPETITION}.zip"

# Show structure
echo "Dataset structure:"
find . -type f | head -30

echo "Dataset downloaded to $OUTPUT_DIR"
