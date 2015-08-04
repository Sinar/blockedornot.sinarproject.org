__author__ = 'sweemeng'
from .. import migrator
from playhouse.migrate import migrate
import logging


def up():

    migrate(
        migrator.rename_column("resultdata", "create_at", "created_at")

    )

def down():
    migrate(
        migrator.rename_column("resultdata", "created_at", "create_at")
    )