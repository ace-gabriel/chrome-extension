# -*- coding: utf-8 -*-

# Yunpian sms
# ToDo: make this async
import httplib
import urllib
import json
import requests

from index import app
from s3 import s3_get_url
from referral import LANDING_PAGE_URL
from ..models import Picture
from ..msg.template import message_list

# 1. profile_image_url 2. name 3. landing_page link
REFERRAL_EMAIL = u'''
<div style="width:100%; max-width:620px; margin: 0 auto; text-align:center;font-size:16px; font-family:PingFang SC ">
  <div style="background-image:linear-gradient(316deg,#03a9f4,#00bcd4);padding:30px 40px;">
    <div style=" width:110px;height:110px;border-radius:50%;background:#fff url({}) no-repeat center center;background-size:100%;margin:0 auto "></div>
    <p style="font-size:24px;color:#ffffff;margin: 20px 0 0 0;">您的经纪人{}向您推荐优质托管服务</p>
    <p style="font-size:16px;color:#ffffff;opacity:0.5;margin: 20px 0;">WeHome为跨境投资者提供一站式房屋托管服务，极速收房，<wbr>无空置风险。马上注册，为您的海外房产保驾护航。</p>
    <a href={} target="_blank">
      <button style="background:#fff;border-radius:2px;border:0;font-size:16px;color:#39474e;width:48%;padding: 10px;margin:0px">立即注册，马上获得租金</button>
    </a>
  </div>
  <div style="padding:20px 0;margin:0;line-height:40px;font-size:20px">
    <p style="font-size:20px;color:#b2bec4;margin-top:0;letter-spacing:2px;font-weight:500">轻松收租仅需3步</p>
    <img style="width: 80%;" src="http://a3.qpic.cn/psb?/V14QQRlh3VVhl9/7MaYAqiSLFf40XKuxkkrUmdv1.2*VO85JhjgUOBCUqw!/b/dGoBAAAAAAAA&amp;bo=vAW6AAAAAAADACY!&amp;rf=viewer_4&amp;t=5"> 
    <div style="overflow:auto; font-size:12px;width: 83%;margin:0 auto;line-height:1.5">
      <div style="float:left;width:33.3%;text-align:left;margin:0;">
        <p style="width: 80px;margin:0;text-align:center">提交房屋信息,立即获取房租报价</p>
     </div>
      <div style="float:left;width:33.3%;text-align:center;margin:0;">
        <p style="width: 80px;margin:0 auto;text-align:center;">我们进行房屋信息确认和现场勘察</p>
      </div>
      <div style="float:right;width:33.3%;text-align:right;margin:0;">
        <p style="width: 80px; margin: 0;text-align:center;float:right;">房子勘察后房租将在24小时内到账</p>
      </div>
    </div>
  </div>
</div>
'''

# email
import sendgrid
from sendgrid.helpers.mail import *
def send_single_email(sender, recepient, subject, body, plainText = False):
  sg = sendgrid.SendGridAPIClient(apikey=app.config["SENDGRID_API_KEY"])
  from_email = Email(sender)
  to_email = Email(recepient)
  mimeType = "text/plain" if plainText else "text/html"
  content = Content(mimeType, body)
  mail = Mail(from_email, subject, to_email, content)
  response = sg.client.mail.send.post(request_body=mail.get())
  app.logger.info("send email response {} {} {}".format(response.status_code, response.body, response.headers))
  return response.status_code == 202

def send_landlord_referral_email(recepient, landlord):
  name = landlord["userName"]
  profile_image_url = s3_get_url(Picture.get_filename_with_user_id(landlord["id"]))

  code = ReferralCode.get_referral_code_from_user(landlord["id"])
  if not code:
    return False
  link = LANDING_PAGE_URL.format(code)
  body = REFERRAL_EMAIL.format(profile_image_url, name, link)

  subject = u'您的经纪人{}向您推荐优质托管服务'.format(name)
  result = send_single_email(
    app.config['SENDGRID_DEFAULT_FROM'],
    recepient,
    subject,
    body,
    False
  )
  return result

# sms

def send_sms(mobile, country, text):
  status = False
  if app.config['TESTING']:
    return True
  if country == "86":
    status = send_sms_cn(mobile, text)
  elif country == "1":
    status = send_sms_nexmo(mobile, country, text)
  else:
    app.logger.warn("country code not supported {} {}".format(country, mobile))
  return status

def send_sms_cn(mobile, text):
  text = "【唯家WeHome】您的验证码是{}".format(text)
  apikey = app.config['YUNPIAN_KEY']
  sms_host = "sms.yunpian.com"
  port = 443
  version = "v2"
  sms_send_uri = "/" + version + "/sms/single_send.json"
  params = urllib.urlencode({'apikey': apikey, 'text': text, 'mobile':mobile})
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

  conn = httplib.HTTPSConnection(sms_host, port=port, timeout=30)
  response_json = {}
  try:
    conn.request("POST", sms_send_uri, params, headers)
    response = conn.getresponse()
    response_json = json.loads(response.read())
  finally:
    conn.close()
  success = response_json.get("code") == 0
  if not success:
    app.logger.error("Failed to send sms code to {} {}".format(mobile, response_json))
  return success

