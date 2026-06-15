FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @byreal-io/byreal-cli @byreal-io/byreal-perps-cli \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY service/requirements.txt /app/service/requirements.txt
RUN pip install --no-cache-dir -r /app/service/requirements.txt

COPY . /app

ENV PYTHONPATH=/app/service/server
WORKDIR /app/service/server

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "from byreal_cli import check_cli_health; import sys; sys.exit(0 if check_cli_health().get('ok') else 1)" || exit 1

CMD ["python", "main.py"]
