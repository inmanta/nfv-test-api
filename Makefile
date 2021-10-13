.PHONY: build clean
VERSION := $(shell poetry version | cut -f 2 -d " ")
RPMDIR := $(shell pwd)/rpms
isort = isort src tests
black = black src tests
flake8 = flake8 src tests

build:
	poetry build

clean:
	rm -rf build dist *.egg-info rpms

rpm: build
	rm -rf rpms/*
	mock -r epel-7-x86_64 -D "pyversion ${VERSION}" --buildsrpm --spec nfv-test-api.spec --sources dist --resultdir rpms
	mock -r epel-7-x86_64 -D "pyversion ${VERSION}" --rebuild rpms/nfv-test-api-*.src.rpm --resultdir rpms

upload: RPM := $(shell basename ${RPMDIR}/nfv-test-api-${VERSION}-*.x86_64.rpm)

upload:
	@echo Uploading $(RPM)
	ssh repomanager@artifacts.ii.inmanta.com "/usr/bin/repomanager --config /etc/repomanager.toml --repo nfv-test-api --distro el7 --file - --file-name ${RPM}" < ${RPMDIR}/${RPM}

.PHONY: format
format:
	$(isort)
	$(black)
	$(flake8)

.PHONY: pep8
pep8:
	flake8 nfv-test-api tests

# Build up folders strucuture corresponding to inmanta loader structure, so mypy knows what goes where.
RUN_MYPY=MYPYPATH=src python -m mypy --html-report mypy -p nfv_test_api

.PHONY: mypy
mypy:
	$(RUN_MYPY)
