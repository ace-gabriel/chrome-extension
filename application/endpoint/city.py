from flask import request, jsonify, g
from flask import Blueprint
from index import app
from application.utils.auth import json_validate_logic
from application.region.city import CityRegion

ep_city_bp = Blueprint('ep_city_blueprint', __name__)
logger = app.logger


@ep_city_bp.route('/city/geometry', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["city","geoid"])
def city_geometry():
    incoming = g.incoming

    name, geoid = incoming.get('city'), incoming.get('geoid')
    city_region = CityRegion(name=name,geoid=geoid)
    result = city_region.get_region_geo_imp()

    return jsonify(success=True, result=result)

@ep_city_bp.route('/city/census', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["city","geoid"])
def city_census():
    incoming = g.incoming

    name, geoid = incoming.get('city'), incoming.get('geoid')
    city_region = CityRegion(name=name,geoid=geoid)
    result = city_region.get_census_report_imp()

    return jsonify(success=True, result=result)

@ep_city_bp.route('/city/estate', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["city","geoid"])
def city_estate():
    incoming = g.incoming

    name, geoid = incoming.get('city'), incoming.get('geoid')
    city_region = CityRegion(name=name,geoid=geoid)
    result = city_region.get_real_estate_imp()

    return jsonify(success=True, result=result)


@ep_city_bp.route('/city/property', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["city","geoid"])
def city_property():
    incoming = g.incoming

    name, geoid = incoming.get('city'), incoming.get('geoid')
    city_region = CityRegion(name=name,geoid=geoid)
    result = city_region.get_house_within_region_imp()

    return jsonify(success=True, result=result)


@ep_city_bp.route('/city/market', methods=['POST', 'GET'])
@json_validate_logic(filter_disjunction=["city", "geoid"])
def city_market():
    incoming = g.incoming
    
    name, geoid = incoming.get('city'), incoming.get('geoid')
    city_region = CityRegion(name=name, geoid=geoid)
    result = city_region.get_redfin_market()
    
    return jsonify(success=True, result=result)


@ep_city_bp.route('/city/neighbor', methods=['POST','GET'])
def city_to_neighbor():
    incoming = g.incoming
    if not (incoming.get('geoid') or incoming.get('city')):
        logger.warning("Engineer: invalid input paras")
        return jsonify(success=False,message="Invalid paras")

    name, geoid = incoming.get('city'), incoming.get('geoid')
    city_region = CityRegion(name=name,geoid=geoid)
    result = city_region.get_child_regions_imp()

    return jsonify(success=True, result=result)