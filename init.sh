#!/bin/bash
set -e

echo "=== Lean4Evaluation - Environment Setup ==="

# Check Python version
python_version=$(python --version 2>&1)
echo "Python: $python_version"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv package manager not found. Install it via: pip install uv"
    exit 1
fi

# Install dependencies
echo "Installing dependencies with uv..."
uv sync

# Create results directory
mkdir -p results

# Verify .env exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found. Copy .env.example and fill in your API credentials."
    echo "  cp .env.example .env"
else
    echo ".env file found."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Usage:"
echo "  Task1 (Translation Evaluation):"
echo "    uv run python scripts/run_task1.py --data benchmarks/MiniF2F/MiniF2F-test-examples.jsonl --output results/task1_output.jsonl"
echo ""
echo "  Task2 (Proof Evaluation, Pass@k):"
echo "    uv run python scripts/run_task2.py --data benchmarks/MiniF2F/MiniF2F-test-examples.jsonl --output results/task2_output.jsonl --k 5"
echo ""
echo "See README.md for full documentation."
