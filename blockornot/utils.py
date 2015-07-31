__author__ = 'sweemeng'
import time
import argparse

from socket import socket, IPPROTO_TCP, TCP_NODELAY, timeout, gethostbyname, \
    getprotobyname, AF_INET, SOL_IP, SOCK_RAW, SOCK_DGRAM, IP_TTL, gethostbyaddr, error, getaddrinfo, SOL_TCP

from models import ResultData



class target:
    pass

SUCCESS = True
FAIL = False

# This test essentially test for timeout but not http code.
class HttpDPITamperingCheck:
    def simple_check(self, host, path="/"):
        print "## Test 1: Check DNS, and IP block: Testing Same IP, different Virtual Host"
        s = socket()
        s.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        s.connect((host, 80))
        path_str = "GET %s HTTP/1.1\r\n\r\n" % path
        s.send(path_str)
        try:
            print s.recv(4096)
            return SUCCESS
        except timeout:
            print "Timeout -- waited 5 seconds\n"
            return FAIL

    def browser_emulation_check(self, host, path="/"):
        print "## Test 2: Emulating a real web browser: Testing Same IP, actual Virtual Host, single packet"
        s = socket()
        s.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        s.connect((host, 80))
        path_str = "GET %s HTTP/1.1\r\nHost: %s\r\n\r\n" % (path, host)
        s.send(path_str)
        # five seconds ought to be enough
        s.settimeout(5)
        try:
            print s.recv(4096)
            return SUCCESS
        except timeout:
            print "Timeout -- waited 5 seconds\n"
            return FAIL

    def packet_fragmentation_check(self, host, path="/"):
        print "## Test 3: Attempting to fragment: Testing Same IP, actual Virtual Host, fragmented packet"
        s = socket()
        s.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        s.connect((host, 80))
        path_str = "GET %s HTTP/1.1\r\n" % path
        s.send(path_str)
        # Sleep for a bit to ensure that the next packets goes through separately.
        # Not sure if we actually need it. Reducing it from 0.2 to 0.1 seconds
        time.sleep(0.1)
        s.send("Host: " + host[0:2])
        time.sleep(0.1)
        s.send(host[2:] + "\r\n\r\n")
        try:
            print s.recv(4096)
            return SUCCESS
        except timeout:
            print "Timeout -- waited 5 seconds\n "
            return FAIL

    def run_single(self, host, path="/"):
        simple_ok = self.simple_check(host, path)
        browser_ok = self.browser_emulation_check(host, path)
        packat_frag_ok = self.packet_fragmentation_check(host, path)

        if all([simple_ok, browser_ok, packat_frag_ok]):
            return SUCCESS
        return FAIL

    def run_all(self, host, path="/"):
        ips = socket_getips(host)
        results = []
        if len(ips) > 0:

            for i in ips:
                if self.run_single(i, path) == FAIL:
                    results.append(i)
        else:
            return (FAIL, "Cannot find ip for this address")
        if results:
            ips_str = ", ".join(ips)
            message = "Request to the following ip %s, have been tampered with" % ips_str
            return (FAIL, message)
        else:
            return (SUCCESS, "No tampering of http request found.")


def socket_getips(host, port=80):
    """
    See http://docs.python.org/2/library/socket.html#socket.getaddrinfo
    """
    addrs = getaddrinfo(host, port, 0, 0, SOL_TCP)
    result = []
    for addr in addrs:
        sockaddr = addr[4]
        if (addr[0] == 2):
            # We take IPv4 addresses only. IPv6 will be ignored for now
            result.append(sockaddr[0])
    return result

# I do this so that I can autocomplete the code.
def store_to_db(data, task_type, task_status, url=None, task_id=None, status=None, extra_attr=None):
    create = False
    try:
        if task_id:
            result = ResultData.get(task_id=task_id)
        else:
            create = True

    except ResultData.DoesNotExist:
        create = True

    if create:
        result = ResultData()
        result.transaction_id = data["transaction_id"]
        result.task_id = task_id
        result.task_type = task_type
        result.location = data["location"]
        result.country = data["country"]
        result.url = url

        if extra_attr:
            result.status = extra_attr

    result.task_status = task_status

    if status:
        # Difference between status and task_status. task_status is for celery task.
        result.status = status

    result.raw_data = data
    result.save()