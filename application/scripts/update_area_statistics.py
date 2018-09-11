# python -m application.scripts.update_area_statistics (how to run?)
# please cd to wehomeInvestment folder
# print __name__, __package__

from flask import request, jsonify, g
from flask import Blueprint

from ..utils.filter import filter_city, sort_result
from ..utils.query import QueryHelper
from ..utils.esquery import EsqueryHelper
from ..models import Area,City,Neighborhood
from ..utils.auth import requires_auth, json_validate
from ..utils.helper import uuid_gen
from ..utils.roles import CUSTOMER, ADMIN, EVERYONE

from index import app,db,es,redis_store

from .. import settings

from elasticsearch import Elasticsearch
from elasticsearch import helpers
import json
import datetime

from multiprocessing import Pool

logger = app.logger

HOME_INDEX = 'rooms'
HOME_TYPE = 'room'

def job(area):
  area_statistics = {}
  if not area.properties:
    return
  p = area.properties['features'][0]
  _body = {
                    "query": {
                      "geo_shape": {
                        "location": {
                          "relation": "within",
                          "shape": p['geometry']
                        }
                      }
                    },
                    "aggs":{
                        "median_rent_income_ratio":
                            {"percentiles":{"field":"rental_income_ratio","percents":[50.0]}},
                        "median_increase_ratio":
                            {"percentiles":{"field":"increase_ratio","percents":[50.0]}},
                        "median_sale_rent_ratio":
                            {"percentiles":{"field":"sale_rent_ratio","percents":[50.0]}},
                        "median_house_price":
                            {"percentiles":{"field":"house_price_dollar","percents":[50.0]}},
                        "median_rent_price":
                            {"percentiles":{"field":"rent","percents":[50.0]}},
                        "score":
                            {"percentiles":{"field":"score","percents":[50.0]}},
                        "median_airbnb_price":
                            {"percentiles":{"field":"airbnb_rent","percents":[50.0]}},
                        "median_airbnb_rental_ratio":
                            {"percentiles":{"field":"airbnb_rental_ratio","percents":[50.0]}}
                      }
              }
  with app.app_context():
    res = es.search(index=HOME_INDEX,
            doc_type=HOME_TYPE,
            body=_body,
            size=0
      )
  p['properties']['rent_increase_ratio'] = res['aggregations']['median_rent_income_ratio']['values']['50.0']
  p['properties']['increase_ratio'] = res['aggregations']['median_increase_ratio']['values']['50.0']
  p['properties']['sale_rent_ratio'] = res['aggregations']['median_sale_rent_ratio']['values']['50.0']
  p['properties']['house_price'] = res['aggregations']['median_house_price']['values']['50.0']
  p['properties']['rent_median'] = res['aggregations']['median_rent_price']['values']['50.0']
  p['properties']['airbnb_median'] = res['aggregations']['median_airbnb_price']['values']['50.0']
  p['properties']['airbnb_rental_ratio'] = res['aggregations']['median_airbnb_rental_ratio']['values']['50.0']
  p['properties']['score'] = res['aggregations']['score']['values']['50.0']
  p['properties']['region_id'] = area.geoid

  # separate sale and sold status
  with app.app_context():
    status_sale = 2
    _body_separate = {
                    "query": {
                      "bool":{
                        "must":[{"match":{"status":2}}],

                        "filter":{
                            "geo_shape": {
                              "location": {
                                "relation": "within",
                                "shape": p['geometry']}
                                        }
                                }
                              }
                            },
                    "aggs":{
                        "median_house_price":
                            {"percentiles":{"field":"price","percents":[50.0]}}
                      }
              }
    res_sale = es.search(index=HOME_INDEX,doc_type=HOME_TYPE,body=_body_separate,size=0)
  with app.app_context():
    status_sold = 4
    _body_separate = {
                    "query": {
                      "bool":{
                        "must":[{"match":{"status":4}}],
                        "filter":{
                            "geo_shape": {
                              "location": {
                                "relation": "within",
                                "shape": p['geometry']}
                                        }
                                }
                              }
                            },
                    "aggs":{
                        "median_house_price":
                            {"percentiles":{"field":"price","percents":[50.0]}}
                      }
              }
    res_sold = es.search(index=HOME_INDEX,doc_type=HOME_TYPE,body=_body_separate,size=0)

  p['properties']['listing_price'] = res_sale['aggregations']['median_house_price']['values']['50.0']
  p['properties']['sold_price'] = res_sold['aggregations']['median_house_price']['values']['50.0']

  airbnb_rental_ratio = None if p['properties']['airbnb_rental_ratio']==u'NaN' else p['properties']['airbnb_rental_ratio']
  rent_increase_ratio = None if p['properties']['rent_increase_ratio']==u'NaN' else p['properties']['rent_increase_ratio']
  increase_ratio = None if p['properties']['increase_ratio']==u'NaN' else p['properties']['increase_ratio']
  sale_rent_ratio = None if p['properties']['sale_rent_ratio']==u'NaN' else p['properties']['sale_rent_ratio']
  total_ratio = increase_ratio + rent_increase_ratio if increase_ratio and rent_increase_ratio else None
  house_price = None  if p['properties']['house_price']==u'NaN' else p['properties']['house_price']
  rent_median = None if p['properties']['rent_median']==u'NaN' else p['properties']['rent_median']
  airbnb_rent_median = None if p['properties']['airbnb_median']==u'NaN' else p['properties']['airbnb_median']
  score = None if p['properties']['score']==u'NaN' else p['properties']['score']
  sale_price = None if p['properties']['listing_price'] ==u'NaN' else p['properties']['listing_price']
  sold_price = None if p['properties']['sold_price'] ==u'NaN' else p['properties']['sold_price']

  area_statistics[area.geoid] = {"increase_ratio":increase_ratio,
                                "rent_increase_ratio":rent_increase_ratio,
                                "sale_rent_ratio":sale_rent_ratio,
                                "house_price":house_price,
                                "rent_median":rent_median,
                                "airbnb_rent_median":airbnb_rent_median,
                                "score":score,
                                "total_ratio":total_ratio,
                                "airbnb_rental_ratio":airbnb_rental_ratio,
                                "score":score,
                                "sale_price":sale_price,
                                "sold_price":sold_price}
  more_fields_for_irr = {"acquisition_cost":area.acquisition_cost,
                        "cap_ex":area.cap_ex,
                        "disposition_cost":area.disposition_cost,
                        "insurance_cost":area.insurance_cost,
                        "leasing_commission":area.leasing_commission,
                        "property_management_fee":area.property_management_fee,
                        "property_tax":area.property_tax,
                        "repair":area.repair,
                        "vaccancy_rate":area.vaccancy_rate,
                        "rent_growth":area.rent_growth,
                        "down_payment":area.down_payment,
                        "expenses":area.expenses,
                        "loan_interest_rate":area.loan_interest_rate,
                        "closing_costs_misc":area.closing_costs_misc}
  area_statistics[area.geoid].update(more_fields_for_irr)
  redis_store.hmset(settings.AREA_STATISTICS,area_statistics)


if __name__ == '__main__':
  with app.app_context():
    logger.warning("Engineer: starting updating statistics of area,length(+0) statistics updating!")
  areas = Area.query.filter_by().all()

  p = Pool(processes=50)
  data = p.map(job,areas)
  p.close()
  with app.app_context():
    logger.warning("Engineer: finished updating statistics of area,length(+{}) statistics updating!".format(len(data)))
