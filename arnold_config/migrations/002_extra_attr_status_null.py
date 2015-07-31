__author__ = 'sweemeng'
from .. import migrator
from playhouse.migrate import migrate


def up():
    migrate(
        migrator.drop_not_null("resultdata", "extra_attr"),
        migrator.drop_not_null("resultdata", "status")
    )

def down():
    migrate(
        migrator.add_not_null("resultdata", "extra_attr"),
        migrator.add_not_null("resultdata", "status")
    )