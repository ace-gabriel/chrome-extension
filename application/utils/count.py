class Count(object):
  VISIT_ACTION = 1

  ACTION_MAP = {
    1: "visit",
  }

  def __init__(self, redis_db):
    self.redis_db = redis_db

  def get(self, rule, company, action=1):
    '''
    if the key exists then return the cache data
    else return None
    '''
    key = self.generate_key(rule, company, action)
    return self.redis_db.get(key)

  def incr(self, rule, company, action=1):
    key = self.generate_key(rule,company,action)
    return self.redis_db.incr(key)

  def decr(self, rule, company, action=1):
    key = self.generate_key(rule,company,action)
    return self.redis_db.decr(key)

  @classmethod
  def generate_key(cls, rule, company, action):
    api = rule.api_id.replace('/','_')
    key = "{}_{}_{}".format(company, cls.ACTION_MAP[action], api)
    return key
