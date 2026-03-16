# ---- Base image ----
FROM python:3.12-slim

# Install nginx
RUN apt-get update && \
    apt-get install -y nginx curl git && \
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

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Remove default nginx site
RUN rm -f /etc/nginx/sites-enabled/default

# Create log + run directories
RUN mkdir -p /var/run/nginx

# Document the exposed port (nginx default port)
EXPOSE 18880

# Create data directory for sqlite db
RUN mkdir -p /app/data

RUN python n2t -c dev-config.env loaddb

ENV N2T_SETTINGS=/app/dev-config.env

# Startup script
COPY start_n2t_docker.sh start_n2t_docker.sh
RUN chmod +x start_n2t_docker.sh

CMD ["./start_n2t_docker.sh"]