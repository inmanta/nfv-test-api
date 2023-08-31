isort = isort src tests
black = black src tests
flake8 = flake8 src tests

.PHONY: install
install:
	pip install -e . -r requirements.dev.txt

image:
	docker build -t inmantaci/nfv-test-api:latest .

.PHONY: format
format:
	$(isort)
	$(black)
	$(flake8)

.PHONY: pep8
pep8:
	$(flake8)

.PHONY: mypy
mypy:
	MYPYPATH=src python -m mypy --html-report mypy -p nfv_test_api
	MYPYPATH=src python -m mypy --html-report mypy -p pytest_nfv_test_api
	MYPYPATH=. python -m mypy --html-report mypy tests
