isort = isort src tests
black = black src tests
flake8 = flake8 src tests

.PHONY: install
install:
	pip install -U pip wheel
	pip install -U poetry
	poetry install

.PHONY: format
format:
	$(isort)
	$(black)
	$(flake8)

.PHONY: pep8
pep8:
	$(flake8)

# Build up folders strucuture corresponding to inmanta loader structure, so mypy knows what goes where.
RUN_MYPY=MYPYPATH=src python -m mypy --html-report mypy -p nfv_test_api

.PHONY: mypy
mypy:
	$(RUN_MYPY)
