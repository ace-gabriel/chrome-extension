import string
import random
import uuid
import flask
from functools import wraps
import re

def id_generator(size=6, chars=string.digits):
  return ''.join(random.choice(chars) for x in range(size))

def uuid_gen(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    flask.g.uuid = str(uuid.uuid4()).split("-")[0]
    return f(*args, **kwargs)
  return decorated

def allowed_file(filename, allowed_extensions):
  return '.' in filename and \
         filename.rsplit('.', 1)[1].upper() in allowed_extensions
