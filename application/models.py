from index import db, bcrypt
import datetime
import decimal
import json
from sqlalchemy.orm import relationship
from flask import jsonify
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import JSON

user_rule_association = db.Table(
  'user_rule_association', db.Model.metadata,
  db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
  db.Column('rule_id', db.Integer, db.ForeignKey('rule.id')),
  info={'bind_key': 'wehomeproperty'}
)


class User(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  name = db.Column(db.String(255), index=True, unique=True)
  rules = relationship("Rule", secondary=user_rule_association, back_populates="users")
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)
  
  @staticmethod
  def get_user_with_name_or_id(id=None, name=None):
    if id:
      user = User.query.filter_by(id=id).first()
    elif name:
      user = User.query.filter_by(name=name).first()
    if user:
      return user
    else:
      return None


class Rule(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  users = relationship("User", secondary=user_rule_association, back_populates="rules")
  api_id = db.Column(db.String(255))
  throttle_day = db.Column(db.String(255))
  throttle_hour = db.Column(db.String(255))
  throttle_min = db.Column(db.String(255))
  includes = db.Column(db.Text())
  excludes = db.Column(db.Text())
  statistics = db.Column(db.Boolean(), default=False)
  notes = db.Column(db.String(255))
  extra = db.Column(db.Text())


class Picture(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  # type 0: avatar 1 => linkinde url
  type = db.Column(db.Integer())
  picturable_id = db.Column(db.Integer())
  filename = db.Column(db.String(255))
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)
  
  __table_args__ = (
    db.Index("idx_type_picturable_id", "type", "picturable_id"),
  )
  
  def __init__(self, type, picturable_id, filename):
    self.type = type
    self.picturable_id = picturable_id
    self.filename = filename
  
  @staticmethod
  def get_filename_with_user_id(user_id):
    picture = Picture.query.filter_by(type=0, picturable_id=user_id).order_by(Picture.id.desc()).first()
    if picture:
      return picture.filename
    return None


class Administrator(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  user_id = db.Column(db.Integer(), db.ForeignKey("user.id", ondelete="CASCADE"),
                      nullable=False, index=True, unique=True)
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)
  
  @staticmethod
  def is_user_admin(user_id):
    admin = Administrator.query.filter_by(user_id=user_id).first()
    return admin is not None


class File(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  # 0 => s3 file
  type = db.Column(db.Integer())
  is_active = db.Column(db.Boolean(), default=True, index=True)
  foreign_id = db.Column(db.Integer(), nullable=False, index=True)
  # like report's item id and itme id
  item_id = db.Column(db.Integer(), nullable=False, index=True)
  filename = db.Column(db.String(255))
  # the raw name of upload
  raw_name = db.Column(db.String(255))
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)
  
  __table_args__ = (
    db.Index("idx_foreign_id_item_id_type_is_active", "foreign_id", 'item_id', 'type', 'is_active'),
  )
  
  def __init__(self, type, foreign_id, item_id, filename, raw_name, is_active=True):
    self.type = type
    self.foreign_id = foreign_id
    self.item_id = item_id
    self.filename = filename
    self.is_active = is_active
    self.raw_name = raw_name


class ExtraFile(db.Model):
  __bind_key__ = 'wehomeproperty'
  '''for user or property extra file'''
  id = db.Column(db.Integer(), index=True, primary_key=True)
  # user_id or property_id
  foreign_id = db.Column(db.Integer(), nullable=False, index=True)
  file_id = db.Column(db.Integer())
  # 0 => user inspection report 1 => user contract file
  type = db.Column(db.Integer())
  url = db.Column(db.String(255))
  # 0 => discard 1 => used
  is_active = db.Column(db.Boolean(), default=True, index=True)
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)
  
  def __init__(self, foreign_id, file_id, type, url, is_active=1):
    self.foreign_id = foreign_id
    self.file_id = file_id
    self.type = type
    self.url = url
    self.is_active = is_active


