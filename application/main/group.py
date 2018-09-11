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

group_bp = Blueprint('group', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@group_bp.route('/group',methods=['GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
def group():
  """ get area's statistices data
  """
  _geojson=request.args.get('geojson')
  _level=request.args.get('level')
  _geoids=request.args.get('geoid')

  _beds = request.args.get("beds")
  _baths = request.args.get("baths")
  _areamin = request.args.get("areamin")
  _areamax = request.args.get("areamax")
  _val_expectmin = request.args.get("val_expectmin")
  _val_expectmax = request.args.get("val_expectmax")
  _rent_expectmin = request.args.get("rent_expectmin")
  _rent_expectmax = request.args.get("rent_expectmax")
  _house_pricemin = request.args.get("house_pricemin")
  _house_pricemax = request.args.get("house_pricemax")
  _status=request.args.get("status")

  _sort_by_val_expect = request.args.get("sort_val")
  _sort_by_price = request.args.get("sort_price")
  _sort_by_online_date = request.args.get("sort_od")
  _sort_by_year=request.args.get("sort_year")
  _search_text = request.args.get("search_text")
  _sort_by_cz = request.args.get("sort_cz")

  _isVilla = request.args.get('isVilla')
  _isApartment = request.args.get('isApartment')
  _online_day = request.args.get('online_day')
  area_ids = _geoids.split(',') if _geoids else []
  area_ids = app.config['POPULAR_AREAS'] if not area_ids else area_ids

  # prepare the query body (without search)
  _query=[]
  query_body = {
                'bool': {
                  'must': filter_city(_query, area_ids=area_ids,val_expect=[_val_expectmin, _val_expectmax], beds=_beds, baths=_baths,area=[_areamin, _areamax], house_price=[_house_pricemin, _house_pricemax],rent_expect=[_rent_expectmin, _rent_expectmax],status=_status,isVilla=_isVilla,isApartment=_isApartment,online_day=_online_day)}
                }

  # prepare the query body (with search)
  if _search_text:
    query_body['bool']['must'].append({"multi_match": {"fields": ["city", "addr"], 
                                                        "query": _search_text}})
  # prepare the sort body
  _sort_body = sort_result(sort_val=_sort_by_val_expect,
                            sort_price=_sort_by_price,
                            sort_od=_sort_by_online_date,
                            sort_cz=_sort_by_cz,
                            sort_year=_sort_by_year)

  includes_fields = ["id", "location"]
  # the whole body here (fetch ten items from every area which satisfied the certain criteria)
  _body = {
          "query": query_body,
          "sort": _sort_body,
          "size": 0,
          "aggs": {
            "top-areas": {
              "terms": {
                "field": "area.id.keyword",
                "size":30,
              },
              "aggs": {
                "top_area_hits": {
                  "top_hits": {
                    "size": 10,  # only ten from every msa
                    "_source": {
                      "includes": includes_fields
                    }
                  }
                },
              }
            }
          }
        }
  res = es.search(index=HOME_INDEX,
                  doc_type=HOME_TYPE,
                  body=_body,
                  size=20000,
                  _source_include=includes_fields,
                  )
  area = Area.query.filter(Area.geoid.in_(area_ids)).all()

  if _level=='0':
    areadict={}
    for each in area:
      areadict[str(each.geoid)] = [[float(each.lng),float(each.lat)],each.eng_name]

    features=[]
    for each in res['aggregations']['top-areas']['buckets']:
      before = {
                  "count":each['doc_count'],
                  "eng_name":areadict[each['key']][1],
                  "geoid":each['key'],
                  "center":areadict[each['key']][0]
                }
      after = EsqueryHelper.get_stats_by_area_id(each['key'])
      z = before.copy()
      z.update(after)
      features.append({"geometry":
                            { "type":"Point",
                              "coordinates":areadict[each['key']][0]
                            },
                        "properties":z,
                        "type":"Feature"})

    r_res = {
            "group": {
                    "features":features,
                    "type": "FeatureCollection"
                    }

                ,
            "level":0,
            "length":0,
            "rooms":[]
        }
    return jsonify(result=r_res, success=True)


  if _level=='1':
    features = []

    for each in res['hits']['hits']:
      features.append({"geometry":
                          {"type":"Point",
                          "coordinates":each['_source']['location']['coordinates']},
                      "properties":{"id":each['_source']['id']},
                      "type":"Feature"})
    for each in res['hits']['hits']:
      del each['_id']
      del each['_index']
      del each['_score']
    r_res = {
      "group": {
        "features": features,
        "type": "FeatureCollection"
      },
      "level": 1,
      "boundary":dict({"type": "FeatureCollection"}.items()+area[0].properties.items())
    }
    return jsonify(result=r_res, success=True)