def send_sms_nexmo(mobile, country, text):
  import urllib

  params = {
    'api_key': app.config.get("NEXMO_KEY"),
    'api_secret': app.config.get("NEXMO_SECRET"),
    'to': "{}{}".format(country, mobile),
    'pin' : text
  }

  r = requests.get('https://rest.nexmo.com/sc/us/2fa/json?', params=params)

  success = False

  if r.status_code == 200:
    response_json = r.json()
    if len(response_json["messages"]) > 0 and response_json["messages"][0]["status"] == "0":
      success = True

  if not success:
    app.logger.error("Failed to send nexmo sms to {}, response is {}".format(mobile, r))

  return success

class Notification(object):
  @classmethod
  def gen_sms_message(cls, **kwargs):
    text_type = kwargs.get('text_type', None)
    # FixMe:// need to
    # if text_type == PAYMENT_CONFIRMATION:
    #   return message_list[str(kwargs.get('country', None))][text_type].format(email=kwargs.get('text', None))
    # if text_type in [OFFER_READY_MESSAGE, OFFER_FINISHED_MESSAGE, PAYMENT_CONFIRMATION,
    #   INSPECTION_NEED_FIXATION, INSPECTION_FINISHED]:
    #   return message_list[str(kwargs.get('country', None))][text_type].format(link=kwargs.get('text', None))
    return message_list[str(kwargs.get('country', None))][text_type]

  @classmethod
  def send_sms_cn(cls, **kwargs):
    text = cls.gen_sms_message(**kwargs)
    apikey = app.config['YUNPIAN_KEY']
    sms_host = "sms.yunpian.com"
    port = 443
    version = "v2"
    sms_send_uri = "/" + version + "/sms/single_send.json"
    params = urllib.urlencode({'apikey': apikey, 'text': text, 'mobile': kwargs.get('mobile', None)})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

    conn = httplib.HTTPSConnection(sms_host, port=port, timeout=30)
    response_json = {}
    try:
      conn.request("POST", sms_send_uri, params, headers)
      response = conn.getresponse()
      response_json = json.loads(response.read())
    finally:
      conn.close()
    success = response_json.get("code") == 0
    if not success:
      app.logger.error("Failed to send sms code to {} {}".format(kwargs.get('mobile', None), response_json))
    return success

  @classmethod
  def send_sms_message(cls, mobile, country, text_type, text):
    status = False
    if app.config['TESTING']:
      return True
    if country == "86":
      status = cls.send_sms_cn(mobile=mobile, country=country, text_type=int(text_type), text=text)
    elif country == "1":
      status = cls.send_sms_nexmo(mobile=mobile, country=country, text_type=int(text_type), text=text)
    else:
      app.logger.warn("country code not supported {} {}".format(country, mobile))
    return status


  @classmethod
  def send_sms_nexmo(cls, **kwargs):
    print kwargs
    text = cls.gen_sms_message(**kwargs)
    params = {
      'api_key': app.config.get("NEXMO_KEY"),
      'api_secret': app.config.get("NEXMO_SECRET"),
      'to': "{}{}".format(kwargs.get('country', None), kwargs.get('mobile', None)),
      'from': "18889706966",
      'text' : text
    }
    r = requests.get('https://rest.nexmo.com/sms/json', params=params)
    success = False
    if r.status_code == 200:
      response_json = r.json()
      if len(response_json["messages"]) > 0 and response_json["messages"][0]["status"] == "0":
        success = True
    if not success:
      app.logger.error("Failed to send nexmo sms to {}, response is {}".format(kwargs.get('mobile', None), r))
    return success

  @classmethod
  def send_single_email(cls, sender, recepient, subject, body, plainText = False):
    sg = sendgrid.SendGridAPIClient(apikey=app.config["SENDGRID_API_KEY"])
    from_email = Email(sender)
    to_email = Email(recepient)
    mimeType = "text/plain" if plainText else "text/html"
    content = Content(mimeType, body)
    mail = Mail(from_email, subject, to_email, content)
    response = sg.client.mail.send.post(request_body=mail.get())
    app.logger.info("send email response {} {} {}".format(response.status_code, response.body, response.headers))
    return response.status_code == 202

  @classmethod
  def send_realtor_input_info_email(cls, recepient, home_id, landlord_name):
    body = app.config['REALTOR_UTILITY_EMAIL_BODY'].format(
      landlord_name=landlord_name, home_id=home_id)
    subject = u'您的客户{}向您发来房屋信息补充请求'.format(landlord_name)
    result = cls.send_single_email(
      app.config['SENDGRID_DEFAULT_FROM'],
      recepient,
      subject,
      body,
      False
    )
    return result
