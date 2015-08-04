__author__ = 'sweemeng'
from .. import migrator
from playhouse.migrate import migrate
from playhouse.postgres_ext import *

isp = CharField(null=True)

def up():
    migrate(
        migrator.add_column("resultdata", "isp", isp)

    )

def down():
    migrate(
        migrator.drop_column("resultdata", "isp", isp)
    )