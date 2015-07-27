__author__ = 'sweemeng'
from app import app
from celery import Celery
import requests
import logging
import subprocess
import re


backend = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
backend.conf.update(app.config)

# TODO: how do we broadcast task all working running this task
# TODO: how do we tag country/isp for this result
# TODO: if we were to give the script to run on volunteers computer, can they use the rabbitmq server?
@backend.task
def http_task(url):
    r = requests.get(url)
    return r

# TODO: What other error in DNS again?
# TODO: Do test with other DNS IP such as from different ISP
@backend.task
def dns_task(url):
    command = ["dig", url]
    p = subprocess.check_output(command)
    if re.search("NXDOMAIN", p):
        return "Not Found"
    if re.search("NOERROR", p):
        return "Resolved properly"

