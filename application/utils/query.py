from ..models import User, Picture, Administrator, Neighborhood, Area
from ..models import File, ExtraFile
from sqlalchemy import and_, or_
from .status import NOTE_USED, NOTE_DISCARDED, UTILITY_USED, UTILITY_DISCARDED, NOTE_TYPE_HOME, NOTE_TYPE_OFFER, NOTE_TYPE_USER, IS_ACTIVE_USED, IS_ACTIVE_DISCARDED
import json
from datetime import datetime, timedelta
import decimal
from flask import jsonify
from index import db, app, es
from ..settings import HOME_INDEX, HOME_TYPE
import sys
from sqlalchemy.exc import DataError, IntegrityError
from dateutil.relativedelta import relativedelta

class QueryHelper(object):
  'You can use this class query the complex query via the SqlAlchemy query'
  @classmethod
  def get_users_with_pagination(cls, offset, limit):
    return User.query.order_by(User.created_at.desc()).paginate(offset, limit, False).items

  @classmethod
  def get_user_with_id(cls, user_id):
  	return User.query.filter_by(id=user_id).first()

  @classmethod
  def to_json_with_filter(cls, rows_dict, columns):
    d = {'success':True}
    for k, v in rows_dict.items():
      # handle the dict and integer and float
      if type(v) == type({}) or type(v) == type(1) or type(v) == type(1.0):
        d[k] = v
      # handle the model object
      elif (type(v) != type([])) and (v is not None):
        d[k] = {_k:_v for _k, _v in v.__dict__.items() if _k in columns}
      # handle the list
      elif v is not None:
        l = []
        for item in v:
          # handle the model object
          if type(item) != type({}):
            l.append({_k:_v for _k, _v in item.__dict__.items() if _k in columns})
          # handle the dict  
          else:
            l.append({_k:_v for _k, _v in item.items() if _k in columns})
        d[k] = l
      # handle the None  
      else:
        d[k] = {}
    return jsonify(d), 200

  @classmethod
  def to_json_with_filter_handle_isodatetime(cls, rows_dict, columns, columns_json=[], use_response=True):
    d = {'success':True}
    for k, v in rows_dict.items():
      # handle the dict and integer and float
      if type(v) == type({}) or type(v) == type(1) or type(v) == type(1.0):
        d[k] = v
      # handle the model object
      elif (type(v) != type([])) and (v is not None):
        tmp = {}
        for _k, _v in v.__dict__.items():
          if _k in columns:
            if _k not in columns_json:
              if isinstance(_v,datetime):
                tmp[_k] = _v.isoformat()
              else:
                tmp[_k] = _v
            else:
              if _v:
                tmp[_k] = json.loads(_v)
              else:
                tmp[_k] = _v
        d[k] = tmp

      # handle the list
      elif v is not None:
        l = []
        for item in v:
          # handle the model object
          if type(item) != type({}):
            tmp2 = {}
            for _k, _v in item.__dict__.items():
              if _k in columns:
                if _k not in columns_json:
                  if isinstance(_v,datetime):
                    tmp2[_k] = _v.isoformat()
                  else:
                    tmp2[_k] = _v
                else:
                  if _v:
                    tmp2[_k] = json.loads(_v)
                  else:
                    tmp2[_k] = _v
            l.append(tmp2)
          # handle the dict
          else:
            l.append({_k:_v for _k, _v in item.items() if _k in columns})
        d[k] = l
      # handle the None
      else:
        d[k] = {}
    if use_response:
      return jsonify(d), 200
    else:
      return d

  @classmethod
  def validate_json_contains_none_value(cls, columns, val_json):
    if val_json is None:
      return True
    for item in columns:
      if item not in val_json:
        return True
    for k, v in val_json.items():
      if k == '' or v is None or v == '':
        return True
    return False

  @classmethod
  def filter_dict_none_value(cls, d):
    return {k:v for k, v in d.iteritems() if k and v}

  @classmethod
  def set_user_with_id(cls, **kwargs):
    try:
      db.session.query(User).filter(User.id==kwargs['id']).update(kwargs)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return False
    return True

  @classmethod
  def get_users_with_user_name_or_email_or_phone(cls, name=None, email=None, phone=None):
    if name:
      return User.query.filter(User.name.like('%'+str(name)+'%')).all()
    if email:
      return User.query.filter(User.email.like('%'+str(email)+'%')).all()
    if phone:
      return User.query.filter(User.phone.like('%'+str(phone)+'%')).all()
    return None

  @classmethod
  def admin_filter(cls, query_type, query):
    # type 0 => user.name query 1 => user.email query 2 => user.phone query
    # type 10 => offer.status query
    d = {}
    choose_list = [
    ['name', 'email', 'phone'],
    ['status'],
    ['address'],
  ]
    # user query
    if query_type // 10 == 0:
      all_users = cls.get_users_with_user_name_or_email_or_phone(**{
        choose_list[0][query_type%10]: query
        })
      l = []
      for user in all_users:
        l.append({
          'id': user.id,
          'name': user.name,
          'phone': user.phone,
          'homes': len(user.homes)
          })
      d['users'] = l
      d['length'] = len(all_users)
      columns = ['name', 'phone', 'homes', 'id']
      return cls.to_json_with_filter(rows_dict=d, columns=columns)
    # offer query
    if query_type // 10 == 1:
      all_offers = cls.get_offers_with_status(**{
        choose_list[1][query_type%10]: query
        })
      l = []
      for offer in all_offers:
          l.append({
            'home_id': offer.home.id,
            'address': offer.home.address,
            'name': offer.home.owner.name,
            'status': offer.status,
            'id': offer.id,
            'phone': offer.home.owner.phone})
      d['offers'] = l
      d['length'] = len(all_offers)
      columns = ['home_id', 'address', 'name', 'phone', 'status', 'id']
      return cls.to_json_with_filter(rows_dict=d, columns=columns)
    # home query
    if query_type // 10 == 2:
      all_homes = cls.get_homes_with_address(**{
        choose_list[2][query_type%10]: query
        })
      l = []
      for home in all_homes:
          l.append({
            'address': home.address,
            'name': home.owner.name,
            'id': home.id,
            'phone': home.owner.phone})
      d['homes'] = l
      d['length'] = len(all_homes)
      columns = ['id', 'address', 'name', 'phone', 'length']
      return cls.to_json_with_filter(rows_dict=d, columns=columns)

  @classmethod
  def add_user(cls, name, email, phone, country, password, user_type=0):
    new_user = None
    try:
      new_user = User(name=name, email=email, phone=phone, country=country,
      password=password, user_type=user_type)
      db.session.add(new_user)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return None
    return new_user

  @classmethod
  def get_user_with_email(cls, email):
    return User.query.filter_by(email=email).first()

  @classmethod
  def add_picture(cls, type, picturable_id, filename):
    try:
      new_picture = Picture(type=type, picturable_id=picturable_id, filename=filename)
      db.session.add(new_picture)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return False
    return True

  @classmethod
  def get_linkedin_user_with_email(cls, email):
    return User.query.filter_by(email=email, type=1).first()

  @classmethod
  def get_linkedin_user_with_phone(cls, phone):
    return User.query.filter_by(phone=phone, type=1).first()

  @classmethod
  def add_file(cls, type, foreign_id, item_id, filename, raw_name):
    new_file = None
    try:
      new_file = File(type=type, foreign_id=foreign_id, item_id=item_id, filename=filename, raw_name=raw_name)
      db.session.add(new_file)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return None
    return new_file

  @classmethod
  def del_file(cls, type, foreign_id, item_id):
    try:
      file = File.query.filter(and_(File.foreign_id==foreign_id, File.item_id==item_id,
        File.type==type, File.is_active==IS_ACTIVE_USED)).first()
      if not file:
        return True
      # FixMe: need IS_ACTIVE_DISCARDED type
      # file.is_active = IS_ACTIVE_DISCARDED
      db.session.merge(file)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return False
    return True

  @classmethod
  def save_extra_file(cls, foreign_id, file_id, type, url, is_active=1):
    new_file = None
    try:
      new_file = ExtraFile(foreign_id=foreign_id, file_id=file_id, type=type, url=url, is_active=is_active)
      db.session.add(new_file)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return None
    return new_file

  @classmethod
  def get_file_with_id(cls, file_id):
    return File.query.filter_by(id=file_id).first()

  @classmethod
  def fill_neighbor_info(cls,neighbor_item):
    neighbor = Neighborhood.query.filter_by(region_id=neighbor_item['id']).first()
    if not neighbor:
      return neighbor_item
    neighbor_item['increase_ratio'] = neighbor.forecast_increase_ratio
    neighbor_item['rent_ratio'] = neighbor.forecast_rent_ratio
    price_curve = neighbor.home_value_sale_price_history
    neighbor_item['price_curve'] = json.loads(price_curve) if price_curve else None
    neighbor_item['sale_rent_ratio'] = neighbor.sale_rent_ratio
    return neighbor_item

  @classmethod
  def fill_area_info(cls,area_item):
    area = Area.query.filter_by(geoid=area_item['id']).first()
    if not area:
      return area_item
    area_item['eng_name'] = area.eng_name
    return area_item

  @classmethod
  def get_collection_with_user_home(cls, user_id, home_id):
    return Collection.query.filter(and_(Collection.user_id==user_id, Collection.home_id==home_id)).first()

  @classmethod
  def get_active_collection_with_user_home(cls, user_id, home_id):
    return Collection.query.filter(and_(Collection.user_id==user_id, Collection.home_id==home_id,Collection.is_active==True)).first()

  @classmethod
  def set_collection(cls, user_id, home_id):
    collection = cls.get_collection_with_user_home(user_id=user_id, home_id=home_id)
    if not collection:
      collection = Collection(user_id=user_id, home_id=home_id)
    else:
      collection.is_active = True

    try:
      db.session.merge(collection)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return None
    return cls.get_collection_with_user_home(user_id=user_id, home_id=home_id)

  @classmethod
  def del_collection(cls, user_id, home_id):
    collection = cls.get_collection_with_user_home(user_id=user_id, home_id=home_id)
    if not collection:
      return False
    collection.is_active = False
    try:
      db.session.merge(collection)
      db.session.commit()
    except (DataError, IntegrityError), e:
      app.logger.error(sys._getframe().f_code.co_name + str(e))
      return False
    return True

  @classmethod
  def get_collections_with_user(cls, user_id):
    return Collection.query.filter(and_(Collection.user_id==user_id, Collection.is_active==True)).all()
