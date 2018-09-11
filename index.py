from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from config import BaseConfig
from flask_bcrypt import Bcrypt
from celery import Celery
import logging
from flask_elasticsearch import FlaskElasticsearch
from flask_redis import FlaskRedis
from application.utils.count import Count
from application.utils.redisDB import RedisDB, HomeCache, CityCache, FeedbackCache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address,get_ipaddr
from werkzeug.contrib.fixers import ProxyFix
from flask_kafka_python import KafkaExtension

app = Flask(__name__,template_folder="./static")
app.config.from_object(BaseConfig)
db = SQLAlchemy(app)
redis_store = FlaskRedis(app)
bcrypt = Bcrypt(app)
es = FlaskElasticsearch(app)
app.wsgi_app = ProxyFix(app.wsgi_app,num_proxies=1)
limiter = Limiter(app,key_func=get_ipaddr,storage_uri=app.config['REDIS_URL'])   # moving average

redis_db_counts = RedisDB(host=app.config['REDIS_SESSION_HOST'], port=app.config['REDIS_SESSION_PORT'], dbname='counts', db=app.config['REDIS_DB'])
home_cache = HomeCache(host=app.config['REDIS_SESSION_HOST'], port=app.config['REDIS_SESSION_PORT'],password=app.config['REDIS_SESSION_PWD'], db=2)
city_cache = CityCache(host=app.config['REDIS_SESSION_HOST'], port=app.config['REDIS_SESSION_PORT'],password=app.config['REDIS_SESSION_PWD'], db=3)
count = Count(redis_db_counts)

kafka_extension = KafkaExtension()
def make_kafka(app):
    app.config.update(
        KAFKA_HOSTS=app.config['KAFKA_HOSTS'],
        KAFKA_TIMEOUT_SECONDS=15
    )
    kafka_extension.init_app(app)
    return app

app = make_kafka(app)


class RequestIdFilter(logging.Filter):
  # This is a logging filter that makes the request ID available for use in
  # the logging format. Note that we're checking if we're in a request
  # context, as we may want to log things before Flask is fully loaded.
  def filter(self, record):
    record.request_id = g.get("uuid")
    return True

def make_celery(app):
  celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
  celery.conf.update(app.config)
  TaskBase = celery.Task
  class ContextTask(TaskBase):
    abstract = True
    def __call__(self, *args, **kwargs):
      with app.app_context():
        return TaskBase.__call__(self, *args, **kwargs)
  celery.Task = ContextTask
  return celery

celery = make_celery(app)
#import application.tasks

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(request_id)s %(message)s'))
app.logger.addHandler(handler)
app.logger.addFilter(RequestIdFilter())
app.logger.handlers.extend(logging.getLogger("gunicorn.log").handlers)
