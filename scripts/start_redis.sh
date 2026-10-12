#!/bin/bash
# Start Redis for local testing

CONTAINER_NAME="stocksignals-redis-test"
PORT=6379

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker not found${NC}"
        echo "Please install Docker from https://www.docker.com"
        exit 1
    fi
}

case "${1:-start}" in
    start)
        echo "Starting Redis container..."

        # Check if container already exists
        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                echo -e "${YELLOW}⚠ Redis already running${NC}"
                docker ps | grep $CONTAINER_NAME
            else
                echo "Restarting existing Redis container..."
                docker start $CONTAINER_NAME
            fi
        else
            echo "Creating new Redis container..."
            docker run -d \
                -p $PORT:6379 \
                --name $CONTAINER_NAME \
                redis:7-alpine
        fi

        # Wait for Redis to be ready
        sleep 2

        if docker ps | grep -q $CONTAINER_NAME; then
            echo -e "${GREEN}✓ Redis is running${NC}"
            echo ""
            echo "Redis connection info:"
            echo "  Host: localhost"
            echo "  Port: $PORT"
            echo ""
            echo "Test connection:"
            echo "  redis-cli ping"
            echo ""
            echo "Monitor in real-time:"
            echo "  redis-cli MONITOR"
            echo ""
            echo "View dedup keys:"
            echo "  redis-cli KEYS 'dedup:signal:*'"
            echo ""
        else
            echo -e "${RED}✗ Failed to start Redis${NC}"
            exit 1
        fi
        ;;

    stop)
        echo "Stopping Redis..."
        if docker ps | grep -q $CONTAINER_NAME; then
            docker stop $CONTAINER_NAME
            echo -e "${GREEN}✓ Redis stopped${NC}"
        else
            echo -e "${YELLOW}⚠ Redis not running${NC}"
        fi
        ;;

    restart)
        echo "Restarting Redis..."
        docker stop $CONTAINER_NAME 2>/dev/null || true
        sleep 1
        docker start $CONTAINER_NAME
        sleep 2
        echo -e "${GREEN}✓ Redis restarted${NC}"
        ;;

    clean)
        echo "Removing Redis container..."
        if docker ps -a | grep -q $CONTAINER_NAME; then
            docker stop $CONTAINER_NAME 2>/dev/null || true
            docker rm $CONTAINER_NAME
            echo -e "${GREEN}✓ Redis container removed${NC}"
        else
            echo -e "${YELLOW}⚠ Redis container not found${NC}"
        fi
        ;;

    status)
        echo "Checking Redis status..."
        if docker ps | grep -q $CONTAINER_NAME; then
            echo -e "${GREEN}✓ Redis is running${NC}"
            docker ps | grep $CONTAINER_NAME
            echo ""
            redis-cli ping 2>/dev/null && echo -e "${GREEN}✓ Redis is responsive${NC}" || echo -e "${RED}✗ Redis not responding${NC}"
        else
            echo -e "${RED}✗ Redis is not running${NC}"
        fi
        ;;

    logs)
        echo "Redis logs:"
        docker logs -f $CONTAINER_NAME
        ;;

    cli)
        echo "Connecting to Redis..."
        redis-cli
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|clean|status|logs|cli}"
        echo ""
        echo "Commands:"
        echo "  start     - Start Redis container"
        echo "  stop      - Stop Redis container"
        echo "  restart   - Restart Redis container"
        echo "  clean     - Remove Redis container"
        echo "  status    - Check Redis status"
        echo "  logs      - View Redis logs"
        echo "  cli       - Open Redis CLI"
        echo ""
        exit 1
        ;;
esac
