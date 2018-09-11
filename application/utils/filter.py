import datetime

from application.settings import DEFAULT_STATUS, VILLASORT, APARTSORT, ONLINE_DAY
from application.settings import INCREASE_RATIO_MAX,RENTAL_INCOME_RATIO_MAX,AIRBNB_RENTAL_RATIO_MAX 
from application.settings import UPPER_BED_SHOW, UPPER_HOUSE_PRICE_SHOW

def filter_city(body, area_ids=[], val_expect=[], rent_expect=[], near_businiess='', near_hospital='', beds='', baths='', area=[],
                house_price=[], status='', isApartment='', isVilla='', online_day='',zipcode='',bedroom='',price_range='',upper_bed=None,house_price_range=None,upper_house_price=None):
  # return sample as following
  '''
    [
     {'terms': 
        {'area.id': ['40140', '41860', '38900', '38060', '36740', '38300', '19740', '26420', '19820', '33100', '29820']}
      }, 
      {'term': {'beds': 4}}, 
      {'range': {'increase_ratio': {'gte': -100.0, 'lte': 0.1}}},
      {'range': {'rental_income_ratio': {'gte': -100.0, 'lte': 0.157}}},
      {'term': {'status': 2}}
    ]

   Upper structure as following
   {
    "query": {
      "bool": {
        "must": [],
        "filter": [],
        "should": [],
        "must_not": []
      }
    }
  }
  '''
  if not status:status=DEFAULT_STATUS
  room_type=[]
  if isApartment =='1':
    for each in APARTSORT:
      room_type.append(each)
  if isVilla=='1':
    for each in VILLASORT:
      room_type.append(each)
  if zipcode:
    body.append({'term': {'zipcode': zipcode}})
  if ONLINE_DAY.has_key(online_day):
    if ONLINE_DAY[online_day][1]== 'lt':
      body.append({"range":{"online_date":{"gt" : str(datetime.datetime.now())[:10] +"||-" + ONLINE_DAY[online_day][0] + "d"}}})
    if ONLINE_DAY[online_day][1]== 'gt':
      body.append({"range":{"online_date":{"lt" : str(datetime.datetime.now())[:10] +"||-" + ONLINE_DAY[online_day][0] + "d"}}})

  if area_ids:
    body.append({'terms':{'area.id':area_ids}})
  if beds:
    body.append({'term': {'beds': int(beds)}})
  if baths:
    body.append({'term': {'baths': int(baths)}})
  if area[0] and area[1]:
    body.append({'range': {'size': {"gte": float(area[0]), "lte": float(area[1])}}})

  if val_expect[1]:
    body.append({'range': {'increase_ratio': {"gte": float(val_expect[0]), "lte": float(val_expect[1])}}})
  else:
    body.append({'range': {'increase_ratio': {"gte": float(val_expect[0] or -100), "lte": float(INCREASE_RATIO_MAX)}}})

  if rent_expect[1]:
    body.append({'range': {'rental_income_ratio': {"gte": float(rent_expect[0]), "lte": float(rent_expect[1])}}})
  else:
    body.append({'range': {'rental_income_ratio': {"gte": float(rent_expect[0] or -100), "lte": float(RENTAL_INCOME_RATIO_MAX)}}})

  if house_price[1]:
    body.append({'range': {'house_price_dollar': {"gte": float(house_price[0] or 0), "lte": float(house_price[1])}}})
  if status:
    body.append({'term':{'status':int(status)}})
  if room_type:
    body.append({'terms': {'room_type':room_type}})
  else:
    t = ['Single Family','Multi Family','Townhouse','Apartment']
    should_type = []
    for i in t:
      should_type.append({'match_phrase':{"room_type.keyword":i}})
    body.append({"bool":{"should":should_type,"minimum_should_match":1}})

  if bedroom:
    # multiple beds options
    bedroom_array = bedroom.split(',')

    if upper_bed:
      upper_bed = int(upper_bed)
    else:
      upper_bed = UPPER_BED_SHOW
    body.append(config_ranged_beds(bedroom_array,upper_bed))

  if house_price_range:
    house_price_array = house_price_range.split(',')

    if upper_house_price:
      upper_house_price = int(upper_house_price)
    else:
      upper_house_price = UPPER_HOUSE_PRICE_SHOW
    body.append(config_ranged_house_price(house_price_array,upper_house_price))

  #print body
  return body


def sort_result(sort_val, sort_price, sort_od, sort_cz,sort_year):
  body = []

  if sort_price == '1': body.append({"house_price_dollar": {"order": "desc"}})
  if sort_price == '0': body.append({"house_price_dollar": {"order": "asc"}})
  if sort_od == '1': body.append({"online_date": {"order": "desc"}})
  if sort_od == '0': body.append({"online_date": {"order": "asc"}})
  if sort_cz == '1': body.append({"rental_income_ratio": {"order": "desc"}})
  if sort_cz == '0': body.append({"rental_income_ratio": {"order": "asc"}})
  if sort_year == '0': body.append({"year_built":{"order":"asc"}})
  if sort_year == '1': body.append({"year_built":{"order":"desc"}})
  if sort_val == '1': body.append({"total_ratio": {"order": "desc"}})
  if sort_val == '0': body.append({"total_ratio": {"order": "asc"}})
  return body

def config_ranged_beds(bedroom_array,upper_bed):
  # Is it really necessary to choose multiple beds ???
  bed_range = [int(float(i)) for i in bedroom_array if i]
  bed_seg_should = []
  for i in bed_range:
    if i < upper_bed:
      s = {"range":{"beds":{"gte":int(i),"lt":int(i+1)}}}
    else:
      s = {"range":{"beds":{"gte":upper_bed,"lt":None}}}
    bed_seg_should.append(s)

  filter_beds = {
          "bool": {
            "should": bed_seg_should,
            "minimum_should_match": 1
          }
        }
  return filter_beds

def config_ranged_house_price(house_price_array,upper_house_price):
  house_price_range = [i.split('-') for i in house_price_array if i]
  house_seg_should = []
  #print house_price_range, upper_house_price
  for p_l,p_u in house_price_range:
    if float(p_l) >= upper_house_price:
      s = {"range":{"house_price_dollar":{"gte":float(upper_house_price),"lt":None}}}
    else:
      #print p_l,p_u
      s = {"range":{"house_price_dollar":{"gte":float(p_l),"lt":float(p_u)}}}
    house_seg_should.append(s)

  filter_house = {
          "bool": {
            "should": house_seg_should,
            "minimum_should_match": 1
          }
        }
  return filter_house
