# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

LABEL org.opencontainers.image.title="IntentLock" \
      org.opencontainers.image.description="Proof-of-intent authorization gateway for AI agents" \
      org.opencontainers.image.version="4.0.0" \
      org.opencontainers.image.vendor="IntentLock" \
      org.opencontainers.image.licenses="Proprietary"

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install .


FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

LABEL org.opencontainers.image.title="IntentLock" \
      org.opencontainers.image.description="Proof-of-intent authorization gateway for AI agents" \
      org.opencontainers.image.version="4.0.0" \
      org.opencontainers.image.vendor="IntentLock" \
      org.opencontainers.image.licenses="Proprietary" \
      org.opencontainers.image.base.image="python:3.11-slim-bookworm"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system intentlock \
    && useradd --system --gid intentlock --create-home intentlock \
    && mkdir -p /tmp/intentlock \
    && chown intentlock:intentlock /tmp/intentlock \
    && chmod 700 /tmp/intentlock

COPY --from=builder /opt/venv /opt/venv
COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config

RUN chown -R intentlock:intentlock /app && \
    mkdir -p /app/logs && \
    chown -R intentlock:intentlock /app/logs && \
    # Verify no secrets were copied into the image
    ( \
      grep -r -i -E "(password|secret|key|token|api_key)" /app/config /app/app 2>/dev/null \
      | grep -v -E "(\"secret\"|'secret'|SECRET_KEY|jwt_secret_key|EXAMPLE|sample|placeholder)" \
      && echo "WARNING: Possible secrets found in application files" && exit 1 \
    ) || true

USER intentlock

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
