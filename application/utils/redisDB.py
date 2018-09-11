import redis

class RedisDB(object):

  def __init__(self, host, port, dbname, db):
    self.dbname = dbname
    self.client = redis.StrictRedis(host=host, port=port, db=db)

  def get(self, key):
    '''
    if the key exists then return the cache data
    else return None
    '''
    hexists = self.client.hexists(self.dbname, key)
    if hexists :
      return self.client.hget(self.dbname, key)
    else:
      return None

  def set(self, key, value):
    self.client.hset(self.dbname, key, value)
    return value

  def pure_set(self, key, value):
    return self.client.set(key, value)

  def pure_get(self, key):
    return self.client.get(key)

  def expire(self, key, time):
    return self.client.expire(key, time)

  def lpush(self, key, value):
    return self.client.lpush(key, value)

  def lrem(self, key, value):
    return self.client.lrem(key, 0, value)

  def lrange(self, key, range):
    return self.client.lrange(key, 0, range)

  def sadd(self, key, value):
    return self.client.sadd(key, value)

  def srem(self, key, value):
    return self.client.srem(key, value)

  def smembers(self, key):
    return self.client.smembers(key)

  def incr(self, key):
    self.client.hincrby(self.dbname, key, 1)

  def pure_incr(self, key):
    self.client.incr(key)

  def decr(self, key):
    self.client.hincrby(self.dbname, key, -1)

  def remove_all(self):
    assert self.dbname is not None, 'dbname is None'
    self.client.delete(self.dbname)


class HomeCache(list):

    def __init__(self, host, port, password, db=1):

        list.__init__([])
        self.client = redis.Redis(host=host, port=port, password=password, db=db)

    def __getitem__(self, key):
        '''
        if the key exists then return the cache data
        else return None
        '''
        exists = self.client.exists(name=key)
        if exists :
            return self.client.get(name=key).decode("utf-8")
        else:
            return None

    def __setitem__(self, key, value):
        self.client.set(key, value)
        return value

    def set_key_value(self, name, value, expiration):
        self.client.set(name=name, value=value)
        self.client.expire(name=name, time=expiration)
        return value

class CityCache(list):

    # redis cache for search city result

    def __init__(self, host, port, password, db=3):

        list.__init__([])
        self.client = redis.Redis(host=host, port=port, password=password, db=db)

    def __getitem__(self, key):

        exists = self.client.exists(name=key)
        if exists :
            return self.client.get(name=key).decode("utf-8")
        else:
            return None

    def __setitem__(self, key, value):
        self.client.set(key, value)
        return value

    def set_key_value(self, name, value, expiration):
        self.client.set(name=name, value=value)
        self.client.expire(name=name, time=expiration)
        return value


class FeedbackCache(list):

    # redis cache for search city result

    def __init__(self, host, port, password, db=4):

        list.__init__([])
        self.client = redis.Redis(host=host, port=port, password=password, db=db)

    def __getitem__(self, key):

        exists = self.client.exists(name=key)
        if exists :
            return self.client.get(name=key).decode("utf-8")
        else:
            return None

    def __setitem__(self, key, value):
        self.client.set(key, value)
        return value

    def set_key_value(self, name, value, expiration):
        self.client.set(name=name, value=value)
        self.client.expire(name=name, time=expiration)
        return value

