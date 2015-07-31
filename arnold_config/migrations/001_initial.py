__author__ = 'sweemeng'
from .. import database
from .. import ResultData

def up():
    database.connect()
    database.create_table(ResultData)

def down():
    database.connect()
    database.drop_table(ResultData)