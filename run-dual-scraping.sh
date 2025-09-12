#!/bin/bash

# Credit Checker Dual Scraping Management Script
# Runs two containers: one for even case IDs, one for odd case IDs
# Usage: ./run-dual-scraping.sh [start|stop|restart|status|logs]

set -e

CONTAINER_EVEN="credit-checker-even"
CONTAINER_ODD="credit-checker-odd"
BATCH_SIZE=${BATCH_SIZE:-5}

case "${1:-start}" in
    start)
        echo "🚀 Starting Credit Checker Dual Scraping..."
        echo "📊 Batch size: $BATCH_SIZE claims per cycle per container"
        echo "🔍 Even container: Processing even case IDs"
        echo "🔍 Odd container: Processing odd case IDs"
        echo ""
        
        # Build the Docker image
        echo "🔨 Building Docker image..."
        docker build -t credit-checker-scraping .
        
        # Start even container
        echo "🏃 Starting even container..."
        docker run -d --restart=unless-stopped \
          --name $CONTAINER_EVEN \
          -v "$(pwd)/output:/app/output" \
          -v "$(pwd)/logs:/app/logs" \
          -v "$(pwd)/overall_checked_claims.csv:/app/overall_checked_claims.csv" \
          -v "$(pwd)/claims.csv:/app/claims.csv" \
          -v "$(pwd):/app/data" \
          --shm-size=2g \
          --security-opt seccomp:unconfined \
          -e BATCH_SIZE=$BATCH_SIZE \
          -e FILTER_TYPE=even \
          credit-checker-scraping
        
        # Start odd container
        echo "🏃 Starting odd container..."
        docker run -d --restart=unless-stopped \
          --name $CONTAINER_ODD \
          -v "$(pwd)/output:/app/output" \
          -v "$(pwd)/logs:/app/logs" \
          -v "$(pwd)/overall_checked_claims.csv:/app/overall_checked_claims.csv" \
          -v "$(pwd)/claims.csv:/app/claims.csv" \
          -v "$(pwd)/daily_claims_$(date +%Y-%m-%d).csv:/app/daily_claims_$(date +%Y-%m-%d).csv" \
          --shm-size=2g \
          --security-opt seccomp:unconfined \
          -e BATCH_SIZE=$BATCH_SIZE \
          -e FILTER_TYPE=odd \
          credit-checker-scraping
        
        echo "✅ Both containers started successfully!"
        echo "📊 Use './run-dual-scraping.sh status' to view status"
        echo "📋 Use './run-dual-scraping.sh logs' to view logs"
        echo "🛑 Use './run-dual-scraping.sh stop' to stop"
        ;;
        
    stop)
        echo "🛑 Stopping Credit Checker Dual Scraping..."
        docker stop $CONTAINER_EVEN $CONTAINER_ODD 2>/dev/null || echo "Containers not running"
        docker rm $CONTAINER_EVEN $CONTAINER_ODD 2>/dev/null || echo "Containers not found"
        echo "✅ Both containers stopped!"
        ;;
        
    restart)
        echo "🔄 Restarting Credit Checker Dual Scraping..."
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        echo "📊 Credit Checker Dual Scraping Status:"
        echo "======================================"
        echo ""
        echo "🔍 Even Container:"
        if docker ps -q -f name=$CONTAINER_EVEN | grep -q .; then
            echo "✅ Running"
            docker stats $CONTAINER_EVEN --no-stream
        else
            echo "❌ Not running"
        fi
        echo ""
        echo "🔍 Odd Container:"
        if docker ps -q -f name=$CONTAINER_ODD | grep -q .; then
            echo "✅ Running"
            docker stats $CONTAINER_ODD --no-stream
        else
            echo "❌ Not running"
        fi
        ;;
        
    logs)
        echo "📋 Credit Checker Dual Scraping Logs:"
        echo "===================================="
        echo "Choose which container logs to view:"
        echo "1) Even container"
        echo "2) Odd container"
        echo "3) Both (interleaved)"
        read -p "Enter choice (1-3): " choice
        
        case $choice in
            1)
                docker logs -f $CONTAINER_EVEN
                ;;
            2)
                docker logs -f $CONTAINER_ODD
                ;;
            3)
                docker logs -f $CONTAINER_EVEN $CONTAINER_ODD
                ;;
            *)
                echo "Invalid choice"
                exit 1
                ;;
        esac
        ;;
        
    *)
        echo "Usage: $0 [start|stop|restart|status|logs]"
        echo ""
        echo "Commands:"
        echo "  start   - Start both even and odd containers"
        echo "  stop    - Stop both containers"
        echo "  restart - Restart both containers"
        echo "  status  - Show status of both containers"
        echo "  logs    - View logs (choose which container)"
        echo ""
        echo "Environment variables:"
        echo "  BATCH_SIZE - Number of claims per cycle per container (default: 5)"
        echo ""
        echo "Examples:"
        echo "  BATCH_SIZE=10 $0 start  # Start with 10 claims per cycle per container"
        echo "  $0 logs                # View logs"
        echo "  $0 status              # Check status"
        exit 1
        ;;
esac
