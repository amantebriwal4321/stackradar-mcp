FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STACKRADAR_HOST=0.0.0.0 \
    STACKRADAR_PORT=8741 \
    STACKRADAR_MODE=auto \
    STACKRADAR_CACHE_DIR=/tmp/stackradar-cache

COPY pyproject.toml README.md LICENSE requirements.txt ./
COPY stackradar_mcp ./stackradar_mcp
RUN pip install --no-cache-dir .

EXPOSE 8741
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8741/health')"

CMD ["stackradar-mcp"]
