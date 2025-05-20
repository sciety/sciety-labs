FROM python:3.10-slim AS base

USER root

WORKDIR /app/sciety-labs

ENV PIP_NO_CACHE_DIR=1
COPY requirements.build.txt ./
RUN pip install --disable-pip-version-check \
    -r requirements.build.txt

COPY requirements.txt ./
RUN pip install --disable-pip-version-check \
    -r requirements.build.txt \
    -r requirements.txt

COPY requirements.dev.txt ./
RUN pip install --disable-pip-version-check \
    -r requirements.build.txt \
    -r requirements.txt \
    -r requirements.dev.txt

COPY sciety_labs ./sciety_labs
COPY static ./static
COPY templates ./templates
COPY config ./config

COPY tests ./tests
COPY .pylintrc .flake8 mypy.ini ./

CMD [ "python3", "-m", "uvicorn", "sciety_labs.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--log-config=config/logging.yaml"]
