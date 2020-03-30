import datetime
import json
from peewee import *
from playhouse.shortcuts import model_to_dict, dict_to_model
import os
from dotenv import load_dotenv, find_dotenv

db_user = os.environ.get("DB_USER") or 'dev'
db_pass = os.environ.get("DB_PASS") or ''
db = MySQLDatabase(host='localhost', user=db_user, passwd=db_pass, database='crypto')

class BaseModel(Model):
    class Meta:
        database = db

    def __str__(self):
        return str(model_to_dict(self))

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.now()
        return super(BaseModel, self).save(*args, **kwargs)

class Portfolio(BaseModel):
    name = CharField(max_length=255)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField()

class Order(BaseModel):
    portfolio = ForeignKeyField(Portfolio)
    currency = CharField(max_length=10, index=True) # Index on this field to search
    base_currency = CharField(max_length=10)
    price = DecimalField(max_digits=20,decimal_places=8,auto_round=True)
    quantity = DecimalField(max_digits=20,decimal_places=8,auto_round=True)
    order_type = CharField(index=True)
    status = CharField(max_length=255, index=True)
    comment = CharField(null=True, max_length=255)   
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField()

    def market_symbol(self):
        return "%s/%s" % (self.currency, self.base_currency)

class Trade(BaseModel):
    portfolio = ForeignKeyField(Portfolio)
    currency = CharField(max_length=10, index=True) # Index on this field to search
    base_currency = CharField(null=True, max_length=10)
    base_currency_usd = DecimalField(max_digits=20,decimal_places=8,auto_round=True,null=True)
    price = DecimalField(null=True,max_digits=20,decimal_places=8,auto_round=True)
    quantity = DecimalField(max_digits=20,decimal_places=8,auto_round=True)
    comment = CharField(null=True, max_length=255)   
    linked_trade = ForeignKeyField('self', null=True, unique=True)
    trade_fee = DecimalField(null=True,max_digits=20,decimal_places=8,auto_round=True)
    order = ForeignKeyField(Order,null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField()
    
db.create_tables([Portfolio, Trade, Order], True)
