# ---- Base image ----
FROM python:3.12-slim

# Install nginx
RUN apt-get update && \
    apt-get install -y nginx curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy entire project FIRST (because of -e .)
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Remove default nginx site
RUN rm -f /etc/nginx/sites-enabled/default

# Create log + run directories
RUN mkdir -p /var/run/nginx

# Expose port
EXPOSE 8000

RUN python n2t -c dev-config-docker.env loaddb

ENV N2T_SETTINGS=/app/dev-config-docker.env

# Startup script
RUN chmod +x start_n2t_docker.sh

CMD ["./start_n2t_docker.sh"]