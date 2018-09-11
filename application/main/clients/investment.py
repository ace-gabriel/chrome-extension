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

investment_bp = Blueprint('client_investment', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@investment_bp.route('/homeinvestment', methods=['POST','GET'])
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
  closing_costs_misc = incoming.get('closing_costs_misc') if closing_costs_misc else item.get('closing_costs_misc')

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
