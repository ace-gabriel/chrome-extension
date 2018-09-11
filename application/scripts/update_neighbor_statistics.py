# python -m application.scripts.update_neighbor_statistics (how to run?)
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
from elasticsearch import TransportError 

logger = app.logger

HOME_INDEX = 'rooms'
HOME_TYPE = 'room'

def job(neighbor):
  neighbor_statistics = {}
  if not neighbor.properties:
    return
  p = json.loads(neighbor.properties)['features'][0]
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
  try:
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
    p['properties']['region_id'] = neighbor.region_id

    airbnb_rental_ratio = None if p['properties']['airbnb_rental_ratio']==u'NaN' else p['properties']['airbnb_rental_ratio']
    rent_increase_ratio = None if p['properties']['rent_increase_ratio']==u'NaN' else p['properties']['rent_increase_ratio']
    increase_ratio = None if p['properties']['increase_ratio']==u'NaN' else p['properties']['increase_ratio']
    sale_rent_ratio = None if p['properties']['sale_rent_ratio']==u'NaN' else p['properties']['sale_rent_ratio']
    total_ratio = increase_ratio + rent_increase_ratio if increase_ratio and rent_increase_ratio else None
    house_price = None  if p['properties']['house_price']==u'NaN' else p['properties']['house_price']
    rent_median = None if p['properties']['rent_median']==u'NaN' else p['properties']['rent_median']
    airbnb_rent_median = None if p['properties']['airbnb_median']==u'NaN' else p['properties']['airbnb_median']
    score = None if p['properties']['score']==u'NaN' else p['properties']['score']

    neighbor_statistics[neighbor.region_id] = {"increase_ratio":increase_ratio,
                        "rent_increase_ratio":rent_increase_ratio,
                        "sale_rent_ratio":sale_rent_ratio,
                        "house_price":house_price,
                        "rent_median":rent_median,
                        "airbnb_rent_median":airbnb_rent_median,
                        "score":score,
                        "total_ratio":total_ratio,
                        "airbnb_rental_ratio":airbnb_rental_ratio,
                        "total_ratio":total_ratio}
    more_fields_for_irr = {"acquisition_cost":neighbor.acquisition_cost,
                        "cap_ex":neighbor.cap_ex,
                        "disposition_cost":neighbor.disposition_cost,
                        "insurance_cost":neighbor.insurance_cost,
                        "leasing_commission":neighbor.leasing_commission,
                        "property_management_fee":neighbor.property_management_fee,
                        "property_tax":neighbor.property_tax,
                        "repair":neighbor.repair,
                        "vaccancy_rate":neighbor.vaccancy_rate,
                        "rent_growth":neighbor.rent_growth}
    neighbor_statistics[neighbor.region_id].update(more_fields_for_irr)
    redis_store.hmset(settings.NEIGHBORHOOD_STATISTICS,neighbor_statistics)
  except TransportError:
    with app.app_context():
      logger.warning("ES transport error")


if __name__ == '__main__':
  with app.app_context():
    logger.warning("Engineer: starting updating statistics of neighbor,length(+0) statistics updating!")
  neighbors = Neighborhood.query.filter_by().all()

  p = Pool(processes=50)
  data = p.map(job,neighbors)
  p.close()
  with app.app_context():
    logger.warning("Engineer: finished updating statistics of neighbor,length(+{}) statistics updating!".format(len(data)))
