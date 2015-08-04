__author__ = 'sweemeng'
from .. import migrator
from playhouse.migrate import migrate
from playhouse.postgres_ext import *

description = CharField(null=True)

def up():
    migrate(
        migrator.add_column("resultdata", "description", description)

    )

def down():
    migrate(
        migrator.drop_column("resultdata", "description", description)
    )