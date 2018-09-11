from flask import request, jsonify, g
from flask import Blueprint
from index import app
from application.utils.auth import json_validate_logic
from application.region.msa import MsaRegion


ep_msa_bp = Blueprint('ep_msa_blueprint', __name__)
logger = app.logger

@ep_msa_bp.route('/cbsa/geometry', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["msa","geoid"])
def msa_geometry():
    incoming = g.incoming

    name, geoid = incoming.get('msa'), incoming.get('geoid')
    msa_region = MsaRegion(name=name,geoid=geoid)
    result = msa_region.get_region_geo_imp()

    return jsonify(success=True, result=result)

@ep_msa_bp.route('/cbsa/census', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["msa","geoid"])
def msa_census():
    incoming = request.get_json()

    name, geoid = incoming.get('msa'), incoming.get('geoid')
    msa_region = MsaRegion(name=name,geoid=geoid)
    result = msa_region.get_census_report_imp()

    return jsonify(success=True, result=result)

@ep_msa_bp.route('/cbsa/estate', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["msa","geoid"])
def msa_estate():
    incoming = request.get_json()

    name, geoid = incoming.get('msa'), incoming.get('geoid')
    msa_region = MsaRegion(name=name,geoid=geoid)
    result = msa_region.get_real_estate_imp()

    return jsonify(success=True, result=result)


@ep_msa_bp.route('/cbsa/property', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["msa","geoid"])
def msa_property():
    incoming = request.get_json()

    name, geoid = incoming.get('msa'), incoming.get('geoid')
    msa_region = MsaRegion(name=name,geoid=geoid)
    result = msa_region.get_house_within_region_imp()

    return jsonify(success=True, result=result)

@ep_msa_bp.route('/cbsa/cities', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["msa","geoid"])
def state_cities():
    incoming = request.get_json()

    name, geoid = incoming.get('state'), incoming.get('geoid')
    msa_region = MsaRegion(name=name, geoid=geoid)
    result = msa_region.get_cities_list()

    return jsonify(success=True, result=result)