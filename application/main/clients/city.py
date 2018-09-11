# -*- encoding='utf-8'
import pandas as pd
import numpy as np
from flask import request, jsonify, g
from flask import Blueprint
from ...utils.esquery import EsqueryHelper
from ...utils.query import QueryHelper
from ...utils.auth import requires_auth, json_validate, requires_rule
from ...utils.helper import uuid_gen
from ...utils.query_census import query_census_detail
from ...utils.request import  get_ipaddr
from ...settings import HOME_INDEX,HOME_TYPE
from ...finance.search_city import *
from index import app,db,es,redis_store,limiter,home_cache,city_cache
from ...models import IpQuery
import  datetime
import json

city_bp = Blueprint('client_city', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@city_bp.route('/dashboard/search', methods=['POST'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen

def get_city_data():

  rule = g.current_rule
  incoming = request.get_json()

  city = incoming.get('city')
  state = incoming.get('state')
  engine_str = app.config['SQLALCHEMY_BINDS']['datawarehouse']
  city_geoid = map_geoid(engine_str, city, state)

  if city_geoid == None:
    return None

  cached_result = city_cache[city_geoid]
  if cached_result:
      return jsonify(**json.loads(cached_result))

  nb_stats = scoring_neighborhood(city)
  real_estate_stats = get_city_sources(city)
  census_result = query_census_detail(engine_str, city_geoid)
  result = dict(nb_stats.items() + real_estate_stats.items() + census_result.items())
  # set key -> value pair to cache into database
  city_cache.set_key_value(name = city_geoid, value = json.dumps(result),expiration = 60 * 60 * 24 * 365 * 99)

  return jsonify(result)
