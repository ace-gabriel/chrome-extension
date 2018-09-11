import requests
import re
import json
import time
import datetime
from calendar import monthrange

ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'

def get_html(url):
  r = requests.get(url,headers={'user-agent':ua})
  return r.text

def get_history_url(html,zpid):
  url = None
  part_url = re.search(r'(https://ppz.zillowstatic.com:443/hdp_chart/render.json.+?)"',html)
  if part_url:
    url = part_url.group(1)+"&zpid={zpid}&m=1&t=tenYears&jsonp=YUI.Env.JSONP.paparazzi{zpid}&size=standard&showForecast=true&signedIn=true".format(zpid=zpid)
  return url

def get_history_data(html):
  data = re.search(r'paparazziData": (\[.+"Home"}\]),',html)
  if data:
    return data.group(1)
  else:
    return []


def return_price_point_trend(url,zpid):
  html = get_html(url)
  if html:
    history_url = get_history_url(html,zpid)

  # price html
  html_price_history = get_html(history_url)
  json_data = get_history_data(html_price_history)
  if isinstance(json_data,unicode):
    json_data = json.loads(json_data)
  else:
    return {}
  threeLine = {}
  for dic in json_data:
    data = {}
    line = []
    if dic['name'] == 'Sale':
      continue
    
    for ii in dic['data']:
      d = {}
      d['x'] = ii['xValue']
      d['y'] = ii['yValue']
      # print ii['xValue'], ii['yValue']
      
      point = {}
      y_m = time.strftime('%Y-%m', time.gmtime(d['x'] / 1000))
      point['price'] = d['y']
      point['year'] = y_m[:4]
      point['month'] = y_m[-2:]
      # print point
      line.append(point)

    dist = line[-1]['price'] - line[-2]['price']
    date = datetime.datetime(int(line[-1]['year']), int(line[-1]['month']), 1)
    N = 3
    for mon in range(N):
      point = {}
      date += datetime.timedelta(days=monthrange(date.year, date.month)[1])
      # print date.year, date.month
      point['price'] = line[-1]['price'] + dist
      point['year'] = str(date.year)
      m = str(date.month)
      point['month'] = (2 - len(m)) * '0' + m
      line.append(point)
      # predict to 2019.02
      if point['year'] == '2019' and point['month'] == '02':
        break
      
    data['name'] = dic['name']
    data['regionType'] = dic['regionType']
    data['data'] = line
    threeLine[dic['regionType']] = data

  return threeLine
