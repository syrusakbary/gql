.PHONY: clean tests docs

SRC_PYTHON := gql tests scripts/gql-cli docs/code_examples

dev-setup:
	python pip install -e ".[test]"

tests:
	pytest tests --cov=gql --cov-report=term-missing -vv

all_tests:
	pytest tests --cov=gql --cov-report=term-missing --run-online -vv

check:
	isort --recursive $(SRC_PYTHON)
	black $(SRC_PYTHON)
	flake8 $(SRC_PYTHON)
	mypy $(SRC_PYTHON)
	check-manifest

docs:
	rm -rf ./docs/_build
	cd docs; make html

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" | xargs -I {} rm -rf {}
	rm -rf ./htmlcov
	rm -rf ./.mypy_cache
	rm -rf ./.pytest_cache
	rm -rf ./.tox
	rm -rf ./gql.egg-info
	rm -rf ./dist
	rm -rf ./build
	rm -rf ./docs/_build
	rm -f ./.coverage
