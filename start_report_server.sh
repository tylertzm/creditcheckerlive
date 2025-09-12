#!/bin/bash

# Credit Checker Report Server Starter
# Starts a web server to serve the HTML report

PORT=${1:-8080}

echo "🚀 Starting Credit Checker Report Server..."
echo "📊 Port: $PORT"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python3"
    exit 1
fi

# Make sure the script is executable
chmod +x serve_report.py

# Start the server
echo "🌐 Starting server on port $PORT..."
echo "📊 Access the report at: http://localhost:$PORT"
echo "📊 Access the report at: http://$(hostname -I | awk '{print $1}'):$PORT"
echo "🔄 Report auto-refreshes on each visit"
echo "⏹️  Press Ctrl+C to stop"
echo ""

python3 serve_report.py $PORT
