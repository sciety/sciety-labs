FROM python:3.8 AS base

USER root

WORKDIR /app/sciety-discovery

COPY requirements.build.txt ./
RUN pip install --disable-pip-version-check -r requirements.build.txt

COPY requirements.txt ./
RUN pip install --disable-pip-version-check -r requirements.txt

COPY requirements.dev.txt ./
RUN pip install --disable-pip-version-check -r requirements.dev.txt

COPY sciety_discovery ./sciety_discovery
COPY static ./static
COPY templates ./templates

COPY tests ./tests
COPY .pylintrc .flake8 mypy.ini ./

CMD [ "python3", "-m", "uvicorn", "sciety_discovery.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
