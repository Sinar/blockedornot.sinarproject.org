__author__ = 'sweemeng'
from .. import migrator
from playhouse.migrate import migrate
from playhouse.postgres_ext import *

reason = CharField(null=True)

def up():
    migrate(
        migrator.add_column("resultdata", "reason", reason)

    )

def down():
    migrate(
        migrator.drop_column("resultdata", "reason", reason)
    )