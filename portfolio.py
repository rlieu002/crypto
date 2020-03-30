import datetime
from peewee import *

db = MySQLDatabase(host='localhost', user='root', passwd='', database='crypto')

class BaseModel(Model):
    class Meta:
        database = db

class Portfolio(BaseModel):
    name = CharField(max_length=50)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField()

class Trade(BaseModel):
    portfolio = ForeignKeyField(Portfolio, to_field='id')
    currency = CharField(max_length=5)
    base_currency = CharField(max_length=5)
    base_currency_usd = DecimalField(max_digits=20,decimal_places=6)
    price = DecimalField(max_digits=20,decimal_places=6)
    quantity = DecimalField(max_digits=20,decimal_places=6)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField()

db.create_tables([Portfolio, Trade], True)