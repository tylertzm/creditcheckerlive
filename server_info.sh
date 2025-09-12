#!/bin/bash

# Server Information for Credit Checker Report
# Shows how to access the report from different locations

echo "🖥️  Credit Checker Report Server Information"
echo "=============================================="
echo ""

# Get server IP addresses
echo "🌐 Server IP Addresses:"
echo "   Local:  http://localhost:8080"
echo "   Local:  http://127.0.0.1:8080"

# Try to get external IP
if command -v hostname &> /dev/null; then
    INTERNAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null)
    if [ ! -z "$INTERNAL_IP" ]; then
        echo "   Internal: http://$INTERNAL_IP:8080"
    fi
fi

# Try to get external IP
if command -v curl &> /dev/null; then
    EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null)
    if [ ! -z "$EXTERNAL_IP" ]; then
        echo "   External: http://$EXTERNAL_IP:8080"
    fi
fi

echo ""
echo "📊 Commands to start the report server:"
echo "   ./start_report_server.sh          # Start on port 8080"
echo "   ./start_report_server.sh 9000     # Start on port 9000"
echo "   python3 -m http.server 8080       # Simple Python server"
echo ""
echo "📁 Report file location:"
echo "   $(pwd)/credit_checker_report.html"
echo ""
echo "🔄 To regenerate the report:"
echo "   ./report.sh"
echo "   python3 generate_report.py"
echo ""
echo "📋 Current report status:"
if [ -f "credit_checker_report.html" ]; then
    echo "   ✅ Report file exists ($(du -h credit_checker_report.html | cut -f1))"
    echo "   📅 Last modified: $(stat -f "%Sm" credit_checker_report.html 2>/dev/null || stat -c "%y" credit_checker_report.html 2>/dev/null)"
else
    echo "   ❌ Report file not found"
fi
