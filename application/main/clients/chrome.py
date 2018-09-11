# -*- encoding='utf-8'
from flask import request, jsonify, g
from flask import Blueprint
from ...utils.esquery import EsqueryHelper
from ...utils.query import QueryHelper
from ...utils.auth import requires_auth, json_validate, requires_rule
from ...utils.helper import uuid_gen
from ...utils.request import  get_ipaddr
from ...settings import HOME_INDEX,HOME_TYPE
from index import app,db,es,redis_store,limiter,home_cache,city_cache
from ...finance.rent import *
from ...finance.irr import *
from ...finance.appr import *
from ...finance.stats import *
from ...utils.redisDB import FeedbackCache
from ...models import IpQuery
import  datetime
import json
import geopy.distance as dist


feedback_bp = Blueprint('chrome_feedback', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@feedback_bp.route('/feedback', methods=['POST'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
def cache_user_feedback():

    user_info = request.get_json()
    user_cache = FeedbackCache(host=app.config['REDIS_SESSION_HOST'], port=app.config['REDIS_SESSION_PORT'],
                               password=app.config['REDIS_SESSION_PWD'], db=4)
    user_first_name = user_info.get("firstname")
    user_last_name = user_info.get("lastname")
    user_email = user_info.get("email")
    user_message = user_info.get("message")
    logger.warning("Business: new user feedback received. User IP: {}, Firstname: {}, Lastname: {}, Email: {}, Message: {}".format(get_ipaddr(), user_first_name, user_last_name,
                                                                                                                         user_email, user_message))
    user_cache.set_key_value(name=user_first_name+ '_' +user_last_name, value=json.dumps(user_info), expiration=60*60*24*365*100)
    success_msg = {"Success" : True}

    return (jsonify(**success_msg))



chrome_bp = Blueprint('client_chrome', __name__)
logger = app.logger

def rate_limit_from_g():
  return g.limit

@chrome_bp.route('/rent', methods=['POST'])
@requires_rule
@limiter.limit(rate_limit_from_g)
@uuid_gen
@json_validate(filter=['home_id','centroid','beds','baths','size'])
def calculate_rent():
  """
    For investment application
    request args:
       as following
       home_id,"589908808", str
       url: "https://www.zillow.com/homedetails/30-Dorset-Dr-Kissimmee-FL-34758/46315662_zpid/"
       centroid,"47.6293733,-122.4280742", str
       yearbuilt, 1923,int
       rent,2000,int
       rent_estimate,int
       beds,3,int
       baths,3.5,float
       size,2424,float
       roomtype,'Single Family',str
  """
  rule = g.current_rule
  incoming = request.get_json()


  if incoming.get('home_id') == '0xf1':
      logger.error("Zillow front-end structure has changed. Error extracting information. User IP:{}, Url:{}".format(get_ipaddr(), incoming['url']))
      return jsonify(**incoming)

  if incoming.get('home_id') == '0xf2':
      logger.error("User has requested a rent property. User IP:{}, Url:{}".format(get_ipaddr(), incoming['url']))
      return jsonify(**incoming)

  if incoming.get('source_name','zillow')=='zillow':
    logger.warning("Business: user ip:{} request address:{},home_id:{},with_editting:{},".format(get_ipaddr(),
                                                                                                         incoming.get("addr"),
                                                                                                         incoming['home_id'],
                                                                                                         incoming.get('changed')))

  item = {}
  if incoming['home_id']:
      item['home_id'] = incoming['home_id']
      item['source_name'] = incoming.get('source_name', 'zillow')
      new_item = home_cache[item['home_id']+'_'+item['source_name']]
      if new_item and not incoming.get('changed'):
          return jsonify(**json.loads(new_item))

  try:
    item['fixme'] = incoming.get('fixme',False)
    item['centroid'] = get_location(incoming['addr']) if not incoming['centroid'] else incoming['centroid']
    item['url'] = incoming.get('url')
    item['address'] = incoming['addr']
    item['state'] = incoming.get('state')
    item['zipcode'] = incoming.get('zipcode')
    item['city'] = incoming.get('city')
    item['addr_city'] = incoming.get('addr_part')
    if item['addr_city']:
      s = item['addr_city'].split(',')
    if not item['city'] and "s" in locals().keys():
      item['city'] = s[0].strip()
    if not item['state'] and "s" in locals().keys():
      item['state'],item['zipcode'] = s[1].strip().split(" ")[0],s[1].strip().split(" ")[-1]
    item['Beds'] = incoming['beds']
    item['Baths'] = incoming['baths']
    item['RoomType'] = incoming.get('roomtype')
    item['size'] = int(incoming['size'])
    item['yearbuilt'] = incoming.get('yearbuilt')
    item['description'] = incoming.get('description')
    if incoming.get('status_details') and "$" in incoming['status_details']:
      item['status_details'] = incoming['status_details'].split('$')[0].strip()
    else:
      item['status_details'] = incoming.get('status_details')

    stats_para_text = incoming.get('status_icon') or ""
    if "for-rent" in stats_para_text:
      item['status'] = 1
    elif "for-sale" in stats_para_text:
      item['status'] = 2
    elif "off-market" in stats_para_text:
      item['status'] = 3
    elif "-sold" in stats_para_text:
      item['status'] = 4
    elif "pre-market" in stats_para_text:
      item['status'] = 5
    else:
      item['status'] = 6

    item['lot_size'] = incoming.get('lot_size')
    item['pict_urls'] = incoming.get('pict_urls')
    item['listing_price'] = int(''.join(incoming['listing_price'].split('$')[1].split('    ')[0].split(','))) if not incoming.get('changed') else float(incoming['listing_price'])
  except Exception as e:
    logger.error("Engineer:parse room information error happened,{}".format(e))

  try:
    new_item = process_item(item,rule, incoming=incoming)
  except:
    app.logger.warning("something uncommon problem here ")
    new_item = None

  if not new_item:
    item['Suggested_Rent'] = 'No Data'
    item['Return'] = 'No Data'
    item['Revenue'] = 'No Data'
    item['Ratio'] = 'No Data'
    item['Irr'] = 'No Data'
    item['Appr'] = 'N/A'
    item['Cap'] = 'No Data'
    item['Score'] = 'No Data'
    item['neighbor_id'] = 'No Data'
    item['name'] = 'Not Applied'
    item['crime'] = 'Not Applied'
    item['demographic'] = 'Not Applied'
    item['real_estate'] = 'Not Applied'
    item['overview'] = 'Not Applied'
    item['school'] = 'No Data'
    item['Median_Price'] = 'No Data'
    item['Median_Revenue'] = 'No Data'
    item['Median_Appr'] = 'No Data'
    item['Median_Cap'] = 'No Data'
    item['Median_Ratio'] = 'No Data'
    item['Median_Score'] = 'No Data'
    item['Addr1'] = 'No Data'
    item['Addr2'] = 'No Data'
    item['Addr3'] = 'No Data'

    item['first_address'] = 'No Data'
    item['second_address'] = 'No Data'
    item['third_address'] = 'No Data'

    item['rent_score'] = 'No Data'
    item['appr_score'] = 'No Data'
    item['risk_score'] = 'No Data'
    item['cap_score'] = 'No Data'
    item['cost_score'] = 'No Data'
    item['nm_rent'] = 'No Data'
    item['nm_cost'] = 'No Data'
    item['nm_appr'] = 'No Data'
    item['nm_risk'] = 'No Data'
    item['nm_cap'] = 'No Data'

    # added neighborhood houses comparation data
    item['first_price'] = 'No Data'
    item['first_appr'] = 'No Data'
    item['first_cash'] = 'No Data'
    item['second_price'] = 'No Data'
    item['second_appr'] = 'No Data'
    item['second_cash'] = 'No Data'
    item['third_price'] = 'No Data'
    item['third_appr'] = 'No Data'
    item['third_cash'] = 'No Data'

    logger.error("Engineer:No data provided for propery address:{}".format(item['address']))
    return jsonify(**item)

  neighbor_info = get_neighborhood(item)
  new_item['name'] = neighbor_info['name']
  new_item['crime'] = neighbor_info['crime']
  new_item['demographic'] = neighbor_info['demographic']
  new_item['real_estate'] = neighbor_info['real_estate']
  new_item['overview'] = neighbor_info['overview']
  new_item['school'] = neighbor_info['school']

  # cache home information
  if not incoming.get('changed') and incoming['home_id']:
    home_cache.set_key_value(name=item['home_id']+'_'+item['source_name'],value=json.dumps(new_item),expiration=60*60*24)
  return jsonify(**new_item)

def process_item(item,rule,incoming):

  # get nearby rooms
  NEARBY_RANGE_KM = "2mi"
  NEARBY_RANGE_SCORE = "3mi"
  ROOMS_LENGTH = 1000     # return 20 rooms nearby the centroid
  #rent_status = 1
  query = {
            "query": {
              "bool": {
                "must": [],
                "filter": {
                    "geo_distance" : {
                              "distance" : NEARBY_RANGE_KM,
                              "location_point" : item['centroid'],
                          }
                },
                #"must": [{"match_phrase":{"status":rent_status}}],
                "must_not": [{"match_phrase":{"room_type":{"query": ""}}}]
              }
            },
            "sort":[
              {
                "_geo_distance" : {
                  "location_point" : item['centroid'],
                  "order": "asc",
                  "unit": "mi"
                }
              }
            ]
          }

  query_score = {
            "query": {
              "bool": {
                "must": [],
                "filter": {
                    "geo_distance" : {
                              "distance" : NEARBY_RANGE_SCORE,
                              "location_point" : item['centroid'],
                          }
                },
                #"must": [{"match_phrase":{"status": 2}}],
                "must_not": [{"match_phrase":{"room_type":{"query": ""}}}]
              }
            },
            "sort":[
              {
                "_geo_distance" : {
                  "location_point" : item['centroid'],
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
                  _source_include=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True),
                  _source_exclude=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True)
                  )

  res_score = es.search(index=HOME_INDEX,
                   doc_type=HOME_TYPE,
                   body=query_score,
                   size=ROOMS_LENGTH,
                   _source_include=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True),
                   _source_exclude=EsqueryHelper.config_include_or_exclude_field_from_rule(rule,exclude=True)
                   )


  rent = calcrent(res, item)

  if rent == 'N/A':
      return None



  else:
      item['Suggested_Rent'] = calcrent(res, item) if not incoming.get('rent') else float(incoming['rent'])
      item['Return'] = '%.2f' % float(12 * item['Suggested_Rent'])
      item['Revenue'] = '%.2f' % float(12 * item['Suggested_Rent'] - 0.035 * item['listing_price'])
      item['Ratio'] = '%.2f' % float((12 * item['Suggested_Rent'] / item['listing_price']) * 100)
      item['Irr'] = '%.2f' % cashflow(item['listing_price'], item['Suggested_Rent'])
      try:
        item['Appr'] = '%.2f' % calcappr(res, item) if not incoming.get('appr') else float(incoming['appr'])
      except TypeError as e:
        #app.logger.warning(e)
        return None

      item['Cap'] = '%.2f' % (float(item['Appr']) + float(item['Ratio']) - 3.5)

  if item['Appr'] == 'N/A':
      return None

  nearest_items_in_db = []
  if res_score['hits']['hits'] and res_score['hits']['hits'].__len__()>5:
    for i in range(5):
      nearest_item_in_db = res_score['hits']['hits'][i]['_source']
      if nearest_item_in_db.get('area') and nearest_item_in_db['area'].get('id'):
        item['area_id'] = nearest_item_in_db['area']['id']

      if nearest_item_in_db.get('neighborhood') and nearest_item_in_db['neighborhood'].get('id'):
        item['neighborhood_id'] = nearest_item_in_db['neighborhood']['id']
        break


  data = calcscore(res_score, item)

  if data == 'N/A':
      return None

  item['Score'] = data['score']
  item['Median_Price'] = '%.2f' % (data['price'])
  item['Median_Revenue'] = '%.2f' % (data['revenue'])
  item['Median_Appr'] = '%.2f' % (data['appr'])
  item['Median_Cap'] = '%.2f' % (data['cap'])
  item['Median_Ratio'] = '%.2f' % (data['ratio'])
  item['Median_Score'] = '%.2f' % (data['median_score'])
  item['Addr1'] = data['first']
  item['Addr2'] = data['second']
  item['Addr3'] = data['third']

  item['first_address'] = data['first_address']
  item['second_address'] = data['second_address']
  item['third_address'] = data['third_address']

  item['rent_score'] = data['rent-score']
  item['appr_score'] = data['appr-score']
  item['risk_score'] = data['risk-score']
  item['cap_score'] = data['cap-score']
  item['cost_score'] = data['cost-score']
  item['nm_rent'] = data['nm-rent']
  item['nm_cost'] = data['nm-cost']
  item['nm_appr'] = data['nm-appr']
  item['nm_risk'] = data['nm-risk']
  item['nm_cap'] = data['nm-cap']

  # added neighborhood houses comparation data
  item['first_price'] = '%.2f' % data['first_price']
  item['first_appr'] = '%.2f' % data['first_appr']
  item['first_cash'] = '%.2f' % data['first_cash']
  item['second_price'] = '%.2f' % data['second_price']
  item['second_appr'] = '%.2f' % data['second_appr']
  item['second_cash'] = '%.2f' % data['second_cash']
  item['third_price'] = '%.2f' % data['third_price']
  item['third_appr'] = '%.2f' % data['third_appr']
  item['third_cash'] = '%.2f' % data['third_cash']

 # print("IT", item)

  if item.get('fixme') and not incoming.get('changed'):
    upsert_to_es(item)

  # calculate started
  return item


def upsert_to_es(item):
  # preprocess
  item['centroid_point'] = item['centroid']
  item['centroid_map'] = {
                            "type": "point",
                            "coordinates": list(map(lambda x:float(x),item['centroid'].split(',')[::-1]))
                          }
  item['Appr_des'] = round(float(item['Appr'])/100,6)


  # define mapping
  mapping = {
              "Suggested_Rent": "rent",
              "address": "addr",
              "Beds": "beds",
              "Baths": "baths",
              "listing_price": "house_price_dollar",
              "RoomType" :"room_type",
              "size": "size",
              "Score": "score",
              "centroid_point": "location_point",
              "centroid_map": "location",
              "home_id": "source_id",
              "source_name": "source_name",
              "Appr_des": "increase_ratio",
              "yearbuilt": "year_built",
              "city": "city",
              "lot_size": "lot_size",
              "state": "state",
              "zipcode": "zipcode",
              "pict_urls": "pict_urls",
              "description": "description",
              "status":"status",
              "status_details":"status_details"
            }

  # exchange item
  item_new = {}
  for k,v in mapping.items():
    item_new[v] = item[k]

  # more field + financial data
  item_new['sale_rent_ratio']=round(1/float(item['Ratio']),6)
  item_new['area'] = {"id":item.get('area_id')}
  item_new['neighborhood'] = {"id":item.get('neighborhood_id')}
  item_new['score_radar'] = {"score_appreciation":60,
                              "score_cost":60,
                              "score_rental":60,
                              "score_anti_risk":60,
                              "score_airbnb":60
                            }

  item_new['score'] = item['Score']
  item_new['score_radar']['score_appreciation'] = item['appr_score']*5
  item_new['score_radar']['score_cost'] = item['cost_score']*5
  item_new['score_radar']['score_rental'] = item['rent_score']*5
  item_new['score_radar']['score_anti_risk'] = item['risk_score']*5
  item_new['score_radar']['score_airbnb'] = item['cap_score']*5  #TODO

  item_new['rental_return_rate'] = float(item['Ratio'])/100
  item_new['rental_return_rate_net'] = float(item['Ratio'])/100
  item_new['rental_return_annual'] = item['Revenue']

  item_new['insurance'] = item['Suggested_Rent'] * 0.056
  item_new['maintainance'] = item['listing_price'] * 0.04
  item_new['tax'] = item['listing_price'] * 0.02725
  item_new['pm_long'] = item['Suggested_Rent'] * 0.08
  item_new['pm_short'] = 0
  item_new['irr'] = float('%.2f' % float(item['Irr']))

  # upsert to elasticsearch
  try:
    es.update(index=HOME_INDEX,
            doc_type=HOME_TYPE,
            id=str(item_new['source_id']) +'_'+ item_new['source_name'],
            body={'doc':item_new,
                  'doc_as_upsert':True}
            )
  except Exception as e:
    logger.warn("error when update zillow id:{},{}".format(item_new['source_id'],e))




def get_neighborhood(item):

    #set up the connection
    city = item['city']
    center = item['centroid']
    res = db.session.execute("select centroid, name, crime, demographic, real_estate, overview, school, city from neighbor where city = '%s'" % city)
    data = res.fetchall()
    df = pd.DataFrame(columns = ['centroid', 'name', 'crime', 'demographic',
     'real_estate', 'overview', 'school', 'city'])

    columns_zc = ['centroid', 'name', 'crime', 'demographic',
     'real_estate', 'overview', 'school', 'city']

    for i in range(0, 8):
        df[columns_zc[i]] = list(data[j][i] for j in range(0, len(data)))

    centers = list('(' + item + ')' for item in df['centroid'])
    df['centroid'] = centers
    distance = list(dist.vincenty(center, item).miles for item in df['centroid'])
    df['distance'] = distance
    result = df.sort_values('distance', ascending = True)
    result = result.loc[result.index.values[0]]
    response = {

    "name" : result['name'],
    "crime" : result['crime'],
    "demographic" : result['demographic'],
    "real_estate" : result['real_estate'],
    "overview" : result['overview'],
    "school" : result['school']

    }

    return response
