from flask import request, jsonify, g
from flask import Blueprint
from index import app
from application.utils.auth import json_validate_logic
from application.region.zipcode import ZipcodeRegion

ep_zipcode_bp = Blueprint('ep_zipcode_blueprint', __name__)
logger = app.logger


@ep_zipcode_bp.route('/zipcode/geometry', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["zipcode","geoid"])
def zipcode_geometry():
    incoming = g.incoming
    name, geoid = incoming.get('zipcode'), incoming.get('geoid')

    zipcode_region = ZipcodeRegion(name=name,geoid=geoid)
    result = zipcode_region.get_region_geo_imp()

    return jsonify(success=True, result=result)

@ep_zipcode_bp.route('/zipcode/census', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["zipcode","geoid"])
def zipcode_census():
    incoming = g.incoming
    name, geoid = incoming.get('zipcode'), incoming.get('geoid')

    zipcode_region = ZipcodeRegion(name=name,geoid=geoid)
    result = zipcode_region.get_census_report_imp()

    return jsonify(success=True, result=result)

@ep_zipcode_bp.route('/zipcode/estate', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["zipcode","geoid"])
def zipcode_estate():
    incoming = g.incoming
    name, geoid = incoming.get('zipcode'), incoming.get('geoid')

    zipcode_region = ZipcodeRegion(name=name,geoid=geoid)
    result = zipcode_region.get_real_estate_imp()

    return jsonify(success=True, result=result)

@ep_zipcode_bp.route('/zipcode/property', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["zipcode","geoid"])
def zipcode_property():
    incoming = g.incoming

    name, geoid = incoming.get('zipcode'), incoming.get('geoid')
    zipcode_region = ZipcodeRegion(name=name,geoid=geoid)
    result = zipcode_region.get_house_within_region_imp()

    return jsonify(success=True, result=result)
