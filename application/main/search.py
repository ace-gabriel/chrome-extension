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

search_bp = Blueprint('search', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@search_bp.route('/search',methods=['GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
def search_text():
  rule = g.current_rule
  includes = rule.includes

  _search_text = request.args.get("search_text")
  result = {}

  # address search
  if "addr" in includes or len(includes)==0:
    _body = {'query': 
              {'bool': 
                {'must': 
                  {"multi_match": 
                    {"fields": ["addr","city"], 
                    "query": _search_text}
                    }
                  }
                }
            }

    res = es.search(index=HOME_INDEX,
                    doc_type=HOME_TYPE,
                    body=_body, size=10, 
                    _source_include=["addr"])

    result['addr'] = [r['_source'] for r in res['hits']['hits']]

  ## zipcode search
  if "zipcode" in includes or len(includes)==0:
    _body = {'query': 
              {'bool': 
                {'must': 
                  {"multi_match": 
                    {"fields": ["zipcode"], 
                    "query": _search_text}
                  }
                }
              }
            }
    res = es.search(index=HOME_INDEX,
                    doc_type=HOME_TYPE,
                    body=_body,
                    _source_include=["zipcode"])

    result['zipcode'] = [r['_source'] for r in res['hits']['hits']]

  #city search
  if "city" in includes or len(includes)==0:
    _body = {'query': 
              {'bool': 
                {'must': 
                  {"multi_match": 
                    {"fields": ["city"],
                     "query": _search_text}
                  }
                }
              }
            }

    res = es.search(index=HOME_INDEX,
                    doc_type=HOME_TYPE,
                    body=_body, _source_include=["city","addr"])
    result['city'] = [r['_source'] for r in res['hits']['hits']]

  return jsonify(result=result)


@search_bp.route('/query',methods=['GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
def query():
  """
    property search and sort within the certain areas or an area
  """
  rule = g.current_rule

  includes_fields = json.loads(rule.includes) if rule.includes else []
  excludes_fields = json.loads(rule.excludes) if rule.excludes else []

  _area_id = request.args.get("_na")
  _search_text = request.args.get("search_text")

  _beds = request.args.get("beds")
  _bedroom = request.args.get("bedroom")  # support mutiple bed query
  _upper_bed = request.args.get("bedroom_upper")

  _baths = request.args.get("baths")
  _areamin = request.args.get("areamin")
  _areamax = request.args.get("areamax")
  _val_expectmin = request.args.get("val_expectmin")
  _val_expectmax = request.args.get("val_expectmax")
  _rent_expectmin = request.args.get("rent_expectmin")
  _rent_expectmax = request.args.get("rent_expectmax")

  _house_pricemin = request.args.get("house_pricemin")
  _house_pricemax = request.args.get("house_pricemax")
  _house_price_range = request.args.get("house_price_ranges")    # price range
  _upper_house_price = request.args.get("house_price_upper")


  _status = request.args.get("status")
  _zipcode=request.args.get("zipcode")

  _sort_by_val_expect = request.args.get("sort_val") or "1"
  _sort_by_price = request.args.get("sort_price")
  _sort_by_online_date = request.args.get("sort_od")

  _sort_by_cz=request.args.get("sort_cz")
  _sort_by_year=request.args.get("sort_year")
  _limit = request.args.get('limit')
  _page = request.args.get('page')
  _online_day=request.args.get('online_day')

  _isVilla=request.args.get('isVilla')
  _isApartment=request.args.get('isApartment')

  if _page:
    page=int(_page)-1
  else:
    page=0
  if _limit:
    limit=int(_limit)
  else:
    limit=20
  lm=page*limit

  _area_id = _area_id.split(',') if _area_id else []
  _area_id = app.config['POPULAR_AREAS'] if not _area_id else _area_id


  _query = []
  query_body = {'bool': {
                  'must': filter_city(_query, area_ids=_area_id, val_expect=[_val_expectmin, _val_expectmax], beds=_beds,
                        baths=_baths,
                        area=[_areamin, _areamax], house_price=[_house_pricemin, _house_pricemax],
                        rent_expect=[_rent_expectmin, _rent_expectmax], status=_status, isVilla=_isVilla,
                        isApartment=_isApartment,online_day=_online_day,zipcode=_zipcode,bedroom=_bedroom,price_range=_house_price_range,
                        upper_bed=_upper_bed,
                        house_price_range=_house_price_range,
                        upper_house_price=_upper_house_price),
                  'must_not':[
                            {"match_phrase":{"room_type":{"query": ""}}}
                  ]
              }}

  # prepare the query body (with search)
  if _search_text:
    query_body['bool']['must'].append({"multi_match": {"fields": ["city", "addr","zipcode"], 
                                                        "query": _search_text}})

  _sort_body = sort_result(sort_val=_sort_by_val_expect, sort_price=_sort_by_price, sort_od=_sort_by_online_date,
                           sort_cz=_sort_by_cz,sort_year=_sort_by_year)

  _body = {"query": query_body, 
          "sort": _sort_body}

  res = es.search(index=HOME_INDEX,
                  doc_type=HOME_TYPE,
                  body=_body,
                  size=limit,  # TODO
                  _source_include=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,include=True),
                  _source_exclude=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True),
                  from_=lm
                  )
  result = {}
  result['rooms'] = {}

  result['rooms'] = [EsqueryHelper.to_dict_with_filter(EsqueryHelper.process_room_item(source["_source"]),columns=includes_fields) for source in res['hits']['hits']] if res else []
  result['length'] = res['hits']['total']

  return jsonify(result=result)
