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

city_bp = Blueprint('city', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@city_bp.route('/city', methods=['GET','POST'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
def city():
  """
    get city information
  """
  rule = g.current_rule

  _area_id = request.args.get("_na") or request.get_json().get('_na')
  area = EsqueryHelper.get_stats_by_area_id(area_id=_area_id)
  area_db = Area.query.filter_by(geoid=_area_id).first()
  if not area and not area_db:
    return jsonify(message='No existing area/city'),404

  result = {}
  add_fields = ['history','block_apartment_median','block_villa_median','deal_average_price','list_average_price','occ_rate_airbnb','occ_rate_long','return_airbnb','return_long']
  for i in add_fields:
    if i=='history':
      result[i] = json.loads(area_db.history) if getattr(area_db,i) else []
      continue
    result[i] = getattr(area_db,i)
  for i in area:
    result[i] = area[i]

  # add count
  # care aboout score which is large than 80
  HIGH_QUALITY_SCORE = 80
  count = es.count(
            index=HOME_INDEX,
            doc_type=HOME_TYPE,
            body={
                  "query": {
                    "bool": {
                      "must": [
                        {
                          "match_all": {}
                        },
                        {
                          "match_phrase": {
                            "area.id": {
                              "query": _area_id
                            }
                          }
                        },
                        {
                          "range": {
                            "score": {
                              "gte": HIGH_QUALITY_SCORE
                            }
                          }
                        }
                      ],
                      "filter": [],
                      "should": [],
                      "must_not": []
                    }}}
          )
  result['hq_length'] = count['count']
  includes, excludes = rule.includes, rule.excludes
  item = EsqueryHelper.to_dict_with_exclude(result,excludes)
  item = EsqueryHelper.to_dict_with_filter(item, columns=includes)
  return jsonify(success=True,result=item)
