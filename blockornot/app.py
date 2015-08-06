__author__ = 'sweemeng'
from flask import Flask
import yaml
import os

def create_app():
    path = os.path.dirname(__file__)
    config = yaml.load(open(os.path.join(path,"config.yaml")))

    app = Flask(__name__)
    app.config["CELERY_BROKER_URL"] = config["CELERY_BROKER_URL"]
    app.config["CELERY_RESULT_BACKEND"] = config["CELERY_RESULT_BACKEND"]
    app.config["CELERY_IMPORTS"] = ("worker")
    app.config["LOCATIONS"] = config["LOCATIONS"]
    app.config["TESTSUITES"] = config["TESTSUITES"]
    app.config["PORT"] = config["PORT"]
    app.config["DBNAME"] = config["DBNAME"]
    app.config["DBUSER"] = config["DBUSER"]
    app.config["DBPASSWD"] = config["DBPASSWD"]
    app.config["BROKER_TRANSPORT_OPTIONS"] = {'socket_timeout': 7200}
    app.config["URL"] = config["URL"]
    app.config["CALLBACK_URL"] = config["CALLBACK_URL"]
    app.config["CELERY_TASK_SERIALIZER"] = "json"
    return app