class Neighborhood(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  name = db.Column(db.String(255))
  region_id = db.Column(db.Integer(), index=True, unique=True)
  city = db.Column(db.String(255))
  state = db.Column(db.String(255))
  
  past_rent_ratio = db.Column(db.Float())
  past_increase_ratio = db.Column(db.Float())
  forecast_rent_ratio = db.Column(db.Float())
  forecast_increase_ratio = db.Column(db.Float())
  
  home_value_rent_price_history = db.Column(db.Text())
  home_value_sale_price_history = db.Column(db.Text())
  
  market_health_index = db.Column(db.Float())
  
  rent_final_point = db.Column(db.Float())
  zestimate = db.Column(db.Float())
  
  neighborhood_score = db.Column(db.Float())
  area_geoid = db.Column(db.Integer(), index=True)
  
  # for IRR
  hoa = db.Column(db.Float())
  property_tax = db.Column(db.Float())
  vaccancy_rate = db.Column(db.Float())
  property_management_fee = db.Column(db.Float())
  leasing_commission = db.Column(db.Float())
  insurance_cost = db.Column(db.Float())
  repair = db.Column(db.Float())
  cap_ex = db.Column(db.Float())
  acquisition_cost = db.Column(db.Float())
  disposition_cost = db.Column(db.Float())
  rent_growth = db.Column(db.Float())
  
  properties = db.Column(LONGTEXT())
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)


class Area(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  geoid = db.Column(db.String(255), index=True, unique=True)
  cities = db.relationship('City', backref='area')
  name = db.Column(db.String(255), index=True)
  eng_name = db.Column(db.String(255), index=True)
  lat = db.Column(db.Float())
  lng = db.Column(db.Float())
  layer_type = db.Column(db.String(255), index=True)
  properties = db.Column(JSON())
  
  # for IRR
  property_tax = db.Column(db.Float())
  vaccancy_rate = db.Column(db.Float())
  property_management_fee = db.Column(db.Float())
  leasing_commission = db.Column(db.Float())
  insurance_cost = db.Column(db.Float())
  repair = db.Column(db.Float())
  cap_ex = db.Column(db.Float())
  acquisition_cost = db.Column(db.Float())
  disposition_cost = db.Column(db.Float())
  rent_growth = db.Column(db.Float())
  
  #
  down_payment = db.Column(db.Float())
  loan_interest_rate = db.Column(db.Float())
  expenses = db.Column(db.Float())
  closing_costs_misc = db.Column(db.Float())
  
  #
  history = db.Column(db.Text())
  block_villa_median = db.Column(db.Float())
  block_apartment_median = db.Column(db.Float())
  deal_average_price = db.Column(db.Float())
  list_average_price = db.Column(db.Float())
  occ_rate_long = db.Column(db.Float())
  occ_rate_airbnb = db.Column(db.Float())
  return_long = db.Column(db.Float())
  return_airbnb = db.Column(db.Float())
  
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)


class State(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  geoid = db.Column(db.String(255), index=True, unique=True)
  name = db.Column(db.String(255))
  name_abbr = db.Column(db.String(255))
  lat = db.Column(db.Float())
  lng = db.Column(db.Float())
  properties = db.Column(JSON)
  cities = db.relationship('City', backref='state')
  
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)


class CensusReport(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  type = db.Column(db.Integer())   # Refer utils.type.CENSUS_REPORT
  geoid = db.Column(db.String(255))
  census = db.Column(JSON)
  
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)
  
  __table_args__ = (
    db.Index("idx_census_report", "type", 'geoid'),
  )
  
  def __init__(self, type, geoid, census):
    self.type = type
    self.geoid = geoid
    self.census = census


class City(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  geoid = db.Column(db.String(255), index=True, unique=True)
  area_geoid = db.Column(db.String(255), db.ForeignKey('area.geoid'), index=True)
  state_geoid = db.Column(db.String(255), db.ForeignKey('state.geoid'),index=True)
  zipcodes = db.relationship('Zipcode', backref='city')
  neighbors = db.relationship('Neighbor', backref='city_')
  name = db.Column(db.String(255), index=True)
  lat = db.Column(db.Float())
  lng = db.Column(db.Float())
  properties = db.Column(JSON)
  
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)


class Zipcode(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  geoid = db.Column(db.String(255), index=True, unique=True)
  city_geoid = db.Column(db.String(255), db.ForeignKey('city.geoid',onupdate="SET NULL", ondelete="SET NULL"), index=True)
  lat = db.Column(db.Float())
  lng = db.Column(db.Float())
  properties = db.Column(JSON)
  
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)


class IpQuery(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  ip = db.Column(db.String(255), index=True)
  home_id = db.Column(db.String(255))
  source_name = db.Column(db.String(255))
  date = db.Column(db.Date())
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)
  
  def __init__(self, ip, home_id, source_name, date):
    self.ip = ip
    self.home_id = home_id
    self.source_name = source_name
    self.date = date


