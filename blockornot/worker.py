__author__ = 'sweemeng'
from app import create_app
from celery import Celery
import requests
import logging
import subprocess
import re

app = create_app()

backend = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
backend.conf.update(app.config)

# TODO: make it easy for people to expand test. We probably going to use zope.interface on this.
# TODO: Store result into mongo. Since this runs on client.
# TODO: On the other hand putting mongodb dependency is a bad idea

# Redis support routing. we just assign each instance with it's own queue celery -A worker.backend worker -Q japan
# The hard part is assigning metadata based on queue name, we probably use a trust system and put it in a config file
@backend.task
def http_task(url):
    r = requests.get(url)
    return r

# TODO: What other error in DNS again?/
@backend.task
def dns_task(url, dns_server=None):
    command = ["dig", url]
    if dns_server:
        server = "@%s" % dns_server
        command.append(server)
    p = subprocess.check_output(command)
    if re.search("NXDOMAIN", p):
        return "Not Found"
    if re.search("NOERROR", p):
        return "Resolved properly"

