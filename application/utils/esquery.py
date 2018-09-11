from ..models import Area, Neighborhood
from index import app,redis_store,es
import json
from .. import settings

from pprint import pprint
import pandas as pd
import math
from numpy import irr
import numpy as np
import re

class EsqueryHelper(object):
  'You can use this class query the complex query'

  @classmethod
  def process_room_item(cls,item,area_stats=None,neighbor_stats=None):
    if item.get('area') and item['area'].get('id'):
      area_stats = cls.get_stats_by_area_id(area_id=item['area']['id'])
      if area_stats:
        item['area'].update(area_stats)
    if item.get('neighborhood') and item.get('neighborhood').get('id'):
      neigh_stats = cls.get_stats_by_neighbor_id(neighbor_id=item['neighborhood']['id'])
      if neigh_stats:
        item['neighborhood'].update(neigh_stats)

    # handle pict_url
    # TODO pict_urls should be list not string here
    if not isinstance(item.get('pict_urls'),list):
      item['pict_urls'] = item.get('pict_urls').strip('{').strip('}').split(',') if item.get('pict_urls') else []
      item['pict_urls'] = [i for i in item['pict_urls'] if '"' not in i]

    # handle intial investment value
    item['initial_adjust'] = {
           "price":item['house_price_dollar'],
           "down_payment":0.28,
           "loan_interest_rate":0.4625,
           "rent":item['rent'],
           "appreciation":item.get('increase_ratio'),
           "expenses":0.27,
           "property_taxes":1500,  #TODO
           "closing_costs_misc":0.015
     }

    return item

  @classmethod
  def jsonify_pict_url(cls,item,first=False):
    item['pict_urls'] = item.get('pict_urls').strip('{').strip('}').split(',') if item.get('pict_urls') else []
    if first:
      item['pict_urls'] = item['pict_urls'][0] if len(item['pict_urls'])>0 else None
    return item

  @classmethod
  def _config_area_statistic(cls,redis_key=None):
    statistics_from_mysql = False
    statistics_from_redis = True

    statistics = {}
    if statistics_from_mysql:
      statistics_list = Area.query.with_entities(Area.geoid,Area.increase_ratio,Area.rent_increase_ratio,Area.sale_rent_ratio).all()
      statistics = { s[0]:{"increase_ratio":s[1],"rent_increase_ratio":s[2],"sale_rent_ratio":s[3]} for s in statistics_list}
    elif statistics_from_redis:
      statistics = redis_store.hgetall(redis_key)
    return statistics

  @classmethod
  def _config_neighbor_statistic(cls,redis_key=None):
    statistics_from_mysql = False
    statistics_from_redis = True

    statistics = {}
    if statistics_from_mysql:
      statistics_list = Neighborhood.query.with_entities(Neighborhood.region_id,Neighborhood.forecast_increase_ratio,Neighborhood.forecast_rent_ratio,Neighborhood.sale_rent_ratio).all()
      statistics = { s[0]:{"increase_ratio":s[1],"rent_increase_ratio":s[2],"sale_rent_ratio":s[3]} for s in statistics_list}
    elif statistics_from_redis:
      statistics = redis_store.hgetall(redis_key)
    return statistics

  @classmethod
  def get_stats_by_area_id(cls,area_id):
    redis_key = settings.AREA_STATISTICS
    s_ = redis_store.hget(redis_key,area_id)
    if s_:
      s_area = json.loads(s_.replace("'",'"').replace("None","null"))
      return s_area or {}
    return {}

  @classmethod
  def get_stats_by_neighbor_id(cls,neighbor_id):
    redis_key = settings.NEIGHBORHOOD_STATISTICS
    s_ = redis_store.hget(redis_key,neighbor_id)
    if s_:
      s_area = json.loads(s_.replace("'",'"').replace("None","null"))
      if s_area:
        s_area['region_id']=neighbor_id
      return s_area or {}

  @classmethod
  def get_region_default_paras(cls,area_id,neighbor_id):
    redis_key_neighbor = settings.NEIGHBORHOOD_STATISTICS
    redis_key_area = settings.AREA_STATISTICS
    paras = {}
    neighbor_ = redis_store.hget(redis_key_neighbor,neighbor_id)
    if neighbor_:
      neighbor_dict = json.loads(neighbor_.replace("'",'"').replace("None","null"))
      paras['neighborhood']=neighbor_dict

    area_ = redis_store.hget(redis_key_area,area_id)
    if area_:
      area_dict = json.loads(area_.replace("'",'"').replace("None","null"))
      paras['area']=area_dict

    return paras

  @classmethod
  def config_include_or_exclude_field_from_rule(cls,rule,white_list=None,include=None,exclude=None):
    if not white_list:
      white_list = settings.FIELDS_WHITE_LIST
    if include is True:
      if rule.includes:
        s = set(json.loads(rule.includes)).union(set(white_list))
        return list(s)
      return []
    if exclude is True:
      if rule.excludes:
        s = set(json.loads(rule.excludes)).difference(set(white_list))
        return list(s)
      return []

  @classmethod
  def to_dict_with_filter(cls, item, columns):
    d = {}
    if columns:
      for k, v in item.items():
        if k in columns:
          d[k] = v
      return d
    else:
      return item

  @classmethod
  def to_dict_with_re_filter(cls, item, columns):
    d = {}
    if columns:
      for k, v in item.items():
        if k in columns:
          d[k] = v
        elif isinstance(v,dict):  #handle nested 
          for v_k,v_v in v.items():
            if "{}.{}".format(k,v_k) in columns:
              if k not in d.keys():d[k]={}
              d[k][v_k]= v_v
      return d
    else:
      return item

  @classmethod
  def to_dict_with_exclude(cls, item, exclude):
    d = {}
    if exclude:
      for k, v in item.items():
        if k not in exclude:
          d[k] = v
      return d
    else:
      return item

  @classmethod
  def get_documents_by_geoshape(cls,geometry):
    # geometry should have the following form for example:
    # geometry {
    #               "type":"MultiPolygon",
    #               "coordinates":[[[[]]]]
    #           }
    _body = {
              "query": {
                "bool": {
                  "must": {
                    "match_all": {}
                  },
                  "filter": {
                    "geo_shape": {
                      "location": {
                        "shape": geometry,
                        "relation": "within"
                      }
                    }
                  }
                }
              }
            }
    res = es.search(index=settings.HOME_INDEX,
                      doc_type=settings.HOME_TYPE,
                      body=_body,
                      size=10
                    )
    return res['hits']

  @classmethod
  def cal_cashflow(cls,item,years=5):
    # must
    PURCHASE_PRICE = item['house_price_dollar']
    RENT = item['rent']

    PROPERTY_TAX = item['property_tax']
    HOA = item.get('hoa',0)
    RENT_GROWTH = item['rent_growth']
    HOME_PRICE_APPRECIATION = item['increase_ratio']
    VACCANCY_RATE,PROPERTY_MANAGEMENT_FEE,LEASING_COMMISSION,INSURANCE_COST,REPAIR = item['vaccancy_rate'],item['property_management_fee'],item['leasing_commission'],item['insurance_cost'],item['repair']
    CAP_EX,ACQUISITION_COST,DISPOSTITION_COST = item['cap_ex'],item['acquisition_cost'],item['disposition_cost']

    UNLEVERAGED_CASH_FLOW_STR = "Unleveraged Cash Flow"
    GROSS_RENT_STR = "Gross Rent"
    ECNOMIC_VACANCY_FACTOR_STR = "Economic Vacancy Factor"
    EXPECTED_RENT = "Expected Rent"

    PROPERTY_MANAGEMENT_STR = "Property Management"
    LEASING_FEES_STR = "Leasing Fees"
    HOA_FEES = "HOA Fees"
    PROPERTY_TAXES_STR = "Propert Taxes"
    INSURANCE_STR = "Insurance"
    REPAIRS_STR = "Repairs & Maintance"
    CAPEX_STR = "CapEx"
    TOTAL_EXPENSES_STR = "Total Expenses"
    TOTAL_OPERATING_CASH_FLOW_STR = "Total Operating Cash"

    INDEXES = [
      UNLEVERAGED_CASH_FLOW_STR,
      GROSS_RENT_STR,
      ECNOMIC_VACANCY_FACTOR_STR,
      EXPECTED_RENT,
      PROPERTY_MANAGEMENT_STR,
      LEASING_FEES_STR,
      HOA_FEES,
      PROPERTY_TAXES_STR,
      INSURANCE_STR,
      REPAIRS_STR,
      CAPEX_STR,
      TOTAL_EXPENSES_STR,
      TOTAL_OPERATING_CASH_FLOW_STR
    ]

    def cal_current_operation_flow(purchase_price, rent, year):

      current_valuation = purchase_price * math.pow(1+HOME_PRICE_APPRECIATION, year)

      monthly_rent = rent*math.pow(1+RENT_GROWTH, year)
      gross_rent = monthly_rent * 12
      ecomonic_vacancy_factor = gross_rent * VACCANCY_RATE
      expected_rent = gross_rent - ecomonic_vacancy_factor

      property_managnement = expected_rent * PROPERTY_MANAGEMENT_FEE * -1
      leasing_fees = expected_rent * LEASING_COMMISSION * -1
      hoa_fees = HOA * 12 * -1
      property_tax = current_valuation * PROPERTY_TAX * -1
      insurance = expected_rent * INSURANCE_COST * -1
      repairs = expected_rent * REPAIR * -1
      capex = expected_rent * CAP_EX * -1
      total_expenses = property_managnement + leasing_fees + hoa_fees + property_tax + insurance + repairs + capex

      total_operating_cash_flow = expected_rent + total_expenses

      result = pd.Series({
        UNLEVERAGED_CASH_FLOW_STR: total_operating_cash_flow,
        GROSS_RENT_STR: gross_rent,
        ECNOMIC_VACANCY_FACTOR_STR: ecomonic_vacancy_factor,
        EXPECTED_RENT: expected_rent,
        PROPERTY_MANAGEMENT_STR: property_managnement,
        LEASING_FEES_STR: leasing_fees,
        HOA_FEES: hoa_fees,
        PROPERTY_TAXES_STR: property_tax,
        INSURANCE_STR: insurance,
        REPAIRS_STR: repairs,
        CAPEX_STR: capex,
        TOTAL_EXPENSES_STR: total_expenses,
        TOTAL_OPERATING_CASH_FLOW_STR: total_operating_cash_flow
      }, index = INDEXES)


      return result

    def cashflow(purchase_price = PURCHASE_PRICE, rent=RENT, years=5):
      net_cash_flow = []
      df = pd.DataFrame(columns=[range(0,years)],index=INDEXES)
      net_purchase_price = purchase_price * (1+ACQUISITION_COST)
      net_cash_flow.append(net_purchase_price * -1.0)
      series = []
      for year in xrange(0, years):
        series.append(cal_current_operation_flow(purchase_price, rent, year))
      df = pd.concat(series, axis=1, keys=range(1, years+1))
      df = pd.DataFrame.transpose(df)
      net_sale_price = purchase_price * math.pow(1+HOME_PRICE_APPRECIATION, years) * (1 - DISPOSTITION_COST)
      net_cash_flow += df[UNLEVERAGED_CASH_FLOW_STR].tolist()
      net_cash_flow[-1] += net_sale_price

      # print net_cash_flow
      irr_value = round(irr(net_cash_flow), 4)
      cap_rate = round(abs(1.0*net_cash_flow[1] / net_cash_flow[0]), 4)

      #print cap_rate * 100, irr_value * 100
      returns = [df[INDEXES[0]].tolist()]
      revenue = [df[INDEXES[i]].tolist() for i in range(1,4)]
      expenses = [df[INDEXES[i]].tolist() for i in range(4,13)]

      return {"flow":{"returns":returns,"revenue":revenue,"expenses":expenses},
            "cap_rate":cap_rate * 100,
            "irr":irr_value * 100}

    def cashflow_levered(purchase_price = PURCHASE_PRICE, rent=RENT, years=5):
      net_cash_flow = []
      df = pd.DataFrame(columns=[range(0,years)],index=INDEXES)
      down_payment_value = purchase_price*item['down_payment']
      loan_fees = purchase_price*item.get('loan_fees',0.01)
      # get the initial value
      net_cash_flow.append((down_payment_value+loan_fees+purchase_price*ACQUISITION_COST)*-1.0)

      # handle the middle value
      series = []
      for year in xrange(0, years):
        series.append(cal_current_operation_flow(purchase_price, rent, year))
      df = pd.concat(series, axis=1, keys=range(1, years+1))
      df = pd.DataFrame.transpose(df)
      net_sale_price = purchase_price * math.pow(1+HOME_PRICE_APPRECIATION, years) * (1 - DISPOSTITION_COST)
      net_cash_flow += df[UNLEVERAGED_CASH_FLOW_STR].tolist()

      yearly_loan_payment_point = np.pmt(item['loan_interest_rate']/12,12*30,purchase_price*(1-item['down_payment']))*12   # 30 years
      for i in range(1,len(net_cash_flow)):
        net_cash_flow[i]+=yearly_loan_payment_point

      # handle the last point
      loan_balance_start_point = purchase_price - down_payment_value
      sum_temp = 0
      for i in range(1,years+1):
        sum_temp+=yearly_loan_payment_point/math.pow(1+item['loan_interest_rate'],i)
      loan_balance_pv_of_final_point = loan_balance_start_point+sum_temp
      final_loan_balance = np.fv(item['loan_interest_rate']/12,12*years,0,-loan_balance_pv_of_final_point)

      net_cash_flow[-1] = net_cash_flow[-1] + net_sale_price - final_loan_balance

      # add loan cash flow
      #print net_cash_flow
      irr_value = round(irr(net_cash_flow), 4)
      cap_rate = round(abs(1.0*net_cash_flow[1] / net_cash_flow[0]), 4)

      #print cap_rate * 100, irr_value * 100
      returns = [df[INDEXES[0]].tolist()]
      revenue = [df[INDEXES[i]].tolist() for i in range(1,4)]
      expenses = [df[INDEXES[i]].tolist() for i in range(4,13)]

      return {"flow":{"returns":returns,"revenue":revenue,"expenses":expenses},
            "cap_rate":cap_rate * 100,
            "irr":irr_value * 100}



    #result = cashflow(purchase_price = PURCHASE_PRICE, rent=RENT, years=5)
    result = cashflow_levered(purchase_price = PURCHASE_PRICE, rent=RENT, years=5)
    # add yearly expenses
    total_ex ={}
    total_expenses = cal_current_operation_flow(item['house_price_dollar'], item['rent'], year=0)
    total_ex['expenses_total'] = total_expenses[INDEXES[3]]
    total_ex['property_managnement'] = abs(total_expenses[INDEXES[4]])
    total_ex['leasing_commission'] = abs(total_expenses[INDEXES[5]])
    total_ex['insurance_cost'] = abs(total_expenses[INDEXES[8]])
    total_ex['property_tax'] = abs(total_expenses[INDEXES[7]])
    total_ex['hoa'] = abs(total_expenses[INDEXES[6]])
    total_ex['repairs_maintenance'] = abs(total_expenses[INDEXES[9]])
    total_ex['capital_expenditures'] = abs(total_expenses[INDEXES[10]])
    result['total_expenses'] = total_ex
    # assumptions
    result['assumptions'] = {
      "purchase_price":item['house_price_dollar'],
      "down_payment":item['down_payment'],
      "interest_rate":item['loan_interest_rate'],
      "loan_term_year":30,
      "rent":item['rent'],
      "rent_growth":item['rent_growth'],
      "home_price_appreciation":item['increase_ratio'],
      "opreating_expenses_override":0,
      "vacancy_rate":item['vaccancy_rate'],
      "property_management_fee":item['property_management_fee'],
      # TODO
      "leasing_commissions":item['leasing_commission'],
      "insurance_cost":item['insurance_cost'],
      "property_tax":item['property_tax'],
      "r_m":0.04,
      "capex":item['cap_ex'],
      "acquisition_costs":item['acquisition_cost'],
      "disposition_costs":item['disposition_cost'],
      "initial_capital_costs":0,
      "loan_fees":0.01
    }

    # plot
    result['estimated_total_gain'] = {
      "increase_benefit":[],
      "rent_benefit":[],
    }
    result['equity_build_up'] = {
      "loan_balance":[],
      "equity":[],
      "property_value":[]
    }
    result['net_cash_flow'] = {
      "net_cash_flow":[],
      "loan_payments":[],
      "operating_expenses":[]
    }
    return result


