# -*- coding: utf-8 -*-
import abc

class RegionAbstraction(object):
    """
    Define the abstraction's interface for region
    """
    def __init__(self, imp):
        self._imp = imp

    def get_region_geo(self):
        # 返回该region的地理区位信息
        return self._imp.get_region_geo_imp()

    def get_census_report(self):
        # 返回该region的census report信息
        return self._imp.get_census_report_imp()

    def get_real_estate(self):
        # 返回该region的区域房产数据
        return self._imp.get_real_estate_imp()

    def get_house_within_region(self):
        # 返回该region内所有房源数据
        return self._imp.get_house_within_region_imp()

    def get_child_regions(self):
        # 返回该region内子region
        return self._imp.get_child_regions_imp()

    def get_parent_region(self):
        # 返回该region内父region
        return self._imp.get_parent_region_imp()

    

class Region(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_region_geo_imp(self):
        pass

    @abc.abstractmethod
    def get_census_report_imp(self):
        pass

    @abc.abstractmethod
    def get_real_estate_imp(self):
        pass

    @abc.abstractmethod
    def get_house_within_region_imp(self):
        pass

    @abc.abstractmethod
    def get_child_regions_imp(self):
        pass

    @abc.abstractmethod
    def get_parent_region_imp(self):
        pass