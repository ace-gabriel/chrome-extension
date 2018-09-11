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

home = Blueprint('home', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@home.route('/homedetails', methods=['POST','GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
def homedetail():
  """
    get information of certain property
  """
  incoming = request.get_json()
  rule = g.current_rule

  home_ids = str(incoming['home_id']).split(',') if incoming.get('home_id') else None
  place_name = incoming.get('place_name')

  if not (home_ids or place_name):
    return jsonify(error=True,message="Unmatched query parameters"),409

  result = []
  includes_fields = json.loads(rule.includes) if rule.includes else []
  excludes_fields = json.loads(rule.excludes) if rule.excludes else []

  if home_ids:
    query_should = [{"match_phrase":{"_id":r}} for r in home_ids if r]
  else:
    query_should = [{"match_phrase":{"addr":place_name}}]
  res = es.search(index=HOME_INDEX,
            doc_type=HOME_TYPE,
            filter_path=['hits.hits._*'],
            body={
              "query": {
                  "bool": {
                    "must": [
                      {
                        "match_all": {}
                      },
                      {
                        "bool": {
                          "should": query_should,
                          "minimum_should_match": 1
                        }
                      }
                    ],
                    "filter": [],
                    "should": [],
                    "must_not": []
                  }
              }
            },
          _source_exclude=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True)
            )
  if not res:
    return jsonify(success=True,result=[])
  items_list = [r['_source'] for r in res['hits']['hits']]
  if not items_list:
    return jsonify(success=True,result=items_list)

  # processed
  d = {}
  item_processed = [EsqueryHelper.to_dict_with_re_filter(EsqueryHelper.process_room_item(item),columns=includes_fields) for item in items_list]

  # add neighborhood history
  for i in item_processed:
    if i.get('neighborhood') and i['neighborhood'].get('id'):
      i['neighborhood']['history'] = get_neighborhood_history_by_regionid(i['neighborhood'].get('id'))
  return jsonify(success=True,result=item_processed)


def get_neighborhood_history_by_regionid(region_id):
  n = Neighborhood.query.filter_by(region_id=region_id).first()
  if n and n.home_value_sale_price_history:
    return json.loads(n.home_value_sale_price_history)
