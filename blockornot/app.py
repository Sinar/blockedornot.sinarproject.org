__author__ = 'sweemeng'
from flask import Flask
import yaml

def create_app():
    config = yaml.load(open("config.yaml"))

    app = Flask(__name__)
    app.config["CELERY_BROKER_URL"] = config["CELERY_BROKER_URL"]
    app.config["CELERY_RESULT_BACKEND"] = config["CELERY_RESULT_BACKEND"]
    app.config["CELERY_IMPORTS"] = ("worker")
    app.config["LOCATIONS"] = config["LOCATIONS"]
    app.config["DNS_TARGETS"] = config["DNS_TARGETS"]
    app.config["TESTSUITES"] = config["TESTSUITES"]
    app.config["PORT"] = config["PORT"]
    app.config["DBUSER"] = config["DBUSER"]
    app.config["DBPASSWD"] = config["DBPASSWD"]
    return app