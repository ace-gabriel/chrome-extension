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

nearby_bp = Blueprint('nearby', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@nearby_bp.route('/nearby',methods=['GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@json_validate(filter=["centroid"])
@uuid_gen
def nearby():
  # controid example: "33.727929,-112.0005255"
  rule = g.current_rule
  centroid = request.args.get("centroid")

  NEARBY_RANGE_KM = "5mi"
  ROOMS_LENGTH = 15     # return 15 rooms nearby the centroid
  query = {
            "query": {
              "bool": {
                "must": [],
                "filter": {
                    "geo_distance" : {
                              "distance" : NEARBY_RANGE_KM,
                              "location_point" : centroid,
                          }
                },
                "should": [],
                "must_not": [{"match_phrase":{"room_type":{"query": ""}}}]
              }
            },
            "sort":[
              {
                "_geo_distance" : {
                  "location_point" : centroid,
                  "order": "asc",
                  "unit": "mi"
                }
              }
            ]
          }
  includes_fields = json.loads(rule.includes) if rule.includes else []
  excludes_fields = json.loads(rule.excludes) if rule.excludes else []
  res = es.search(index=HOME_INDEX,
                  doc_type=HOME_TYPE,
                  body=query,
                  size=ROOMS_LENGTH,
                  _source_include=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True),
                  _source_exclude=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True)
                  )
  if not res:
    return jsonify(success=True,result=[])

  item_processed = []
  for r in res['hits']['hits']:
    new_dict = r['_source']
    new_dict['distance'] = "{} mi".format(r['sort'][0])
    item = EsqueryHelper.to_dict_with_filter(EsqueryHelper.process_room_item(new_dict),columns=includes_fields)
    item_processed.append(item)

  return jsonify(success=True,result=item_processed)
