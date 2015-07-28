__author__ = 'sweemeng'
from app import create_app
from celery import states
from worker import http_task
from worker import dns_task
import logging

app = create_app()

# TODO: Reduce the redirection. What the fuck man...
# This is the result object
class ResultException(Exception):
    pass

class BaseResult(object):
    def __init__(self, isp, location, task_func, test_id, param=None, task_id=None):
        if not (param or task_id):
            raise ResultException("Either supply Parameter or Task ID ")
        self.config = app.config
        self.task_id = task_id
        self.result = None
        self.param = param
        self.task_func = task_func
        self.task = None
        self.status = None
        self.output = {}
        # this is for used by frontend to send data to.
        # TODO: Refactor this, tight coupling suck
        self.test_id = test_id

        # each worker will listen to 1 queue
        # each queue is named after location
        # we just use the honor system to trust that the server is running in the right location
        self.output["location"] = location
        self.output["ISP"] = isp
        queue_name = "%s %s" % (location, isp)
        self.queue = queue_name.lower().replace(" ","_")
        self.output["test_id"] = self.test_id

    def run(self):
        if not self.task_id:
            if type(self.param) == tuple or type(self.param) == list:
                param = self.param
            else:
                param = [self.param]

            self.task = self.task_func.apply_async(
                args=param,
                queue=self.queue
            )
            self.task_id = self.task.id

        else:
            self.task = self.task_func.AsyncResult(self.task_id)
        self.output["task_id"] = self.task_id
        self.status = self.task.state
        if self.status == states.SUCCESS:
            self.result = self.task.get()

    def prepare_result(self):
        raise NotImplementedError()

    def to_json(self):
        logging.warn(self.result)
        self.prepare_result()
        if self.status == states.PENDING:
            self.output["status"] = states.PENDING
        elif self.status == states.SUCCESS:
            self.output["status"] = states.SUCCESS
        else:
            self.output["status"] = states.FAILURE
        return self.output


class HTTPResult(BaseResult):
    def __init__(self, isp, location, test_id, param=None, task_id=None):
        super(HTTPResult, self).__init__(isp, location, http_task, test_id, param=param, task_id=task_id)

    def prepare_result(self):
        if self.status == states.SUCCESS:
            self.output["status_code"] = self.result.status_code
            # Because error result is stored in content
            self.output["content"] = self.result.content


class DNSResult(BaseResult):
    def __init__(self, isp, location, server, provider, test_id, param=None, task_id=None, pos=0):
        super(DNSResult, self).__init__(isp, location, dns_task, test_id, param=param, task_id=task_id)
        self.output["server"] = server
        self.output["provider"] = provider
        # Position of server in TESTSUITES config. Used in html table for javascript.
        self.output["pos"] = pos

    def prepare_result(self):
        if self.status == states.SUCCESS:
            self.output["result"] = self.result

