#!/bin/bash

# Credit Checker Report Generator
# Generates an HTML report and provides server options

echo "🔍 Generating Credit Checker Report..."

# Run the Python script
python3 generate_report.py

echo ""
echo "📊 Report generated: credit_checker_report.html"
echo ""

# Check if we're on a server (no GUI)
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ] && [ -z "$SSH_CLIENT" ] && [ -z "$SSH_TTY" ]; then
    echo "🖥️  Server environment detected"
    echo ""
    echo "🌐 To view the report, you can:"
    echo "   1. Start a web server: ./start_report_server.sh"
    echo "   2. Use Python's built-in server: python3 -m http.server 8080"
    echo "   3. Copy the file to a web server"
    echo "   4. Download the file to your local machine"
    echo ""
    echo "📁 File location: $(pwd)/credit_checker_report.html"
    echo "📊 File size: $(du -h credit_checker_report.html | cut -f1)"
else
    # Try to open in browser (local machine)
    if command -v open &> /dev/null; then
        echo "🌐 Opening report in browser..."
        open credit_checker_report.html
    elif command -v xdg-open &> /dev/null; then
        echo "🌐 Opening report in browser..."
        xdg-open credit_checker_report.html
    else
        echo "🌐 Open manually in your browser: file://$(pwd)/credit_checker_report.html"
    fi
fi

echo "✅ Done!"
