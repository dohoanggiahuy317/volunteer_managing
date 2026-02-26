.PHONY: test test-backend test-coverage test-watch help

help:
	@echo "Available test commands:"
	@echo "  make test              - Run all tests"
	@echo "  make test-backend      - Run backend tests"
	@echo "  make test-coverage     - Run tests with coverage report"

# All tests
test: test-backend
	@echo "✓ All tests completed"

# Backend tests
test-backend:
	@echo "Running backend tests..."
	cd backend && pip install -q -r requirements.txt && pytest test_app.py test_app_advanced.py -v

test-backend-fast:
	@echo "Running backend tests (without advanced)..."
	cd backend && pytest test_app.py -v

test-backend-watch:
	@echo "Running backend tests in watch mode..."
	cd backend && pytest-watch test_app.py

# Coverage reports
test-coverage:
	@echo "Generating coverage reports..."
	cd backend && pip install -q -r requirements.txt && pytest test_app.py test_app_advanced.py --cov=. --cov-report=html --cov-report=term-missing
	@echo "Backend coverage: backend/htmlcov/index.html"

# Specific test suites
test-backend-user:
	@echo "Running user management tests..."
	cd backend && pytest test_app.py::TestUserManagement -v

test-backend-pantry:
	@echo "Running pantry assignment tests..."
	cd backend && pytest test_app.py::TestPantryAssignment -v

test-backend-shifts:
	@echo "Running shift management tests..."
	cd backend && pytest test_app.py::TestShifts -v

test-backend-edge-cases:
	@echo "Running edge case tests..."
	cd backend && pytest test_app_advanced.py::TestEdgeCases -v

# Lint and format
lint-backend:
	@echo "Linting backend..."
	cd backend && pip install -q -r requirements.txt && python -m py_compile app.py test_app.py test_app_advanced.py

lint-frontend:
	@echo "Linting frontend..."
	cd frontend && npm install --silent && npm run lint 2>/dev/null || echo "Lint configuration not found"

# Clean
clean:
	@echo "Cleaning test artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name .coverage -delete 2>/dev/null || true
	find . -type d -name node_modules/.vitest -exec rm -rf {} + 2>/dev/null || true

# Test a specific backend test by name
# Usage: make test-backend-one TEST=test_super_admin_can_assign_pantry
test-backend-one:
	@cd backend && pytest test_app.py test_app_advanced.py -k "$(TEST)" -v
