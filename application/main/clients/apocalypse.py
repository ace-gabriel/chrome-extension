from flask import request, jsonify, g
from flask import Blueprint
from sqlalchemy import or_

from application.utils.filter import filter_city, sort_result
from ...utils.query import QueryHelper
from ...utils.esquery import EsqueryHelper
from ...models import Area,City,Neighborhood
from ...utils.auth import requires_auth, json_validate, requires_rule
from ...utils.helper import uuid_gen
from ...utils.roles import CUSTOMER, ADMIN, EVERYONE
from ...finance.price import *
from ...import settings
from ...settings import HOME_INDEX,HOME_TYPE
from ...settings import FIELDS_WHITE_LIST
from index import app,db,es,redis_store,limiter

from ...utils.count import Count
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import json
import datetime

from application.http.pricetrend import return_price_point_trend

from application.model.radar_score_20180117.score_calculate import process_score

apocalypse_bp = Blueprint('client_apocalypse', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@apocalypse_bp.route('/homeinvestment', methods=['POST','GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
@json_validate(filter=['home_id'])
def homeinvestment():
  """
    For investment application
  """
  incoming = request.get_json()
  home_id = incoming['home_id']

  purchase_price = incoming.get('purchase_price')
  rent = incoming.get('rent')
  down_payment = incoming.get('down_payment')
  loan_interest_rate = incoming.get('loan_interest_rate')
  appreciation = incoming.get('appreciation')
  expenses = incoming.get('expenses')
  closing_costs_misc = incoming.get('closing_costs_misc')

  includes_fields = ['house_price_dollar','rent','area','neighborhood','rent_increase_ratio','total_ratio']
  investment_related_fields=['property_tax','hoa','vaccancy_rate','property_management_fee','leasing_commission','insurance_cost','repair','cap_ex','acquisition_cost','disposition_cost','rent_growth','increase_ratio','down_payment','expenses','loan_interest_rate','closing_costs_misc']

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
                              "match_phrase": {
                                "_id": {
                                  "query": home_id
                                }
                              }
                            }
                          ],
                          "filter": [],
                          "should": [],
                          "must_not": []
                        }
                      }
                },
            _source_include=includes_fields+investment_related_fields
            )
  item = res['hits']['hits'][0]['_source'] if res else {}
  if not item:
    return jsonify(success=True,message='no data')
  region_paras = EsqueryHelper.get_region_default_paras(area_id=item['area']['id'], neighbor_id=item['neighborhood']['id'])

  # prepare investment fields
  for f in investment_related_fields:
    if item.get(f):
      continue
    if not item.get(f) and region_paras.get('neighborhood') and item.get('neighborhood') and region_paras['neighborhood'].get(f):
      if f=='hoa':
        continue
      item[f]=region_paras['neighborhood'][f]
      continue
    if not item.get(f) and region_paras.get('area') and item.get('area'):
      if f=='hoa':
        continue
      item[f]=region_paras['area'][f]

  # user enter information
  item['house_price_dollar'] = float(purchase_price) if purchase_price else item['house_price_dollar']
  item['rent'] = float(rent) if rent else item['rent']
  item['down_payment'] = float(down_payment) if down_payment else item['down_payment']
  item['loan_interest_rate'] = float(loan_interest_rate) if loan_interest_rate else item['loan_interest_rate']
  if item['loan_interest_rate']:
    item['property_management_fee'],item['leasing_commission'],item['insurance_cost'],item['cap_ex'] = 0.32*item['loan_interest_rate'],0.12*item['loan_interest_rate'],0.22*item['loan_interest_rate'],0.34*item['loan_interest_rate']

  item['appreciation'] = incoming.get('appreciation') if appreciation else item['increase_ratio']
  expenses = incoming.get('expenses')
  closing_costs_misc = incoming.get('closing_costs_misc') if closing_costs_misc else item['closing_costs_misc']

  if not item.get('hoa'):item['hoa']=0

  # calculate irr
  invest = EsqueryHelper.cal_cashflow(item,years=5)
  initial_data = {"initial_investment":item['down_payment']*item['house_price_dollar'],
                "current_rent":item.get('rent'),
                "appreciation":item.get('increase_ratio'),
                "cap_rate":invest.pop('cap_rate'),
                "cash_flow":2000,  # TODO
                "total_cash_return":2000*12*5,  #TODO
                "irr":invest.pop('irr')
                }

  return jsonify(success=True,assumptions=invest.pop('assumptions'),total_expenses=invest.pop('total_expenses'),invest=invest,initial_data=initial_data,estimated_total_gain=invest.pop('estimated_total_gain'),equity_build_up=invest.pop('equity_build_up'),net_cash_flow=invest.pop('net_cash_flow'))


