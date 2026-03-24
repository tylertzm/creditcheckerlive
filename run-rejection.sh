#!/bin/bash
# Script to run case rejection from CSV files using Docker
# Uses the existing credit-checker containers which have all dependencies

CONTAINER="credit-checker-even"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if container is running
if ! docker ps | grep -q "$CONTAINER"; then
    echo -e "${YELLOW}⚠️  Container $CONTAINER is not running${NC}"
    echo -e "${BLUE}Starting container...${NC}"
    cd /root/creditcheckerlive && ./run-dual-scraping.sh start
    sleep 5
fi

# Copy latest scripts to container
echo -e "${BLUE}📦 Copying latest rejection scripts to container...${NC}"
docker cp /root/creditcheckerlive/library/rejection/rejection_logic.py $CONTAINER:/app/library/rejection/rejection_logic.py
docker cp /root/creditcheckerlive/library/rejection/rejection_tracker.py $CONTAINER:/app/library/rejection/rejection_tracker.py
docker cp /root/creditcheckerlive/library/rejection/__init__.py $CONTAINER:/app/library/rejection/__init__.py
docker cp /root/creditcheckerlive/library/rejection/reject_cases_from_csv.py $CONTAINER:/app/library/rejection/reject_cases_from_csv.py

# Make script executable
docker exec $CONTAINER chmod +x /app/library/rejection/reject_cases_from_csv.py

echo -e "${GREEN}✅ Scripts updated in container${NC}"
echo ""

# Run the rejection script with passed arguments
echo -e "${BLUE}🚀 Running rejection script...${NC}"
echo -e "${BLUE}Arguments: $@${NC}"
echo ""

docker exec -it $CONTAINER python3 /app/library/rejection/reject_cases_from_csv.py "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Rejection script completed successfully${NC}"
else
    echo ""
    echo -e "${RED}❌ Rejection script failed with exit code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
