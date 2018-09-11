from index import app, limiter, kafka_extension
from flask import Blueprint
from ..utils.auth import requires_auth, json_validate, requires_rule
from flask import  request, jsonify

kafka_bp = Blueprint('kafka', __name__)
logger = app.logger

@kafka_bp.route('/mq', methods=['POST'])
@requires_rule
@json_validate(filter=['topic','message'])
def mq():
  incoming = request.get_json()
  kafka_extension.producer.send(topic = incoming['topic'],
                                value = incoming['message'].encode())
  return jsonify(success=True)
