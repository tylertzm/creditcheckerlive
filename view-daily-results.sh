#!/bin/bash

# Daily Results Viewer Script
# Usage: ./view-daily-results.sh [date] [summary|details|keywords]

DATE=${1:-$(date +%Y-%m-%d)}
MODE=${2:-"summary"}

DAILY_CSV="daily_claims_${DATE}.csv"

echo "📅 Daily Results for: $DATE"
echo "=================================="

if [ ! -f "$DAILY_CSV" ]; then
    echo "❌ No daily CSV found for $DATE"
    echo "📋 Available daily files:"
    ls -la daily_claims_*.csv 2>/dev/null || echo "  No daily files found"
    exit 1
fi

case "$MODE" in
    "summary")
        echo "📊 Summary Statistics:"
        echo "====================="
        total_cases=$(tail -n +2 "$DAILY_CSV" | wc -l)
        keyword_found=$(tail -n +2 "$DAILY_CSV" | cut -d',' -f7 | grep -c "True" || echo "0")
        no_keywords=$(tail -n +2 "$DAILY_CSV" | cut -d',' -f7 | grep -c "False" || echo "0")
        
        echo "Total cases processed: $total_cases"
        echo "Cases with keywords found: $keyword_found"
        echo "Cases with no keywords: $no_keywords"
        
        if [ "$total_cases" -gt 0 ]; then
            success_rate=$(echo "scale=1; $keyword_found * 100 / $total_cases" | bc -l 2>/dev/null || echo "0")
            echo "Success rate: ${success_rate}%"
        fi
        ;;
        
    "details")
        echo "📋 Detailed Results:"
        echo "==================="
        column -t -s',' "$DAILY_CSV" | head -20
        if [ $(tail -n +2 "$DAILY_CSV" | wc -l) -gt 20 ]; then
            echo "... (showing first 20 results)"
        fi
        ;;
        
    "keywords")
        echo "🎯 Cases with Keywords Found:"
        echo "============================="
        tail -n +2 "$DAILY_CSV" | awk -F',' '$7 == "True" {print "Case " $1 " (Hit " $3 "): " $8}' | head -10
        ;;
        
    *)
        echo "Usage: $0 [date] [summary|details|keywords]"
        echo "Examples:"
        echo "  $0                    # Today's summary"
        echo "  $0 2025-09-12        # Specific date summary"
        echo "  $0 2025-09-12 details # Detailed view"
        echo "  $0 2025-09-12 keywords # Only cases with keywords"
        ;;
esac

echo ""
echo "📁 File: $DAILY_CSV"
echo "📊 Total size: $(du -h "$DAILY_CSV" | cut -f1)"
