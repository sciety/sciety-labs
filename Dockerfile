FROM python:3.12-slim AS base

USER root

WORKDIR /app/sciety-labs

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /bin/uv

# The venv on PATH keeps `python3 -m uvicorn` (the CMD below) and
# `docker compose run --rm sciety-labs python -m pytest` (the Makefile) working
# without naming it. UV_PYTHON_DOWNLOADS=never pins us to the base image's
# interpreter instead of provisioning another one.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/sciety-labs/.venv/bin:$PATH"

# --locked, not --frozen: a dependency edit that left uv.lock stale must fail the
# build rather than silently re-resolve. Dev dependencies are included, because
# `make lint` and `make unittest` run inside this image.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

COPY sciety_labs ./sciety_labs
COPY static ./static
COPY templates ./templates
COPY config ./config

COPY tests ./tests
COPY .pylintrc .flake8 mypy.ini ./

CMD [ "python3", "-m", "uvicorn", "sciety_labs.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--log-config=config/logging.yaml"]
