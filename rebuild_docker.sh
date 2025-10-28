#!/bin/bash
# Quick script to rebuild Docker with the rate limiter fix
# Run this to apply the fix and resolve 429 errors

set -e  # Exit on error

echo "==============================================="
echo " Docker Rebuild Script - Rate Limiter Fix"
echo "==============================================="
echo ""

echo "[1/4] Stopping Docker containers..."
docker-compose down
echo "     Done!"
echo ""

echo "[2/4] Rebuilding with no cache..."
echo "     This may take 2-3 minutes..."
docker-compose build --no-cache
echo "     Done!"
echo ""

echo "[3/4] Starting containers..."
docker-compose up -d
echo "     Done!"
echo ""

echo "[4/4] Waiting for application to start..."
sleep 5
echo "     Done!"
echo ""

echo "==============================================="
echo " Rebuild Complete!"
echo "==============================================="
echo ""
echo "Next steps:"
echo "  1. Clear your browser cache (Ctrl+Shift+Delete)"
echo "  2. Go to http://127.0.0.1:5000"
echo "  3. Login and test sending messages"
echo "  4. No more 429 errors!"
echo ""
echo "To watch logs:"
echo "  docker-compose logs -f module-prices-agent"
echo ""
echo "Press Ctrl+C to exit, or wait 3 seconds to view logs..."
sleep 3

docker-compose logs -f module-prices-agent