class Neighbor(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  # neighbor_id = db.Column(db.String(255), index=True, unique=False)
  centroid = db.Column(db.String(255))
  name = db.Column(db.String(255))
  url = db.Column(db.String(255))
  crime = db.Column(db.Integer())
  demographic = db.Column(db.Integer())
  real_estate = db.Column(db.Integer())
  overview = db.Column(db.Integer())
  school = db.Column(db.Integer())
  property = db.Column(JSON)
  city = db.Column(db.String(255), index=True, unique=False)
  city_geoid = db.Column(db.String(255), db.ForeignKey('city.geoid', onupdate="SET NULL", ondelete="SET NULL"), index=True)


class County(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column(db.Integer(), index=True, primary_key=True)
  name = db.Column(db.String(255), index=True)
  geoid = db.Column(db.String(255), index=True, unique=True)
  cbsa_geoid = db.Column(db.String(255), index=True)
  lat = db.Column(db.Float())
  lng = db.Column(db.Float())
  properties = db.Column(JSON)
  created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
  updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)


class RedfinMarket(db.Model):
  __bind_key__ = 'wehomeproperty'
  id = db.Column('index', db.Integer(), primary_key=True)
  avg_sale_to_list_mom = db.Column('Avg Sale To List Mom', db.Float())
  avg_sale_to_list_yoy = db.Column('Avg Sale To List Yoy', db.Float())
  avg_sale_to_list = db.Column('Avg Sale To List', db.Float())
  city = db.Column('City', db.String(255))
  homes_sold_mom = db.Column('Homes Sold Mom', db.Float())
  homes_sold_yoy = db.Column('Homes Sold Yoy', db.Float())
  homes_sold = db.Column('Homes Sold', db.Float())
  inventory_mom = db.Column('Inventory Mom', db.Float())
  inventory_yoy = db.Column('Inventory Yoy', db.Float())
  inventory = db.Column('Inventory', db.Float())
  measure_display = db.Column('Measure Display', db.String(255))
  median_dom_mom = db.Column('Median Dom Mom', db.Integer())
  median_dom_yoy = db.Column('Median Dom Yoy', db.Integer())
  median_dom = db.Column('Median Dom', db.Integer())
  median_list_ppsf_mom = db.Column('Median List Ppsf Mom', db.Float())
  median_list_ppsf_yoy = db.Column('Median List Ppsf Yoy', db.Float())
  median_list_ppsf = db.Column('Median List Ppsf', db.Float())
  median_list_price_mom = db.Column('Median List Price Mom', db.Float())
  median_list_price_yoy = db.Column('Median List Price Yoy', db.Float())
  median_list_price = db.Column('Median List Price', db.Integer())
  median_ppsf_mom = db.Column('Median Ppsf Mom', db.Float())
  median_ppsf_yoy = db.Column('Median Ppsf Yoy', db.Float())
  median_ppsf = db.Column('Median Ppsf', db.Float())
  median_sale_price_mom = db.Column('Median Sale Price Mom', db.Float())
  median_sale_price_yoy = db.Column('Median Sale Price Yoy', db.Float())
  median_sale_price = db.Column('Median Sale Price', db.String(31))
  new_listings_mom = db.Column('New Listings Mom', db.Float())
  new_listings_yoy = db.Column('New Listings Yoy', db.Float())
  new_listings = db.Column('New Listings', db.Integer())
  number_of_records = db.Column('Number of Records', db.Integer())
  period_begin = db.Column('Period Begin', db.String(255))
  period_duration = db.Column('Period Duration', db.Integer())
  period_end = db.Column('Period End', db.String(255))
  price_drops_mom = db.Column('Price Drops Mom', db.Float())
  price_drops_yoy = db.Column('Price Drops Yoy', db.Float())
  price_drops = db.Column('Price Drops', db.Float())
  property_type = db.Column('Property Type', db.String(255))
  region_type = db.Column('Region Type', db.String(15))
  region = db.Column('Region', db.String(255))
  sold_above_list_mom = db.Column('Sold Above List Mom', db.Float())
  sold_above_list_yoy = db.Column('Sold Above List Yoy', db.Float())
  sold_above_list = db.Column('Sold Above List', db.Float())
  state_code = db.Column('State Code', db.String(2))
  state = db.Column('State', db.String(255))
  table_id = db.Column('Table Id', db.String(255))
  worksheet_filter = db.Column('Worksheet Filter', db.String(255))
  months_of_supply = db.Column('Months Of Supply', db.Float())
  months_of_supply_mom = db.Column('Months Of Supply Mom', db.Float())
  months_of_supply_yoy = db.Column('Months Of Supply Yoy', db.Float())

  __table_args__ = (
    db.Index('idx_city_region_type_region_state_code', 'Region Type', 'Region', 'City', 'State Code'),
  )
