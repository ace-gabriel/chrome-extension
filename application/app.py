# -*- coding: utf-8 -*-

from flask import request, render_template, jsonify, url_for, redirect, g
from .models import User, Picture
from index import app, db, celery, es
from sqlalchemy.exc import IntegrityError
from .utils.auth import generate_token, requires_auth, verify_token, verify_sms_code, encrypt_simple_info, decrypt_simple_info, user_role, json_validate
from .utils.auth import decrypt_certificate
from .utils.helper import id_generator, uuid_gen, allowed_file
from .utils.comm import send_sms, send_landlord_referral_email
from .utils.s3 import s3_upload, s3_get_url
from .utils.referral import create_referral_code, ReferralCodeException, LANDING_PAGE_URL, track_referral, referral_stats, referrer_info
from random import shuffle
from .utils.query import QueryHelper
from .utils.esquery import EsqueryHelper
from .utils.roles import CUSTOMER, ADMIN, EVERYONE
import tasks
import datetime
from dateutil.relativedelta import relativedelta
import urllib
import requests
import json
import random
from .utils.type import LINKEDIN_TYPE
from .settings import HOME_INDEX,HOME_TYPE

from application.main.home import home as home_blueprint
from application.main.city import city_bp as city_blueprint
from application.main.search import search_bp as search_blueprint
from application.main.neighbor import neighbor_bp as neighbor_blueprint
from application.main.group import group_bp as group_blueprint
from application.main.nearby import nearby_bp as nearby_blueprint

app.register_blueprint(home_blueprint, url_prefix='/api')
app.register_blueprint(city_blueprint, url_prefix='/api')
app.register_blueprint(search_blueprint, url_prefix='/api')
app.register_blueprint(neighbor_blueprint,url_prefix='/api')
app.register_blueprint(group_blueprint,url_prefix='/api')
app.register_blueprint(nearby_blueprint,url_prefix='/api')

# admin
from application.main.admin import admin as admin_blueprint
app.register_blueprint(admin_blueprint, url_prefix='/api/admin/')

# endpoint
from application.endpoint.nation import ep_nation_bp as ep_nation_blueprint
from application.endpoint.city import ep_city_bp as ep_city_blueprint
from application.endpoint.msa import ep_msa_bp as ep_msa_blueprint
from application.endpoint.state import ep_state_bp as ep_state_blueprint
from application.endpoint.neighbor import ep_neighbor_bp as ep_neighbor_blueprint
from application.endpoint.zipcode import ep_zipcode_bp as ep_zipcode_blueprint
app.register_blueprint(ep_nation_blueprint, url_prefix='/api')
app.register_blueprint(ep_city_blueprint, url_prefix='/api')
app.register_blueprint(ep_msa_blueprint, url_prefix='/api')
app.register_blueprint(ep_state_blueprint, url_prefix='/api')
app.register_blueprint(ep_neighbor_blueprint, url_prefix='/api')
app.register_blueprint(ep_zipcode_blueprint, url_prefix='/api')

# different client
from application.main.clients.apocalypse import apocalypse_bp as apocalypse_blueprint
from application.main.clients.investment import investment_bp as investment_blueprint
from application.main.clients.chrome import feedback_bp as feedback_blueprint
from application.main.clients.chrome import chrome_bp as chrome_blueprint
from application.main.clients.city import city_bp as city_blueprint
from application.main.kafka import kafka_bp as kafka_blueprint
app.register_blueprint(apocalypse_blueprint,url_prefix='/api')
app.register_blueprint(investment_blueprint,url_prefix='/api')
app.register_blueprint(chrome_blueprint,url_prefix='/api')
app.register_blueprint(feedback_blueprint, url_prefix='/api')
app.register_blueprint(city_blueprint,url_prefix='/api')
app.register_blueprint(kafka_blueprint,url_prefix='/api')

ONE_MINUTE = 60
HALF_MINUTE = 30
KB = 1024
MB = KB * KB
KEYS_TO_POP = ["_sa_instance_state", "id", "created_at", "updated_at"]

logger = app.logger

@app.route('/', methods=['GET'])
@uuid_gen
def index():
  return render_template('index.html')


@app.route('/<path:path>', methods=['GET'])
@uuid_gen
def any_root_path(path):
  return render_template('index.html')

###############################################################################
# Uploads
###############################################################################
@app.route("/api/upload_avatar", methods=["POST"])
@uuid_gen
@requires_auth(role=EVERYONE)
def upload_avatar():
  user_id = g.current_user['id']
  if 'file' not in request.files:
    return jsonify(message="No file part"), 400
  file = request.files['file']
  if file.filename == '':
    return jsonify(message="No selected file"), 400
  key = s3_upload(file)
  picture = Picture(0, user_id, key)
  db.session.add(picture)
  db.session.commit()
  return jsonify(filename=key)

@app.route("/api/get_avatar_url", methods=["GET"])
@uuid_gen
@requires_auth(role=EVERYONE)
def get_avatar_url():
  user_id = g.current_user['id']
  picture = QueryHelper.get_picture_with_pic_id(pic_id=user_id)
  if not picture:
    return jsonify(url=None)
  url = picture.filename
  if picture.type == PIC_AVATAR_TYPE:
    key = picture.filename
    url = s3_get_url(key)
  return jsonify(url=url)

@app.route("/api/upload_file", methods=["POST"])
@uuid_gen
@requires_auth(role=EVERYONE)
def upload_file():
  ALLOWED_EXTENSIONS = set(['PDF', 'PNG', 'JPG'])
  user_id = g.current_user['id']
  item_id = request.form.get('item_id', None)
  if 'file' not in request.files:
    return jsonify(message="No file part"), 400
  file = request.files['file']
  if file.filename == '':
    return jsonify(message="No selected file"), 400
  if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
    return jsonify(message="File type out of range"), 400
  size = len(file.read())
  if size > 15 * MB:
    return jsonify(message="File size exceeded"), 400

  key = s3_upload(source_file=file, upload_dir=app.config['S3_UPLOAD_PDF_DIRECTORY'])

  new_user = QueryHelper.add_file(type=FILE_S3_TYPE,
    foreign_id=user_id, item_id=item_id, filename=key, raw_name=file.filename)
  if not new_user:
    return jsonify(success=False,
      message='file upload failed'), 409

  return jsonify(filename=key, id=new_user.id)


@app.route('/api/delete_file', methods=["POST"])
@uuid_gen
@requires_auth(role=EVERYONE)
def delete_file():
  incoming = request.get_json()
  if incoming is None:
    return jsonify(success=False,
      message='Parameters not compatible'), 400
  user_id = g.current_user['id']
  is_success = QueryHelper.del_file(type=FILE_S3_TYPE, foreign_id=user_id, item_id=incoming['item_id'])

  if not is_success:
    return jsonify(success=False,
      message='delete file failed'), 409
  return jsonify(success=True)


@app.route('/api/test', methods=['GET'])
def test():
    from application.region import RegionAbstraction
    from application.region.msa import MsaRegion
    from application.region.state import StateRegion
    from application.region.city import CityRegion
    region = MsaRegion(geoid='40080')
    #region = StateRegion(geoid='53')
    abstraction = RegionAbstraction(region)
    result = abstraction.get_region_geo()
    result = abstraction.get_child_regions()
    #result = abstraction.get_parent_region()
    return jsonify(success=True,result=result)
