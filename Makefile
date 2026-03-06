.PHONY: setup demo test lint test-demo test-production clean

PY := python3

export PYTHONPATH := src

setup:
	@$(PY) -c 'import sys; assert sys.version_info >= (3,11), sys.version'
	@mkdir -p artifacts
	@$(PY) -V

demo: setup
	$(PY) -m portfolio_proof report --examples examples/failing --out artifacts

lint: setup
	$(PY) -m compileall -q src tests

test: test-demo

test-demo: setup
	TEST_MODE=demo $(PY) tests/run_tests.py

test-production: setup
	TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 $(PY) tests/run_tests.py

clean:
	rm -rf artifacts
	find src tests -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	find src tests -name "*.pyc" -delete 2>/dev/null || true
