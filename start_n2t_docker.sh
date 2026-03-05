#!/bin/sh

# Start nginx
nginx

# Start FastAPI via Gunicorn
exec gunicorn n2t.app:app \
    -k uvicorn.workers.UvicornWorker \
    --workers 3 \
    --bind 127.0.0.1:8000