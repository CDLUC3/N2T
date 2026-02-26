brew services restart nginx 

export N2T_SETTINGS=/Users/jjiang/my_dev_space/n2t/dev-config.env

.venv/bin/python -m gunicorn n2t.app:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  -b 127.0.0.1:8000
