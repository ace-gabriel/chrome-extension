# -*- coding: utf-8 -*-
from . import Region
from index import db, es
from flask import jsonify
from application.models import Area,Neighbor, CensusReport, Neighbor
from ..utils.converter import to_dict_from_model
from application.utils.esquery import EsqueryHelper
from application.utils.type import CENSUS_REPORT_TYPE_NEIGHBORHOOD
import json

class NeighborRegion(Region):

    neighbor = None

    def __init__(self,name=None,geoid=None):
        if name is not None:
            self.neighbor = db.session.query(Neighbor).filter_by(name=name).first()
        elif geoid is not None:
            self.neighbor = db.session.query(Neighbor).filter_by(city_geoid=geoid).first()

        self.geoid = self.neighbor.city_geoid if self.neighbor else None

    def get_region_geo_imp(self):
        result = {}
        if self.neighbor:
            db = to_dict_from_model(self.neighbor)
            result = {
                "name" : db.get('name'),
                "city" : db.get('city'),
                "city_geoid" : db.get("city_geoid"),
                "centroid" : db.get("centroid")
            }
        return jsonify(**result)

    def get_child_regions_imp(self):
        result = {}
        return result

    def get_parent_region_imp(self,func_return="get_region_geo_imp"):
        from application.region.city import CityRegion
        result ={}
        if self.neighbor and self.neighbor.city_geoid:
            city_region = CityRegion(geoid=self.neighbor.city_geoid)
            func_result = getattr(city_region,func_return)()
            result['city'] = func_result

        return result

    def get_census_report_imp(self):
        # census data
        self.neighbor_census = db.session.query(CensusReport).filter_by(type=CENSUS_REPORT_TYPE_NEIGHBORHOOD,geoid=self.geoid).first()
        result = {}
        if self.neighbor_census:
            result = self.neighbor_census.census
        return result

    def get_real_estate_imp(self):
        pass

    def get_house_within_region_imp(self):
        geometry = self.neighbor.property['geometry']
        result = EsqueryHelper.get_documents_by_geoshape(geometry=geometry)
        return result

    def get_neighborhoodscount_index(self):
        result = to_dict_from_model(self.neighbor)
        return result
