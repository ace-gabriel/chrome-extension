# -*- coding: utf-8 -*-
from . import Region
from index import db, es
from application.models import Area, City, CensusReport, Neighbor, State, RedfinMarket
from ..utils.converter import to_dict_from_model
from application.utils.esquery import EsqueryHelper
from application.utils.type import CENSUS_REPORT_TYPE_CITY
import json

class CityRegion(Region):

    city = None

    def __init__(self,name=None,geoid=None):
        if name is not None:
            self.city = db.session.query(City).filter_by(name=name).first()
        elif geoid is not None:
            self.city = db.session.query(City).filter_by(geoid=geoid).first()

        self.geoid = self.city.geoid if self.city else None



    def get_region_geo_imp(self):
        result = {}
        if self.city:
            keys_to_return = ["name","geoid","lat","lng","state_geoid","area_geoid","properties"]
            result ={k:v for k,v in to_dict_from_model(self.city).items() if k in keys_to_return}
        return result

    def get_parent_region_imp(self,func_return="get_region_geo_imp"):
        from application.region.state import StateRegion
        from application.region.msa import MsaRegion
        result ={}
        if self.city and self.city.state:
            state_region = StateRegion(geoid=self.city.state.geoid)
            func_result = getattr(state_region,func_return)()
            result['state'] = func_result

        if self.city and self.city.area:
            area_region = MsaRegion(geoid=self.city.area.geoid)
            func_result = getattr(area_region,func_return)()
            result['area'] = func_result
        return result

    def get_census_report_imp(self):
        # census data
        self.city_census = db.session.query(CensusReport).filter_by(type=CENSUS_REPORT_TYPE_CITY,geoid=self.geoid).first()
        result = {}
        if self.city_census:
            result = self.city_census.census
        return result

    def get_real_estate_imp(self):
        pass

    def get_house_within_region_imp(self):
        geometry = self.city.properties['features'][0]['geometry']
        result = EsqueryHelper.get_documents_by_geoshape(geometry=geometry)
        return result

    def get_redfin_market(self):
        name = self.city.name
        state_geoid = self.city.state_geoid
        state_abbr = db.session.query(State).filter_by(geoid = state_geoid).first().name_abbr
        result = []
        for row in db.session.query(RedfinMarket).filter_by(region_type = 'place', city = name, state_code = state_abbr):
            redfin_market = {}
            for key, value in vars(row).items():
                redfin_market[key] = value
            redfin_market.pop('_sa_instance_state')
            redfin_market.pop('table_id')
            redfin_market.pop('worksheet_filter')
            result.append(redfin_market)
        return result

    def get_child_regions_imp(self):
        res = db.session.query(Neighbor).filter_by(city_geoid=self.geoid).all()
        result = list(to_dict_from_model(result) for result in res)
        return result
