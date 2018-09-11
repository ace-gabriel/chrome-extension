# -*- coding: utf-8 -*-
import re
import time
from datetime import datetime

from pytz import timezone

from index import app

logger = app.logger

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def convert_camel_to_snake(name):
  s1 = first_cap_re.sub(r'\1_\2', name)
  return all_cap_re.sub(r'\1_\2', s1).lower()


def convert_seconds_to_human_string(seconds):
  hh = seconds / 3600
  mm = seconds % 3600 / 60
  ss = seconds % 60
  return {
    "HH": hh,
    "MM": mm,
    "SS": ss
  }


def datetime_to_epoch(datetime_obj):
  if not datetime_obj:
    return None
  return (datetime_obj.replace(tzinfo=timezone('UTC')) - datetime(1970, 1, 1).replace(tzinfo=timezone('UTC'))).total_seconds()


def datetime_to_localepoch(datetime_obj):
  # very hacky，将utc时间转成本地的时间戳
  if not datetime_obj:
    return None
  return (datetime_obj.replace(tzinfo=timezone('Asia/Shanghai')) - datetime(1970, 1, 1).replace(tzinfo=timezone('UTC'))).total_seconds()


def utc2local(utc_st):
  """
  UTC时间转本地时间（+8:00）
  :param utc_st:
  :return:
  """
  now_stamp = time.time()
  local_time = datetime.fromtimestamp(now_stamp)
  utc_time = datetime.utcfromtimestamp(now_stamp)
  offset = local_time - utc_time
  local_st = utc_st + offset
  return local_st


def local2utc(local_st):
  """
  本地时间转UTC时间（-8:00）
  """
  time_struct = time.mktime(local_st.timetuple())
  utc_st = datetime.utcfromtimestamp(time_struct)
  return utc_st


def date2str(date, format="%Y-%m-%d %H:%M"):
  """
  本地时间转UTC时间（-8:00）
  """
  if date:
    return date.strftime(format)
  else:
    return None


def localstr2utc(date, format="%Y-%m-%d %H:%M"):
  """
  将本地时间字符串转成utc时间对象
  """
  if str:
    return local2utc(datetime.strptime(str(date), format))
  else:
    return None


def to_dict_from_model(model):
  """
  将对象转成字典
  """
  if model:
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}
  else:
    return {}


def to_dict_from_model_timestamp(model):
  """
  将对象转成字典，并将日期类型的对象转成时间戳
  """
  if model:
    return {c.name: datetime_to_epoch(getattr(model, c.name)) if isinstance(getattr(model, c.name), datetime) else getattr(model, c.name)
            for c in model.__table__.columns}
  else:
    return {}


def to_dict_from_model_localtime(model):
  """
  后台接口专用，因为展示的是localtime
  将对象转成字典，并将日期类型的转换成本地可展示的时间
  """
  if model:
    return {c.name: date2str(utc2local(getattr(model, c.name))) if isinstance(getattr(model, c.name), datetime) else getattr(model, c.name)
            for c in model.__table__.columns}
  else:
    return {}


def to_dict_from_model_notime(model):
  """
  将对象转成字典，不包含时间
  """
  temp = to_dict_from_model(model)
  temp.pop("created_at")
  temp.pop("updated_at")
  return temp
