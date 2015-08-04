__author__ = 'sweemeng'
from playhouse.postgres_ext import *
from app import create_app
from celery import states
import datetime

app = create_app()

db = PostgresqlExtDatabase(app.config["DBNAME"], user=app.config["DBUSER"], password=app.config["DBPASSWD"])


class ResultData(Model):
    # Technically both is a uuid, but the field accept a uuid module,
    # Transaction id is generated when a query is launched. There should be a multiple of these
    transaction_id = CharField()
    # This should unique to task/test being done
    task_id = CharField()
    task_type = CharField()
    location = CharField()
    country = CharField()
    url = CharField()
    isp = CharField()
    task_status = CharField()
    # This is for additional attribute that don't exist in other test. Such as DNS server and DNS provider
    extra_attr = JSONField(null=True)
    # Because DNS return a text i.e NXDOMAIN, and http return code i.e 200. Number don't matter anyway
    status = CharField(null=True)
    # Making data easily queriable in SQL, few lines of code. the ability to get the raw data, priceless.
    # And there is attribute that is unique to some test for example DNS server and provider.
    raw_data = JSONField()
    reason = CharField(null=True)
    description = CharField(null=True)
    # Not part of json
    # This is only created but never change
    created_at = DateTimeField(default=datetime.datetime.now)
    # This is create then updated
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db

    @classmethod
    def from_json(cls, data, extra_attr={}):
        result = cls()
        result.transaction_id = data["transaction_id"]
        # TODO: If task_id don't exist?
        result.task_id = data["task_id"]
        # TODO: Also standardize name
        result.task_type = data["test_type"]
        result.location = data["location"]
        result.country = data["country"]
        result.isp = data["ISP"]
        result.url = data["url"]
        # Standardize on celery convention
        result.task_status = states.PENDING
        if extra_attr:
            # Make it slightly easier to query dns server and what not
            result.extra_attr = extra_attr
        # We still need raw data, because we keep adding stuff on it.
        # This will be the real result I think
        result.raw_data = data
        result.description = data["description"]
        result.save()
        return result

    def save(self, *args, **kwargs):
        data = {}
        data.update(self.raw_data)
        data["status"] = self.task_status
        if self.status:
            data["status_code"] = self.status
        if self.reason:
            data["reason"] = self.reason
        if self.extra_attr:
            for key in self.extra_attr:
                data[key] = self.extra_attr[key]
        self.raw_data = data
        return super(ResultData, self).save(*args, **kwargs)

    def to_json(self):
        output = {}
        output.update(self.raw_data)
        output["created_at"] = self.created_at.isoformat()
        output["updated_at"] = self.updated_at.isoformat()
        return output
