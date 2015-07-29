__author__ = 'sweemeng'
from app import create_app
from celery import Celery
import requests
import logging
import subprocess
import re
import dns
import dns.resolver
import dns.exception

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
def http_task(url):
    r = requests.get(url)
    status_code = r.status_code
    reason = r.reason
    if r.status_code == 200:

        if MCMC_BLOCK_PAGE_HEADER.search(r.content):
            if MCMC_BLOCK_PAGE_PATTERN.search(r.content):
                status_code = 451
                reason = "Unavailable For Legal Reasons"

    result = (status_code, r.content, reason)
    return result

# TODO: Local ISP DNS will resolve to wrong IP.
@backend.task
def dns_task(url, dns_server=None):
    resolver = dns.resolver.Resolver()
    reason = ""
    status = ""
    if dns_server:
        resolver.nameservers = [dns_server]
    try:
        answer = resolver.query(url)
        for entry in answer:
            ip = entry.to_text()
            r = requests.get("http://%s" % ip, headers={"Host":url})

            if r.status_code == 200:

                if MCMC_BLOCK_PAGE_HEADER.search(r.content):
                    if MCMC_BLOCK_PAGE_PATTERN.search(r.content):
                        reason = "Unavailable For Legal Reasons"
                        status = "Error"
                else:
                    reason = "Content resolved properly"
                    status = "OK"

    except dns.resolver.NXDOMAIN as e:
        status = "NXDOMAIN"
        reason = "Domain cannot be resolved"

    except dns.resolver.Timeout:
        status = "Timeout"
        reason = "Timed out trying to resolve %s" % url

    except dns.exception.DNSException:
        status = "Error"
        reason = "Unhandled reception, bug the guys to find out"

    return (status, reason)