@apocalypse_bp.route('/finance', methods=['POST','GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
@json_validate(filter=['home_id'])
def finance():
  """
    only for apocalypse application
  """
  incoming = request.get_json()
  rule = g.current_rule

  home_ids = incoming.get('home_id')

  result = {}
  includes_fields = json.loads(rule.includes) if rule.includes else []
  excludes_fields = json.loads(rule.excludes) if rule.excludes else []

  query_should = [{"match_phrase":{"_id":home_ids}}]
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
          _source_exclude=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True),
          _source_include=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,include=True)
            )
  if not res:
    return jsonify(success=True,result=result)
  res_value = res['hits']['hits'][0]['_source']
  item = EsqueryHelper.to_dict_with_filter(EsqueryHelper.process_room_item(res_value),columns=includes_fields)
  item['score_radar'] = process_score(item)   # radar score
  if item.get('wehome_rent') and item['wehome_rent'] is not None:
    item['rent'] = item['wehome_rent']

  # get propety price trend
  if not item.get('url'):
    item['url'] = "https://www.zillow.com/homedetails/"+"{}_zpid/".format(home_ids.split('_')[0])
  prices = return_price_point_trend(url=item['url'],zpid=item['source_id'])
  item['price_trend'] = prices['Home']['data'] if prices and prices.get('Home') else []

  return jsonify(success=True,result=item)


@apocalypse_bp.route('/propertyprice', methods=['POST','GET'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
@json_validate(filter=['home_id'])
def update_price():

    """
    30 Dorset Dr, Kissimmee, FL, 4 Beds, 2 Baths, 28.17111, -81.489976, 46315662_zpid
    449 Hardy Water Dr, Lawrenceville, GA, 4 Beds, 3 Baths, 33.973542, -83.937303, 97994816_zpid
    300 N 130th St, Unit 1103, Seattle, WA, 1 bed, 1 bath, 47.723786, -122.353735, 82362491_zpid
    """
    NEARBY_RANGE_KM = "2mi"
    ROOMS_LENGTH = 10000

    incoming = request.get_json()
    home_id = incoming['home_id']
    #home_id = "46315662_zillow"

    properties = {}

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
                                            "match_phrase": {
                                                "_id": {
                                                    "query": home_id
                                                }
                                            }
                                        }
                                    ],
                                    "filter": [],
                                    "should": [],
                                    "must_not": []
                                }
                            }
                        }
                        )

    properties["id"] = home_id
    properties["address"] = res['hits']['hits'][0]['_source']['addr']
    properties["RoomType"] = res['hits']['hits'][0]['_source']['room_type']
    properties["Beds"] = res['hits']['hits'][0]['_source']['beds']
    properties["Baths"] = res['hits']['hits'][0]['_source']['baths']
    properties["current_price"] = 0
    properties["location"] = res['hits']['hits'][0]['_source']['location_point']


    centroid = properties["location"]


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
                      "must": [{"match_phrase":{"status": 2}}],
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
    res = es.search(index=HOME_INDEX,
                        doc_type=HOME_TYPE,
                        body=query,
                        size=ROOMS_LENGTH,
                        )


    database = GetData(res['hits']['hits'])
    area_target_properties = GetTargets(database.index.values, database, properties)
    properties['current_price'] = int(np.percentile(area_target_properties['Price'], '60'))
    properties['adjust_price_high'] = int(np.percentile(area_target_properties['Price'], '65'))
    properties['adjust_price_low'] = int(np.percentile(area_target_properties['Price'], '55'))
    properties['average_price'] = (properties['adjust_price_high'] + properties['adjust_price_low']) * 0.5
    properties['z_index'] = (properties['adjust_price_high'] - properties['adjust_price_low']) / properties['adjust_price_low']



    return jsonify(**properties)
