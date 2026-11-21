# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

FROM ${PYTHON_IMAGE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
# Build tools stay out of the runtime image (some dependencies may ship sdists).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/python -m pip install -r /tmp/requirements.txt \
    && /opt/venv/bin/python -m pip check

FROM ${PYTHON_IMAGE} AS runtime
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/appuser \
    XDG_CACHE_HOME=/tmp/cache \
    HF_HOME=/tmp/huggingface
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /bin/bash appuser \
    && mkdir /app \
    && chown appuser:appuser /app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=appuser:appuser . /app
USER appuser
# No application entry point exists yet. This is a build/smoke-test default.
# API, UI and worker commands will be wired when their modules are implemented.
CMD ["python", "--version"]
