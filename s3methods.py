from flask import Flask, jsonify, request, make_response
from datetime import timedelta, datetime
from functools import wraps
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr
from CustomJSONEncoder import CustomJSONEncoder
from util.databaseDefinition import getDatabase
import boto3
from flasgger import Swagger
from flasgger.utils import swag_from
from util.constants import NoDatabaseFound

import simplejson as json
import jwt
import sqlite3
from sqlite_s3_query import sqlite_s3_query
from flask import Blueprint
from functools import partial

s3_api = Blueprint('s3_api', __name__)

def get_credentials(_):
    return (
        "us-east-1",
        "",
        "",
        None
    )

@s3_api.route('/getroutessthree')
def getroutessthree() -> str:
    query_my_db = partial(sqlite_s3_query,
        url='https://s3.amazonaws.com/meubusao.com/grenoble.sqlite',
        get_credentials=get_credentials
    )

    with query_my_db() as query:
        with query('SELECT * FROM route') as (columns, rows):
            data = []
            for row in rows:
                print(row)
                data.append(row)            
    return jsonify(data)
