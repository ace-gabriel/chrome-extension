#GLOBAL SETTNG FOR ALL COMPONETN

# STATISTICS IN REDIS
AREA_STATISTICS = 'area_statistics'
NEIGHBORHOOD_STATISTICS = 'neighborhood_statistics'

# PARAS TO CALCULATE IRR IN REDIS
AREA_STATISTICS = 'area_statistics'
NEIGHBORHOOD_STATISTICS = 'neighborhood_statistics'

DEFAULT_STATUS=2
VILLASORT=['single'] #each villa keyword NEED ONLY ONE WORD!
APARTSORT=['apartment','condo']

ONLINE_DAY={'3':['3','lt'],'7':['7','lt'],'15':['15','lt'],'30':['30','lt'],'30gt':['30','gt'],'0':['0','gt'],'60':['60','lt']}


# ratio ranges
INCREASE_RATIO_MAX = 0.10
RENTAL_INCOME_RATIO_MAX = 0.157
AIRBNB_RENTAL_RATIO_MAX = 0.30

HOME_INDEX = 'rooms'
HOME_TYPE = 'room'

# FIELDS
FIELDS_WHITE_LIST =["area","neighborhood","house_price_dollar","rent","increase_ratio"]


# UPPER BEDROOM
UPPER_BED_SHOW = 20
UPPER_HOUSE_PRICE_SHOW = 10000000   # 10m
