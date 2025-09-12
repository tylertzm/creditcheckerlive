#!/bin/bash

# Credit Checker Scraping Docker Runner
# Usage: ./run-scraping-docker.sh [number_of_claims]

set -e

# Default number of claims if not provided
CLAIMS=${1:-5}

echo "🚀 Credit Checker Scraping Docker Runner"
echo "========================================"
echo "📊 Processing $CLAIMS claims"
echo ""

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t credit-checker-scraping .

echo ""
echo "🏃 Starting scraping container..."
echo ""

# Run the container with proper volume mounts
docker run --rm \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/overall_checked_claims.csv:/app/overall_checked_claims.csv" \
  -v "$(pwd)/claims.csv:/app/claims.csv" \
  --shm-size=2g \
  --security-opt seccomp:unconfined \
  credit-checker-scraping \
  /app/start.sh "$CLAIMS"

echo ""
echo "✅ Scraping completed!"
echo "📁 Check the following files for results:"
echo "   - claims.csv (detailed results)"
echo "   - overall_checked_claims.csv (processed claims tracking)"
echo "   - output/ (any additional output files)"
echo "   - logs/ (log files)"
