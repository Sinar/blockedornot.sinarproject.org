__author__ = 'sweemeng'
from playhouse.postgres_ext import *
from app import create_app
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
    task_status = CharField()
    # This is for additional attribute that don't exist in other test. Such as DNS server and DNS provider
    extra_attr = JSONField(null=True)
    # Because DNS return a text i.e NXDOMAIN, and http return code i.e 200. Number don't matter anyway
    status = CharField(null=True)
    # Making data easily queriable in SQL, few lines of code. the ability to get the raw data, priceless.
    # And there is attribute that is unique to some test for example DNS server and provider.
    raw_data = JSONField()
    # Not part of json
    # This is only created but never change
    created_at = DateTimeField(default=datetime.datetime.now)
    # This is create then updated
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db