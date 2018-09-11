# -*- coding: utf-8 -*-
from . import Region
from index import db, es
from application.models import Area, CensusReport
from ..utils.converter import to_dict_from_model
from application.utils.esquery import EsqueryHelper
from application.utils.type import CENSUS_REPORT_TYPE_MSA
import json

class MsaRegion(Region):
    area = None

    def __init__(self,name=None,geoid=None):
        if name is not None:
            self.area = db.session.query(Area).filter_by(eng_name=name).first()
        elif geoid is not None:
            self.area = db.session.query(Area).filter_by(geoid=geoid).first()

        self.geoid = self.area.geoid if self.area else None

        # area info inside redis
        if self.area:
            self.area_cached = EsqueryHelper.get_stats_by_area_id(self.area.geoid)


    def get_region_geo_imp(self):
        result = {}
        if self.area:
            keys_to_return = ["eng_name","geoid","lat","lng","layer_type","properties"]
            result ={k:v for k,v in to_dict_from_model(self.area).items() if k in keys_to_return}
        return result

    def get_census_report_imp(self):
        # census data
        self.area_census = db.session.query(CensusReport).filter_by(type=CENSUS_REPORT_TYPE_MSA,geoid=self.geoid).first()
        result = {}
        if self.area_census:
            result = self.area_census.census
        return result

    def get_real_estate_imp(self):
        result = {}
        if self.area_cached:
            result = self.area_cached
        return result

    def get_house_within_region_imp(self):
        geometry = self.area.properties['features'][0]['geometry']
        result = EsqueryHelper.get_documents_by_geoshape(geometry=geometry)
        return result

    def get_child_regions_imp(self,func_return="get_region_geo_imp"):
        from application.region.city import CityRegion
        result = []
        if self.area and self.area.cities:
            for c in self.area.cities:
                city_region = CityRegion(geoid=c.geoid)
                func_result = getattr(city_region,func_return)()
                if func_result:
                    result.append(func_result)
        return {"city":result}

    def get_cities_list(self):
        result = []
        if self.area and self.area.cities:
            for c in self.area.cities:
                if c.geoid:
                    result.append(c.geoid)
        return result

    def get_parent_region_imp(self):
        pass