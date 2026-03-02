#!/bin/bash

# start nginx using default config file, which is located at /opt/homebrew/etc/nginx/nginx.conf
# brew commands:
brew services stop nginx 
brew services start nginx 

# stop nginx if it's already running
#nginx -s stop
#nginx

export N2T_SETTINGS=/$HOME/my_dev_space/n2t/dev-config.env

.venv/bin/python -m gunicorn n2t.app:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  -b 127.0.0.1:8000
