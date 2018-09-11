# coding: utf-8

import pickle
# import json
# import types

path = 'application/model/radar_score_20180117/'

def f(x, x_range, score):
  bottom = 20
  y = []
  for i in x:
    if i < x_range[0]:
      pos = 0
    else:
      for j in range(len(x_range)):
        if j == len(x_range) - 1 or \
            i >= x_range[j] and i < x_range[j + 1]:
          pos = j
          break
    s = sum(score[:pos]) + score[pos] * (i - x_range[pos])
    y.append(s + bottom)
  return y


def process_score(house):
  # with open('radar.json', 'r') as fj:
  #   house = json.load(fj)
    # print radar
  
  # print house
  
  score = {
    'score_appreciation': 60,
    'score_cost':         60,
    'score_rental':       60,
    'score_airbnb':       60,
    'score_anti_risk':    60
  }

  with open(path+'scoremodel.pkl', 'rb') as fp:
  # pickle.dump([radar, factor, x_range, score], fopen)
    N = 4

    a = pickle.load(fp)
    if 'increase_ratio' in house and house['increase_ratio'] != None:
      #  房屋增值
      x = house['increase_ratio'] * a[1]
      score['score_appreciation'] = f([x], a[2], a[3])[0]
      # print x, score['score_appreciation']
    
    a = pickle.load(fp)
    if 'house_price_dollar' in house and house['house_price_dollar'] != None:
      # 持有成本
      x = a[1] / house['house_price_dollar']
      # print 'house_price_dollar', house['house_price_dollar']
      score['score_cost'] = f([x], a[2], a[3])[0]
      # print score['score_cost']
      if 'airbnb_rent' in house and house['airbnb_rent'] != None:
        #  短租收益
        a = pickle.load(fp)
        x = house['airbnb_rent'] * 12.0 / house['house_price_dollar'] * a[1]
        score['score_airbnb'] = f([x], a[2], a[3])[0]
        # print score['score_airbnb']

    a = pickle.load(fp)
    if 'rental_income_ratio' in house and house['rental_income_ratio'] != None:
      #  长租收益
      x = house['rental_income_ratio'] * a[1]
      score['score_rental'] = f([x], a[2], a[3])[0]
      # print score['score_rental']
  
  
  if 'neighborhood' in house and 'id' in house['neighborhood'] and house['neighborhood']['id'] != None:
    with open(path+'region_anti_drop.pkl', 'r') as fp:
      #  抗跌能力
      region = pickle.load(fp)
      score_anti = pickle.load(fp)
      if house['neighborhood']['id'] in region:
        # print house['neighborhood']['id']
        i = region.index(house['neighborhood']['id'])
        score['score_anti_risk'] = score_anti[i]
  
  # for i in score:
  #   print '%20s %2.3f ' % (i, score[i])
  
  # check: make sure score in range(20, 100)
  for i in score:
    if score[i] < 20:
      score[i] = 20
    if score[i] > 100:
      score[i] = 100
  
  return score
  

if __name__ == '__main__':
  # README
  print "This is a program calculating house's 5 scores:" \
        "Anti Drop Score," \
        "House Appreciation," \
        "Possess Cost," \
        "Long-term Income" \
        "Short-term Income"
