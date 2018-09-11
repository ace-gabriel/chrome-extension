from flask import request, jsonify, g
from flask import Blueprint
from index import app
from application.utils.auth import json_validate_logic
from application.region.neighbor import NeighborRegion

ep_neighbor_bp = Blueprint('ep_neighbor_blueprint', __name__)
logger = app.logger


@ep_neighbor_bp.route('/neighbor/geometry', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["neighbor","geoid"])
def neighbor_geometry():
    incoming = g.incoming
    name, geoid = incoming.get('neighbor'), incoming.get('geoid')

    neighbor_region = NeighborRegion(name=name,geoid=geoid)
    result = neighbor_region.get_region_geo_imp()

    return result

@ep_neighbor_bp.route('/neighbor/census', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["neighbor","geoid"])
def neighbor_census():
    incoming = g.incoming

    name, geoid = incoming.get('neighbor'), incoming.get('geoid')
    #name, geoid = "Seattle, WA (5th Ave NE / NE 131st Pl)", 123
    neighbor_region = NeighborRegion(name=name,geoid=geoid)
    result = neighbor_region.get_census_report_imp()

    return jsonify(success=True, result=result)

@ep_neighbor_bp.route('/neighbor/estate', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["neighbor","geoid"])
def neighbor_estate():
    incoming = g.incoming

    name, geoid = incoming.get('neighbor'), incoming.get('geoid')
    neighbor_region = NeighborRegion(name=name,geoid=geoid)
    result = neighbor_region.get_real_estate_imp()

    return jsonify(success=True, result=result)

@ep_neighbor_bp.route('/neighbor/property', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["neighbor","geoid"])
def neighbor_property():
    incoming = g.incoming

    name, geoid = incoming.get('neighbor'), incoming.get('geoid')
    neighbor_region = NeighborRegion(name=name,geoid=geoid)
    result = neighbor_region.get_house_within_region_imp()

    return jsonify(success=True, result=result)

@ep_neighbor_bp.route('/neighbor/scout', methods=['POST','GET'])
@json_validate_logic(filter_disjunction=["neighbor","geoid"])
def neighbor_scount():
    incoming = g.incoming
    name, geoid = incoming.get('neighbor'), incoming.get('geoid')
    neighbor_region = NeighborRegion(name=name,geoid=geoid)
    return jsonify(success=True, result = neighbor_region.get_neighborhoodscount_index())
