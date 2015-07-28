__author__ = 'sweemeng'
from flask import Flask
import yaml

def create_app():
    config = yaml.load(open("config.yaml"))

    app = Flask(__name__)
    app.config["CELERY_BROKER_URL"] = config["CELERY_BROKER_URL"]
    app.config["CELERY_RESULT_BACKEND"] = config["CELERY_RESULT_BACKEND"]
    app.config["CELERY_IMPORTS"] = ("worker")
    return app