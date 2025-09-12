#!/bin/bash

# Credit Checker Endless Scraping Management Script
# Usage: ./run-endless-scraping.sh [start|stop|restart|status|logs]

set -e

CONTAINER_NAME="credit-checker-scraping"
BATCH_SIZE=${BATCH_SIZE:-5}

case "${1:-start}" in
    start)
        echo "🚀 Starting Credit Checker Endless Scraping..."
        echo "📊 Batch size: $BATCH_SIZE claims per cycle"
        echo ""
        
        # Build the Docker image
        echo "🔨 Building Docker image..."
        docker build -t credit-checker-scraping .
        
        # Start the container
        echo "🏃 Starting endless scraping container..."
        docker run -d \
          --name $CONTAINER_NAME \
          -v "$(pwd)/output:/app/output" \
          -v "$(pwd)/logs:/app/logs" \
          -v "$(pwd)/overall_checked_claims.csv:/app/overall_checked_claims.csv" \
          -v "$(pwd)/claims.csv:/app/claims.csv" \
          --shm-size=2g \
          --security-opt seccomp:unconfined \
          -e BATCH_SIZE=$BATCH_SIZE \
          credit-checker-scraping
        
        echo "✅ Container started successfully!"
        echo "📊 Use './run-endless-scraping.sh logs' to view logs"
        echo "🛑 Use './run-endless-scraping.sh stop' to stop"
        ;;
        
    stop)
        echo "🛑 Stopping Credit Checker Scraping..."
        docker stop $CONTAINER_NAME 2>/dev/null || echo "Container not running"
        docker rm $CONTAINER_NAME 2>/dev/null || echo "Container not found"
        echo "✅ Container stopped!"
        ;;
        
    restart)
        echo "🔄 Restarting Credit Checker Scraping..."
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        echo "📊 Credit Checker Scraping Status:"
        echo "=================================="
        if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
            echo "✅ Container is running"
            echo "📈 Container stats:"
            docker stats $CONTAINER_NAME --no-stream
        else
            echo "❌ Container is not running"
        fi
        ;;
        
    logs)
        echo "📋 Credit Checker Scraping Logs:"
        echo "==============================="
        docker logs -f $CONTAINER_NAME
        ;;
        
    *)
        echo "Usage: $0 [start|stop|restart|status|logs]"
        echo ""
        echo "Commands:"
        echo "  start   - Start the endless scraping container"
        echo "  stop    - Stop the endless scraping container"
        echo "  restart - Restart the endless scraping container"
        echo "  status  - Show container status and stats"
        echo "  logs    - View container logs (follow mode)"
        echo ""
        echo "Environment variables:"
        echo "  BATCH_SIZE - Number of claims per cycle (default: 5)"
        echo ""
        echo "Examples:"
        echo "  BATCH_SIZE=10 $0 start  # Start with 10 claims per cycle"
        echo "  $0 logs                # View logs"
        echo "  $0 status              # Check status"
        exit 1
        ;;
esac
