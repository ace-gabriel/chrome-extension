from flask import request, jsonify, g
from flask import Blueprint
from index import app
from application.utils.auth import json_validate_logic
from application.region.state import StateRegion

ep_state_bp = Blueprint('ep_state_blueprint', __name__)
logger = app.logger

@ep_state_bp.route('/state/geometry', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["state","geoid"])
def state_geometry():
    incoming = g.incoming
    name, geoid = incoming.get('state'), incoming.get('geoid')
    state_region = StateRegion(name=name,geoid=geoid)
    result = state_region.get_region_geo_imp()

    return jsonify(success=True, result=result)

@ep_state_bp.route('/state/census', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["state","geoid"])
def state_census():
    incoming = g.incoming
    name, geoid = incoming.get('state'), incoming.get('geoid')
    state_region = StateRegion(name=name,geoid=geoid)
    result = state_region.get_census_report_imp()

    return jsonify(success=True, result=result)

@ep_state_bp.route('/state/estate', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["state","geoid"])
def state_estate():
    incoming = g.incoming
    name, geoid = incoming.get('state'), incoming.get('geoid')
    state_region = StateRegion(name=name,geoid=geoid)
    result = state_region.get_real_estate_imp()

    return jsonify(success=True, result=result)


@ep_state_bp.route('/state/property', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["state","geoid"])
def state_property():
    incoming = g.incoming

    name, geoid = incoming.get('state'), incoming.get('geoid')
    state_region = StateRegion(name=name,geoid=geoid)
    result = state_region.get_house_within_region_imp()

    return jsonify(success=True, result=result)


@ep_state_bp.route('/state/cities', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["state","geoid"])
def state_cities():
    incoming = g.incoming

    name, geoid = incoming.get('state'), incoming.get('geoid')
    state_region = StateRegion(name=name, geoid=geoid)
    result = state_region.get_cities_list()

    return jsonify(success=True, result=result)
