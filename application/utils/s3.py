from uuid import uuid4
import boto3
from botocore.client import Config
import os
from index import app
from werkzeug.utils import secure_filename


def s3_upload(source_file, upload_dir=None, acl='public-read', extension='.png'):
  """ Uploads WTForm File Object to Amazon S3
    Expects following app.config attributes to be set:
      S3_KEY              :   S3 API Key
      S3_SECRET           :   S3 Secret Key
      S3_BUCKET           :   What bucket to upload to
      S3_UPLOAD_DIRECTORY :   Which S3 Directory.
    The default sets the access rights on the uploaded file to
    public-read.  It also generates a unique filename via
    the uuid4 function combined with the file extension from
    the source file.
  """

  if upload_dir is None:
    upload_dir = app.config["S3_UPLOAD_DIRECTORY"]

  source_filename = secure_filename(source_file.filename)
  source_extension = os.path.splitext(source_filename)[1]
  destination_filename = uuid4().hex + source_extension
  # Connect to S3 and upload file.
  s3 = boto3.client(
    's3', 
    aws_access_key_id=app.config['S3_KEY'], 
    aws_secret_access_key=app.config['S3_SECRET'],
    region_name=app.config['S3_REGION_NAME'],
    config=Config(signature_version='s3v4')
  )
  saved_file = os.path.join(app.config['S3_TMP_DIRECTORY'], destination_filename)
  source_file.save(saved_file)
  key = "/".join([upload_dir, destination_filename])
  s3.upload_file(saved_file, app.config['S3_BUCKET'], key, {'ACL': acl})
  os.remove(saved_file)
  return key

def s3_get_url(key):
  if key is None:
    return '';
  s3 = boto3.client(
    's3', 
    aws_access_key_id=app.config['S3_KEY'], 
    aws_secret_access_key=app.config['S3_SECRET'],
    region_name=app.config['S3_REGION_NAME'],
    config=Config(signature_version='s3v4')
  )
  url = '{}/{}/{}'.format(s3.meta.endpoint_url, app.config["S3_BUCKET"], key)
  # url = s3.generate_presigned_url(
  #   'get_object', 
  #   Params={'Bucket': app.config["S3_BUCKET"],'Key': key}, 
  #   ExpiresIn=86400)
  return url