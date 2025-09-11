#!/bin/bash

# Credit Check Scheduler Monitor
# This script monitors the scheduler and restarts it if needed

CONTAINER_NAME="creditcheck-scheduler"
LOG_FILE="logs/monitor.log"
CHECK_INTERVAL=300  # Check every 5 minutes

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if container is running
is_container_running() {
    docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to check if container is healthy
is_container_healthy() {
    docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "healthy"
}

# Function to restart container
restart_container() {
    log_message "🔄 Restarting container..."
    docker-compose down
    sleep 5
    docker-compose up -d
    log_message "✅ Container restarted"
}

# Function to check container logs for errors
check_logs_for_errors() {
    # Get last 50 lines of logs and check for critical errors
    docker logs --tail=50 "$CONTAINER_NAME" 2>&1 | grep -i "fatal\|critical\|error.*scheduler" | wc -l
}

log_message "🚀 Credit Check Scheduler Monitor started"

# Main monitoring loop
while true; do
    if ! is_container_running; then
        log_message "❌ Container is not running, restarting..."
        restart_container
    elif ! is_container_healthy; then
        log_message "⚠️ Container is not healthy, checking logs..."
        error_count=$(check_logs_for_errors)
        if [ "$error_count" -gt 0 ]; then
            log_message "❌ Found $error_count errors in logs, restarting..."
            restart_container
        else
            log_message "ℹ️ Container unhealthy but no critical errors found"
        fi
    else
        log_message "✅ Container is running and healthy"
    fi
    
    sleep "$CHECK_INTERVAL"
done
