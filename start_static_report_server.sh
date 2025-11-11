#!/bin/bash

echo "🚀 Starting Simple Credit Checker Report Server..."
echo ""

# Kill any existing server on port 8080
pkill -f "python3 serve_static_report.py" 2>/dev/null

# Generate the report if it doesn't exist
if [ ! -f "credit_checker_report.html" ]; then
    echo "📊 Generating report..."
    python3 generate_report.py
fi

# Start the static web server
echo "🌐 Starting static server..."
python3 serve_static_report.py

echo ""
echo "✅ Static report server stopped!"