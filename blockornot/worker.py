__author__ = 'sweemeng'
from app import create_app
from celery import Celery
from celery import states
import requests
import logging
import subprocess
import re
import dns
import dns.resolver
import dns.exception
import utils
import urlparse
from models import db
from models import ResultData
import json

app = create_app()

backend = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
backend.conf.update(app.config)

MCMC_BLOCK_PAGE_PATTERN = re.compile(r"This website is not available in Malaysia as it violates")
MCMC_BLOCK_PAGE_HEADER = re.compile(r"Makluman/Notification")

# TODO: make it easy for people to expand test. We probably going to use zope.interface on this.
# TODO: How do we create a runnable object anyway?

# Redis support routing. we just assign each instance with it's own queue celery -A worker.backend worker -Q japan
# The hard part is assigning metadata based on queue name, we probably use a trust system and put it in a config file
# This should do ore than just running it slowly in the background. it is humiliating
@backend.task
def initialize_entry(data, extra_attr={}):
    db.connect()
    # This should save the data
    result_data = ResultData.from_json(data, extra_attr=extra_attr)
    return result_data.to_json()

# I'm lazy so I pass the whole dictionary
@backend.task
def call_http_task(data):
    print data
    print data
    try:
        r = requests.get(data["url"])
    except requests.ConnectionError as e:
        status_code, message = e.message
        return {
            "task_id": data["task_id"],
            "status_code": status_code,
            "content": str(message),
            "reason": str(message),
            "status": states.FAILURE
        }

    status_code = r.status_code
    reason = r.reason
    if r.status_code == 200:

        if MCMC_BLOCK_PAGE_HEADER.search(r.content):
            if MCMC_BLOCK_PAGE_PATTERN.search(r.content):
                status_code = 451
                reason = "Unavailable For Legal Reasons"

    if status_code != 200:
        status = states.FAILURE
    else:
        status = states.SUCCESS
    result = {
        "task_id": data["task_id"],
        "status_code": status_code,
        "content":r.content,
        "reason": reason,
        "status": status
    }


    return result

@backend.task
def call_dns_task(data):
    url = data["url"]
    if not re.match(r"^http://", url):
        url = "http://%s" % url
    parsed_url = urlparse.urlparse(url)
    url = parsed_url.netloc
    resolver = dns.resolver.Resolver()
    reason = ""
    status = ""
    if data["extra_attr"].get("server"):
        resolver.nameservers = [data["extra_attr"]["server"]]
    try:
        answer = resolver.query(url)
        if answer:
            reason = "Content resolved properly"
            status = "OK"
        else:
            reason = "Interesting, there is no answer for this DNS Query"
            status = "Error"

    except dns.resolver.NXDOMAIN as e:
        status = "NXDOMAIN"
        reason = "Domain cannot be resolved"

    except dns.resolver.Timeout:
        status = "Timeout"
        reason = "Timed out trying to resolve %s" % url

    except dns.exception.DNSException:
        status = "Error"
        reason = "Unhandled reception, bug the guys to find out"

    if status != "OK":
        task_status = states.FAILURE
    else:
        task_status = states.SUCCESS

    result = {
        "task_id": data["task_id"],
        "status": task_status,
        "status_code": status,
        "reason": reason
    }
    return result


@backend.task
def call_full_request_task(data):
    url = data["url"]
    if not re.match(r"^http://", url):
        url = "http://%s" % url
    parsed_url = urlparse.urlparse(url)
    url = parsed_url.netloc
    resolver = dns.resolver.Resolver()
    reason = ""
    status = ""
    if data["extra_attr"].get("server"):
        resolver.nameservers = [data["extra_attr"]["server"]]
    try:
        answer = resolver.query(url)
        for entry in answer:
            ip = entry.to_text()
            r = requests.get("http://%s" % ip, headers={"Host":url})

            if r.status_code == 200:

                if MCMC_BLOCK_PAGE_HEADER.search(r.content):
                    if MCMC_BLOCK_PAGE_PATTERN.search(r.content):
                        reason = "Unavailable For Legal Reasons"
                        status = 451
                else:
                    reason = r.reason
                    status = r.status_code
            else:
                status = r.status_code
                reason = r.reason

    except dns.resolver.NXDOMAIN as e:
        status = "NXDOMAIN"
        reason = "Domain cannot be resolved"

    except dns.resolver.Timeout:
        status = "Timeout"
        reason = "Timed out trying to resolve %s" % url

    except dns.exception.DNSException:
        status = "Error"
        reason = "Unhandled reception, bug the guys to find out"

    if status != 200:
        task_status = states.FAILURE
    else:
        task_status = states.SUCCESS

    result = {
        "task_id": data["task_id"],
        "status": task_status,
        "status_code": status,
        "reason": reason
    }
    return result

@backend.task
def call_http_dpi_tampering_task(data):
    url = data["url"]

    if not re.match(r"^http\://", url):
        url = "http://%s" % url
    url_components = urlparse.urlparse(url)
    check = utils.HttpDPITamperingCheck()
    status, reason = check.run_all(url_components.netloc, path=url_components.path)

    if status:
        task_status = states.SUCCESS
    else:
        task_status = states.FAILURE

    result = {
        "task_id": data["task_id"],
        "status": task_status,
        "status_code": status,
        "reason": reason
    }
    return result

@backend.task
def update_entry(data):
    # Do not rely that connection will be kept running.
    # If it is known to last as long as the task, just make it global
    logging.warn("Updating database")
    print data
    db.connect()
    result_data = ResultData.get(task_id=data["task_id"])
    result_data.status = data["status_code"]
    result_data.task_status = data["status"]
    result_data.reason = data["reason"]
    result_data.save()
    return result_data.to_json()

@backend.task
def post_update(data):
    url = "%s/postback" % app.config["CALLBACK_URL"]
    logging.warn(url)
    r = requests.post(url, data=json.dumps(data))
