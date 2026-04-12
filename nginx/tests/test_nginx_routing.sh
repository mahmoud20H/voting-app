#!/bin/bash

# Configuration
BASE_URL="http://localhost"
TIMEOUT=5

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "--- Nginx Routing Verification Tests ---"

# Test 1: Root path (Vote App)
echo -n "Test 1: Root path (Vote App) -> "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/)
if [[ "$STATUS" == "302" || "$STATUS" == "200" ]]; then
    echo -e "${GREEN}PASS${NC} (Status: $STATUS)"
else
    echo -e "${RED}FAIL${NC} (Status: $STATUS)"
fi

# Test 2: Results path
echo -n "Test 2: Results path (Result App) -> "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/results)
if [ "$STATUS" == "301" ]; then
    echo -e "${GREEN}PASS${NC} (Status: 301 Redirect)"
else
    echo -e "${RED}FAIL${NC} (Status: $STATUS)"
fi

# Test 3: Auth Verify path
echo -n "Test 3: Auth Verify path -> "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/auth/verify)
if [ "$STATUS" == "401" ]; then
    echo -e "${GREEN}PASS${NC} (Status: 401 Unauthorized)"
else
    echo -e "${RED}FAIL${NC} (Status: $STATUS)"
fi

# Test 4: WebSocket Support
echo -n "Test 4: WebSocket Upgrade Header -> "
STATUS=$(curl -s -I -H "Upgrade: websocket" -H "Connection: Upgrade" $BASE_URL/socket.io/?transport=websocket | grep -i "101 Switching Protocols")
if [ ! -z "$STATUS" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    # Fallback check if result app isn't fully ready
    echo -e "${RED}SKIP/FAIL${NC} (Check if service is running)"
fi

echo "---------------------------------------"
echo "Tests completed."
