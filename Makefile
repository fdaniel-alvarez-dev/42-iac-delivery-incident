.PHONY: setup demo test lint clean

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

test: setup
	$(PY) -m unittest discover -s tests -p "test_*.py" -q
	$(PY) -m portfolio_proof validate --examples examples/passing
	@if $(PY) -m portfolio_proof validate --examples examples/failing >/dev/null; then \
		echo "ERROR: expected validate to fail on examples/failing"; \
		exit 1; \
	else \
		echo "OK: validate fails on examples/failing (as expected)"; \
	fi

clean:
	rm -rf artifacts
	find src tests -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	find src tests -name "*.pyc" -delete 2>/dev/null || true
