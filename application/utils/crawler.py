import requests
import json

from index import app

CRAWLER_HOST = app.config["CRAWLER_HOST"]

def web_crawl(addr):
  try:
    r = requests.post(url=CRAWLER_HOST+"/post-addr",json=addr,timeout=10)
    item = json.loads(r.text)
  except:
    item = {'errmsg':'no match found for input addr'}
  finally:
    return item
