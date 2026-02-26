#!/bin/bash
# Quick test runner script

set -e

echo "================================"
echo "Volunteer Manager - Test Suite"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Backend tests
echo -e "${BLUE}Running Backend Tests...${NC}"
cd backend

echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Running unit tests..."
pytest test_app.py -v

echo ""
echo "Running advanced tests..."
pytest test_app_advanced.py -v

echo ""
echo "Generating coverage report..."
pytest test_app.py test_app_advanced.py --cov=. --cov-report=term-missing --cov-report=html

echo ""
echo -e "${GREEN}✓ Backend tests completed${NC}"
echo "Coverage report: backend/htmlcov/index.html"

echo ""
echo -e "${GREEN}================================"
echo "All tests passed!"
echo "================================${NC}"
