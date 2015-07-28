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
    def __init__(self, task_func, param=None, task_id=None):
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

    def run(self):
        if not self.task_id:
            if type(self.param) == tuple:
                self.task = self.task_func.delay(**self.param)
            else:
                self.task = self.task_func.delay(self.param)
        else:
            self.task = self.task_func.AsyncResult(self.task_id)

        self.task_id = self.task.id
        self.output["task_id"] = self.task_id
        self.status = self.task.state

        if self.status == "SUCCESS":
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
    def __init__(self, isp, location, param=None, task_id=None):
        super(HTTPResult, self).__init__(http_task, param=param, task_id=task_id)

        # each worker will listen to 1 queue
        # each queue is named after location
        # we just use the honor system to trust that the server is running in the right location
        # TODO: make queue tagged with location ISP
        self.output["location"] = location
        self.output["ISP"] = isp
        queue_name = "%s %s" % (location, isp)
        self.queue = queue_name.lower().replace(" ","_")

    def run(self):
        if not self.task_id:
            self.task = self.task_func.apply_async(
                args=[self.param],
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
        if self.status == states.SUCCESS:
            self.output["status_code"] = self.result.status_code
            # Because error result is stored in content
            self.output["content"] = self.result.content


class DNSResult(BaseResult):
    def __init__(self, server, provider, param=None, task_id=None):
        super(DNSResult, self).__init__(dns_task, param=param, task_id=task_id)
        self.output["server"] = server
        self.output["provider"] = provider

    def prepare_result(self):
        if self.status == states.SUCCESS:
            self.output["result"] = self.result

