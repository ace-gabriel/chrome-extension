# -*- coding: utf-8 -*-
from . import Region
from index import db
from application.models import State, CensusReport
from ..utils.converter import to_dict_from_model
from application.utils.type import CENSUS_REPORT_TYPE_STATE
from application.region.city import CityRegion
from application.utils.esquery import EsqueryHelper

class StateRegion(Region):

    state = None

    def __init__(self,name=None,geoid=None):
        if name is not None:
            self.state = db.session.query(State).filter_by(name_abbr=name).first()
        elif geoid is not None:
            self.state = db.session.query(State).filter_by(geoid=geoid).first()

        self.geoid = self.state.geoid

    def get_region_geo_imp(self):
        result = {}
        if self.state:
            keys_to_return = ["name","name_abbr","geoid","lat","lng","properties"]
            result ={k:v for k,v in to_dict_from_model(self.state).items() if k in keys_to_return}
        return result

    def get_census_report_imp(self):
        # census data
        self.state_census = db.session.query(CensusReport).filter_by(type=CENSUS_REPORT_TYPE_STATE,geoid=self.geoid).first()
        result = {}
        if self.state_census:
            result = self.state_census.census
        return result

    def get_child_regions_imp(self,func_return="get_region_geo_imp"):
        result = []
        if self.state and self.state.cities:
            for c in self.state.cities:
                city_region = CityRegion(geoid=c.geoid)
                func_result = getattr(city_region,func_return)()
                if func_result:
                    result.append(func_result)
        return {"city":result}

    def get_cities_list(self):
        result = []
        if self.state and self.state.cities:
            for c in self.state.cities:
                if c.geoid:
                    result.append(c.geoid)
        return result

    def get_real_estate_imp(self):
        result = {}
        return result

    def get_parent_region_imp(self):
        return {}

    def get_house_within_region_imp(self):
        geometry = self.state.properties['features'][0]['geometry']
        result = EsqueryHelper.get_documents_by_geoshape(geometry=geometry)
        return result