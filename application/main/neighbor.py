# -*- coding: utf-8 -*-
from flask import request, jsonify, g
from flask import Blueprint
from sqlalchemy import or_

from application.utils.filter import filter_city, sort_result
from ..utils.query import QueryHelper
from ..utils.esquery import EsqueryHelper
from ..models import Area,City,Neighborhood
from ..utils.auth import requires_auth, json_validate, requires_rule
from ..utils.helper import uuid_gen
from ..utils.roles import CUSTOMER, ADMIN, EVERYONE
from .. import settings
from ..settings import HOME_INDEX,HOME_TYPE
from ..settings import FIELDS_WHITE_LIST
from index import app,db,es,redis_store,limiter

from ..utils.count import Count
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import json
import datetime

neighbor_bp = Blueprint('neighbor', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@neighbor_bp.route('/neighbors',methods=['GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
def neighbor():
  _area_id = request.args.get("_na")
  area = Area.query.filter_by(geoid=int(_area_id)).first()
  if not area:
    return  jsonify(result=[],success=True)
  neighbors = Neighborhood.query.filter_by(area_geoid=int(area.geoid)).all()
  features_array = []
  for n in neighbors:
    if not n.properties:
      continue
    p = json.loads(n.properties)['features'][0]
    p['properties'] = EsqueryHelper.get_stats_by_neighbor_id(neighbor_id=n.region_id)
    p['properties']['name'] = n.name
    if p['properties'].get('increase_ratio') and p['properties'].get('rent_increase_ratio'):
      features_array.append(p)

  result = {"type":"FeatureCollection",
            "features":features_array}
  return jsonify(result=result,success=True)
