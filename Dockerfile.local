# ---- Base image ----
FROM python:3.12-slim

# Install nginx
RUN apt-get update && \
    apt-get install -y curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
COPY pyproject.toml .
COPY uv.lock .
COPY n2t ./n2t
COPY schemes ./schemes
COPY tests ./tests
COPY dev-config.env .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 18880

# Create data directory for sqlite db
RUN mkdir -p /app/data

RUN python n2t -c dev-config.env loaddb

ENV N2T_SETTINGS=/app/dev-config.env

CMD ["gunicorn", "n2t.app:app", \
    "-k", "uvicorn.workers.UvicornWorker", \
    "--workers", "4", \
    "--bind", "0.0.0.0:18880"]