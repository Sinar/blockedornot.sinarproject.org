__author__ = 'sweemeng'
from flask import Flask


app = Flask(__name__)
app.config["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
app.config["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"
app.config["CELERY_IMPORTS"] = ("worker")


