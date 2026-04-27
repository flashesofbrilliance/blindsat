.PHONY: test lint coverage install clean

install:
	pip install -e .[dev]

test:
	pytest -v

coverage:
	pytest -v --cov=sat_private --cov-report=term-missing --cov-fail-under=90

lint:
	ruff check .

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov dist build *.egg-info
