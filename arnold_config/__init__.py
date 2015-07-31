from blockornot.models import db
from blockornot.models import ResultData
from playhouse.migrate import PostgresqlMigrator

database = db
migrator = PostgresqlMigrator(db)