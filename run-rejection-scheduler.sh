#!/bin/bash
# Script to manage the scheduled rejection container
# Usage: ./run-rejection-scheduler.sh [start|stop|restart|status|logs]

set -e

CONTAINER_NAME="credit-checker-rejection"
CHECK_INTERVAL=${CHECK_INTERVAL:-300}  # 5 minutes default

case "${1:-start}" in
    start)
        echo "🚀 Starting Scheduled Rejection Service..."
        echo "⏰ Check interval: $CHECK_INTERVAL seconds ($(($CHECK_INTERVAL / 60)) minutes)"
        echo "📅 Today: $(date +%Y-%m-%d)"
        echo ""
        
        # Build the Docker image (only if it doesn't exist)
        if docker image inspect credit-checker-scraping >/dev/null 2>&1; then
            echo "✅ Docker image already exists, skipping build..."
        else
            echo "🔨 Building Docker image..."
            docker build -t credit-checker-scraping .
        fi
        
        # Check if container is already running
        if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
            echo "⚠️  Container $CONTAINER_NAME is already running"
            echo "Use './run-rejection-scheduler.sh restart' to restart it"
            exit 1
        fi
        
        # Start rejection scheduler container
        echo "🏃 Starting rejection scheduler container..."
        docker compose -f docker-compose-rejection.yml up -d
        
        echo ""
        echo "✅ Scheduled Rejection Service started!"
        echo ""
        echo "📋 Quick commands:"
        echo "  - View logs:    ./run-rejection-scheduler.sh logs"
        echo "  - Check status: ./run-rejection-scheduler.sh status"
        echo "  - Stop:         ./run-rejection-scheduler.sh stop"
        echo "  - Restart:      ./run-rejection-scheduler.sh restart"
        echo ""
        echo "📊 Monitoring:"
        echo "  - Rejected cases tracker: ./rejected_today.csv"
        echo "  - Daily CSV: ./daily_claims_$(date +%Y-%m-%d).csv"
        ;;
        
    stop)
        echo "🛑 Stopping Scheduled Rejection Service..."
        docker compose -f docker-compose-rejection.yml down
        echo "✅ Service stopped"
        ;;
        
    restart)
        echo "🔄 Restarting Scheduled Rejection Service..."
        docker compose -f docker-compose-rejection.yml down
        sleep 2
        docker compose -f docker-compose-rejection.yml up -d
        echo "✅ Service restarted"
        ;;
        
    status)
        echo "📊 Scheduled Rejection Service Status:"
        echo ""
        if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
            echo "✅ Container: RUNNING"
            docker ps --filter name=$CONTAINER_NAME --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}"
            echo ""
            
            # Check if rejected_today.csv exists and show count
            if [ -f rejected_today.csv ]; then
                line_count=$(wc -l < rejected_today.csv)
                rejected_count=$((line_count - 1))  # Subtract header
                if [ $rejected_count -gt 0 ]; then
                    echo "📋 Rejected today: $rejected_count cases"
                else
                    echo "📋 Rejected today: 0 cases"
                fi
            else
                echo "📋 Rejected today: 0 cases (tracker not created yet)"
            fi
            
            # Check today's CSV
            today_csv="daily_claims_$(date +%Y-%m-%d).csv"
            if [ -f "$today_csv" ]; then
                csv_line_count=$(wc -l < "$today_csv")
                csv_case_count=$((csv_line_count - 1))  # Subtract header
                echo "📄 Today's CSV: $csv_case_count cases"
            else
                echo "📄 Today's CSV: Not found yet"
            fi
        else
            echo "❌ Container: NOT RUNNING"
        fi
        ;;
        
    logs)
        echo "📜 Showing logs (Ctrl+C to exit)..."
        docker compose -f docker-compose-rejection.yml logs -f
        ;;
        
    *)
        echo "Usage: $0 [start|stop|restart|status|logs]"
        echo ""
        echo "Commands:"
        echo "  start   - Start the scheduled rejection service"
        echo "  stop    - Stop the service"
        echo "  restart - Restart the service"
        echo "  status  - Show service status and statistics"
        echo "  logs    - Follow the service logs"
        exit 1
        ;;
esac
