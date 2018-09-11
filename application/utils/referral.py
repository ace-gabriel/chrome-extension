from ..models import User, Picture
from helper import id_generator
from s3 import s3_get_url
import string
from index import app, db

LANDING_PAGE_URL = app.config["REFERRAL_BASE_URL"]+"accept-invitation?code={}"

class ReferralCodeException(Exception):
  pass

def create_referral_code(user_id):
  code = id_generator(8, string.ascii_letters)
  # Check weather code exisits 
  counter = 0
  success = False
  while (not success and counter < 10):
    referral_code = ReferralCode(user_id, code)
    db.session.add(referral_code)
    try:
      db.session.commit()
      success = True
    except IntegrityError as e:
      code = id_generator(8, string.ascii_letters)
      counter += 1

  if not success:
    raise ReferralCodeException()
  return code
 
def track_referral(new_user, code):
  if not code:
    app.logger.error("invalide referral code {}".format(code))
    return False
  from_user_id= ReferralCode.get_user_id_from_referral_code(code)
  if not from_user_id:
    app.logger.error("no matching user for referral code {}".format(code))
    return False

  referral_tracking = ReferralTracking(from_user_id, new_user.id, code)
  db.session.add(referral_tracking)
  db.session.commit()
  return True

def referral_stats(landlord):
  results = []
  referred_user_ids = ReferralTracking.get_referred_user_ids(landlord["id"])
  if len(referred_user_ids) == 0:
    return results
  # user_names
  users = User.get_users_with_ids(referred_user_ids)
  results = [{"name": u.name, "id": u.id, "deals": False} for u in users]
  # ToDo: @wenhang check user status
  return results

def referrer_info(referral_code):
  result = {"name": '', 'url': ''}
  referrer_id = ReferralCode.get_user_id_from_referral_code(referral_code)
  if not referrer_id:
    return None
  name = User.query.filter_by(id=referrer_id).first().name
  key = Picture.get_filename_with_user_id(referrer_id)
  url = s3_get_url(key)
  result =  {"name": name, 'url': url}
  return result
