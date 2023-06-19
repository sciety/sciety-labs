DOCKER_COMPOSE_DEV = docker-compose
DOCKER_COMPOSE_CI = docker-compose -f docker-compose.yml
DOCKER_COMPOSE = $(DOCKER_COMPOSE_DEV)

VENV = venv
PIP = $(VENV)/bin/pip
PYTHON = $(VENV)/bin/python

DOCKER_RUN = $(DOCKER_COMPOSE) run --rm sciety-labs
DOCKER_PYTHON = $(DOCKER_RUN) python

ARGS =
PYTEST_WATCH_MODULES = tests/unit_tests

venv-clean:
	@if [ -d "$(VENV)" ]; then \
		rm -rf "$(VENV)"; \
	fi


venv-create:
	python3 -m venv $(VENV)


venv-activate:
	chmod +x venv/bin/activate
	bash -c "venv/bin/activate"


dev-install:
	$(PIP) install --disable-pip-version-check \
		-r requirements.build.txt \
		-r requirements.txt \
		-r requirements.dev.txt


dev-venv: venv-create dev-install


dev-flake8:
	$(PYTHON) -m flake8 sciety_labs tests

dev-pylint:
	$(PYTHON) -m pylint sciety_labs tests

dev-mypy:
	$(PYTHON) -m mypy sciety_labs tests


dev-lint: dev-flake8 dev-pylint dev-mypy


dev-unittest:
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/unit_tests

dev-watch:
	$(PYTHON) -m pytest_watch -- -p no:cacheprovider $(ARGS) $(PYTEST_WATCH_MODULES)

dev-test: dev-lint dev-unittest


dev-start:
	TWITTER_API_AUTHORIZATION_FILE_PATH=.secrets/twitter_api_authorization.txt \
	$(PYTHON) -m uvicorn \
		sciety_labs.app.main:create_app \
		--reload \
		--factory \
		--host 127.0.0.1 \
		--port 8000 \
		--log-config=config/logging.yaml


check-or-reload-data:
	curl \
		--fail-with-body \
		--request POST \
		http://localhost:8000/api/check-or-reload-data


build:
	$(DOCKER_COMPOSE) build sciety-labs

flake8:
	$(DOCKER_PYTHON) -m flake8 sciety_labs tests

pylint:
	$(DOCKER_PYTHON) -m pylint sciety_labs tests

mypy:
	$(DOCKER_PYTHON) -m mypy sciety_labs tests


lint: flake8 pylint mypy


unittest:
	$(DOCKER_PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/unit_tests

watch:
	$(DOCKER_PYTHON) -m pytest_watch -- -p no:cacheprovider $(ARGS) $(PYTEST_WATCH_MODULES)

test: lint unittest


start:
	$(DOCKER_COMPOSE) up -d


stop:
	$(DOCKER_COMPOSE) down


logs:
	$(DOCKER_COMPOSE) logs -f

docker-push:
	$(DOCKER_COMPOSE) push sciety-labs


ci-build-and-test:
	$(MAKE) DOCKER_COMPOSE="$(DOCKER_COMPOSE_CI)" \
		build test

ci-clean:
	$(DOCKER_COMPOSE_CI) down -v
