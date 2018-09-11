# -*- coding: UTF-8 -*-
from flask import request, jsonify, g
from flask import Blueprint
from ..models import User, Picture, Rule
from sqlalchemy.exc import IntegrityError
from ..utils.query import QueryHelper
from ..utils.esquery import EsqueryHelper
from ..utils.auth import requires_auth, json_validate, generate_token
from ..utils.helper import uuid_gen
from ..utils.roles import ADMIN

from index import app,db

admin = Blueprint('admin', __name__)
logger = app.logger

ONE_CENTARY = 100*365*86400

@admin.route("create_user", methods=["POST"])
@uuid_gen
@json_validate(filter= ["name","rules"])
@requires_auth(role=ADMIN)
def create_user():
  incoming = request.get_json()
  rules_ids = [int(i) for i in incoming['rules'].split(',')]
  rules = Rule.query.filter(Rule.id.in_(rules_ids)).all()
  new_user = User(
    name = incoming["name"],
  )
  new_user.rules = rules
  db.session.add(new_user)

  try:
    db.session.commit()
  except IntegrityError as e:
    logger.warning("Repeated User:{}".format(incoming["name"].encode('utf-8')))
    return jsonify(message="User with that name has existed"), 409
  return jsonify(
    token=generate_token(new_user,expiration=ONE_CENTARY),id=new_user.id
  ), 200

@admin.route("get_token", methods=["POST"])
@uuid_gen
@requires_auth(role=ADMIN)
def get_token():
  # admin can get any token of any user
  incoming = request.get_json()
  if not (incoming.get('name') or incoming.get('id')):
    return jsonify(success=False,message='Parameters not compatible'), 400

  if incoming.get("name"):
    user = User.get_user_with_name_or_id(name=incoming['name'])
  elif incoming.get("id"):
    user = User.get_user_with_name_or_id(id=incoming['id'])
  if user:
    return jsonify(
      token=generate_token(user,expiration=ONE_CENTARY),id=user.id
    )

  return jsonify(error=True), 403
