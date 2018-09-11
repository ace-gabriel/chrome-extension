# -*- coding: utf-8 -*-
from . import Region
from index import db, es
from flask import jsonify
from application.models import Area,Zipcode, CensusReport, Neighbor
from ..utils.converter import to_dict_from_model
from application.utils.esquery import EsqueryHelper
from application.utils.type import CENSUS_REPORT_TYPE_ZIPCODE
import json

class ZipcodeRegion(Region):

    zipcode = None

    def __init__(self,name=None,geoid=None):
        if name is not None:
            self.zipcode = db.session.query(Zipcode).filter_by(name=name).first()
        elif geoid is not None:
            self.zipcode = db.session.query(Zipcode).filter_by(geoid=geoid).first()

        self.geoid = self.zipcode.geoid if self.zipcode else None

    def get_region_geo_imp(self):
        result = {}
        if self.zipcode:
            db = to_dict_from_model(self.zipcode)
            result = {
                "geoid" : db.get('geoid'),
                "lat" : db.get('lat'),
                "lng" : db.get('lng'),
                "properties": db.get('properties'),
                "city_geoid" : db.get("city_geoid"),
            }
            print result
        return result

    def get_child_regions_imp(self):
        result = {}
        return result

    def get_parent_region_imp(self,func_return="get_region_geo_imp"):
        from application.region.city import CityRegion
        result ={}
        if self.zipcode and self.zipcode.city_geoid:
            city_region = CityRegion(geoid=self.zipcode.city_geoid)
            func_result = getattr(city_region,func_return)()
            result['city'] = func_result

        return result

    def get_census_report_imp(self):
        # census data
        self.zipcode_census = db.session.query(CensusReport).filter_by(type=CENSUS_REPORT_TYPE_ZIPCODE,geoid=self.geoid).first()
        result = {}
        if self.zipcode_census:
            result = self.zipcode_census.census
        return result

    def get_real_estate_imp(self):
        result = {}
        return  result

    def get_house_within_region_imp(self):
        geometry = self.zipcode.properties['features'][0]['geometry']
        result = EsqueryHelper.get_documents_by_geoshape(geometry=geometry)
        return result
