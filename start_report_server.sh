#!/bin/bash

echo "🚀 Starting Credit Checker Report Server..."
echo ""

# Kill any existing server on port 8000
pkill -f "python3 -m http.server 8000" 2>/dev/null

# Start the web server in the background
python3 -m http.server 8000 --bind 0.0.0.0 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Generate the report
echo "📊 Generating report..."
python3 generate_report.py

echo ""
echo "✅ Report server is running!"
echo "🌐 Open the report at: http://localhost:8000/credit_checker_report.html"
echo "📁 CSV files are accessible at:"
echo "   - http://localhost:8000/daily_claims_2025-09-12.csv"
echo "   - http://localhost:8000/overall_checked_claims.csv"
echo ""
echo "Press Ctrl+C to stop the server"

# Keep the script running
wait $SERVER_PID