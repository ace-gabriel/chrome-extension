# -*- coding: utf-8 -*-

from index import celery, app, db
import requests
import json

@celery.task(name="tasks.pricing")
def pricing(id, address, bedroom, bathroom, size):
  from .models import Offer
  HOST = app.config["PRICING_HOST"]

  data = {
    "address": address,
    "bedroom": bedroom,
    "bathroom": bathroom,
    "size": size
  }
  try:
    r = requests.post(url=HOST+"/offer",json=data,timeout=60)
    pricing = json.loads(r.text)["offer"]
  except requests.Timeout as e:
    app.logger.error("Pricing service timed out {}".format(e))
    return
  app.logger.info("Pricing is {}".format(pricing))

  # Write to offer
  offer = Offer.get_offer_with_home_id(id)
  if offer is None:
    app.logger.error("Offer not existed for home {}".format(id))
    return
  if offer.status == 2:
    app.logger.warning("Offer has been confirmed for home {}".format(id))

  offer.rent = pricing["suggested"]
  offer.suggested = pricing["suggested"]
  offer.suggested_max = pricing["max"]
  offer.suggested_min = pricing["min"]

  offer.status = 1
  db.session.add(offer)
  db.session.commit()
  app.logger.info("Made offer to home {}".format(id))

@celery.task(name="tasks.contract")
def contract(home_id, offer_id, address, home_type, rent, available_date_str, end_date_str, email, name):
  data = {
    "rent": rent,
    "type": home_type,
    "startDate": available_date_str,
    "endDate": end_date_str,
    "pets": "N/A",
    "address": address,
    "landlordName": name,
    "landlordEmail": email
  }

  HOST = app.config["CONTRACT_HOST"]
  try:
    r = requests.post(url=HOST+"/send",json=data,timeout=60)
    envelopeId = json.loads(r.text)["envelopeId"]
  except requests.Timeout as e:
    app.logger.error("Contract service timed out {}".format(e))
    return
  app.logger.info("Envelope id is {}".format(envelopeId))

  from .utils.query import QueryHelper
  from .utils.status import OFFER_FINISHED_MESSAGE, OFFER_FINISHED_MESSAGE_LINK
  QueryHelper.set_or_add_contract_with_home_id(home_id, 1)
  home = QueryHelper.get_home_with_id(home_id)
  send_sms_message.apply_async((home.owner.phone, home.owner.country, OFFER_FINISHED_MESSAGE,
    OFFER_FINISHED_MESSAGE_LINK.format(home_id)))

@celery.task(name="tasks.notification.sms")
def send_sms_message(mobile, country, text_type, text):
  from utils.comm import Notification
  return Notification.send_sms_message(mobile, country, text_type, text)

@celery.task(name='tasks.notification.realtor.email')
def send_realtor_input_info_email(recepient, home_id, landlord_name):
  from utils.comm import Notification
  return Notification.send_realtor_input_info_email(recepient, home_id, landlord_name)