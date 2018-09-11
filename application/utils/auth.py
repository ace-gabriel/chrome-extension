# -*- coding: utf-8 -*-

from functools import wraps, partial
from flask import request, g, jsonify
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature
from index import app, db, limiter, count
from ..models import User, Administrator, Rule
from .roles import CUSTOMER, ADMIN, EVERYONE
import base64
import datetime

TWO_WEEKS = 1209600
FIVE_MINUTES = 300

def user_role(user):
  if Administrator.is_user_admin(user.id):
    return 1
  return 0

def generate_token(user, expiration=TWO_WEEKS):
  s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
  # user role
  role = user_role(user)

  token = s.dumps({
    'id': user.id,
    'name': user.name,
    'role': role,
  }).decode('utf-8')
  return token

def verify_token(token):
  s = Serializer(app.config['SECRET_KEY'])
  try:
    data = s.loads(token)
  except (BadSignature, SignatureExpired):
    return None
  return data

def decrypt_certificate(cert, expiration=FIVE_MINUTES):
  s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
  token = s.dumps({
    'cert': cert
  }).decode('utf-8')
  return token

def verify_sms_code(phone, country, code, expiration=FIVE_MINUTES):
  phone = Phone.get_phone_with_phone_and_country(phone, country)
  if phone and phone.verification_code == code \
      and phone.verification_code_created_at + datetime.timedelta(seconds=expiration) > datetime.datetime.utcnow():
    return True 
  return False

# role: an array
# None any role, 0 landlord, 1 realtor 2 admin 
# expecting an array that contains the roles
def requires_auth(f=None, role=ADMIN):
  if not f:
    return partial(requires_auth, role=role)
  @wraps(f)
  def decorated(*args, **kwargs):
    token = request.headers.get('Authorization', None)
    if token:
      string_token = token.encode('ascii', 'ignore')
      user = verify_token(string_token)
      if user:
        if role is None or user["role"] in role:
          g.current_user = user
          return f(*args, **kwargs)

    return jsonify(message="Authentication is required to access this resource"), 401
  return decorated

def requires_rule(f=None):
  if not f:
    return partial(requires_rule)
  @wraps(f)
  def decorated(*args,**kwargs):
    token = request.headers.get('Authorization', None)
    if token:
      string_token = token.encode('ascii', 'ignore')
      user = verify_token(string_token)
      if user:
        user_db = User.get_user_with_name_or_id(id=user['id'])
        for r in user_db.rules:
          if r.api_id==request.path:
            g.current_rule = r
            g.limit = ";".join([i for i in [r.throttle_day,r.throttle_hour,r.throttle_min] if i])
            if r.statistics:
              count.incr(r,user_db.name,action=1)
            return f(*args, **kwargs)
        return jsonify(message="Rule is required to access this resource"), 401
    return jsonify(message="Authentication is required to access this resource"), 401
  return decorated

def encrypt_simple_info(string):
  return base64.encodestring(string)

def decrypt_simple_info(string):
  return base64.decodestring(string)

def json_validate(f=None, filter=[]):
  if not f:
    return partial(json_validate, filter=filter)
  @wraps(f)
  def decorated(*args, **kwargs):
    incoming = request.get_json() or request.args
    if incoming is None:
      return jsonify(success=False,
        message='Parameters not compatible'), 400
    for item in filter:
      if item not in incoming.keys():
        return jsonify(success=False,
        message='Parameters not compatible'), 400
    return f(*args, **kwargs)
  return decorated

def json_validate_logic(f=None, filter_conjunction=[], filter_disjunction=[]):
  if not f:
    return partial(json_validate_logic, filter_conjunction = filter_conjunction, filter_disjunction = filter_disjunction)
  @wraps(f)
  def decorated(*args, **kwargs):
    if request.method =='POST':
      incoming = request.get_json()
    elif request.method =='GET':
      incoming = request.args
    if incoming is None:
      return jsonify(success=False,
        message='Parameters not compatible'), 400

    for item in filter_conjunction:
      if item not in incoming.keys():
        return jsonify(success=False,
        message='Parameters not compatible'), 400

    interaction = [item for item in incoming.keys() if item in filter_disjunction]
    if not interaction:
        return jsonify(success=False,
        message='Parameters not compatible'), 400

    g.incoming = incoming
    return f(*args, **kwargs)
  return decorated