from uvicorn.workers import UvicornWorker

class MyUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "log_config": "uvicorn_log_config.json",
    }

worker_class = MyUvicornWorker
workers = 4
bind = "0.0.0.0:18880"
accesslog = "-"
errorlog = "-"
loglevel = "info"