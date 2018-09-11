# -*- encoding='utf-8'
import pandas as pd
import numpy as np
from flask import request, jsonify, g
from flask import Blueprint
from ..utils.esquery import EsqueryHelper
from ..utils.query import QueryHelper
from ..utils.auth import requires_auth, json_validate, requires_rule
from ..utils.helper import uuid_gen
from ..utils.query_census import query_census_detail
from ..utils.request import  get_ipaddr
from ..settings import HOME_INDEX,HOME_TYPE
from ..finance.search_city import *
from index import app,db,es,redis_store,limiter,home_cache,city_cache
from flask_cors import cross_origin
from ..models import IpQuery
from city_to_state import *
import  datetime
import json

"Add target cities here"
cities = ["Berkeley"]
states = ["CA"]


def get_city_data(city, state):


  city = city
  state = state
  engine_str = app.config['SQLALCHEMY_BINDS']['datawarehouse']
  city_geoid = map_geoid(engine_str, city, state)
  nb_stats = scoring_neighborhood(city)
  real_estate_stats = get_city_sources(city)
  census_result = query_census_detail(engine_str, city_geoid)
  result = dict(nb_stats.items() + real_estate_stats.items() + census_result.items())
  city_cache.set_key_value(name = city_geoid, value = json.dumps(result),expiration = 60 * 60 * 24)


if __name__ == '__main__':
    with app.app_context():
        for city, state in zip(cities, states):
            get_city_data(city, state)
