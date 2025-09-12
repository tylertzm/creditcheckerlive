#!/bin/bash

# Credit Checker Endless Scraping Docker Runner
# Usage: ./run-scraping-docker.sh [batch_size]

set -e

# Default batch size if not provided
BATCH_SIZE=${1:-5}

echo "🚀 Credit Checker Endless Scraping Docker Runner"
echo "==============================================="
echo "📊 Batch size: $BATCH_SIZE claims per cycle"
echo "🔄 Running endlessly with 5-minute timeout per cycle"
echo ""

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t credit-checker-scraping .

echo ""
echo "🏃 Starting endless scraping container..."
echo ""

# Run the container with proper volume mounts
docker run --rm \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/overall_checked_claims.csv:/app/overall_checked_claims.csv" \
  -v "$(pwd)/claims.csv:/app/claims.csv" \
  --shm-size=2g \
  --security-opt seccomp:unconfined \
  -e BATCH_SIZE=$BATCH_SIZE \
  credit-checker-scraping

echo ""
echo "🛑 Container stopped!"
echo "📁 Check the following files for results:"
echo "   - claims.csv (detailed results)"
echo "   - overall_checked_claims.csv (processed claims tracking)"
echo "   - output/ (any additional output files)"
echo "   - logs/ (log files)"
