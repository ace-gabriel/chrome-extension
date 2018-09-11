import numpy as np
import pandas as pd
from index import app,db,es,redis_store,limiter,home_cache

import psycopg2
import psycopg2.extras
import json
from collections import OrderedDict
from sqlalchemy import create_engine



def get_city_sources(city):

    RENT, SALE, SOLD = 1,2,4
    ROOMS_LENGTH = 20000

    query_rent = {
              "query": {
                "bool": {
                  "must": [{"match_phrase":{"city":city}}, {"match_phrase":{"status":RENT}}],
                  "must_not": [{"match_phrase":{"room_type":{"query": ""}}}]
                }
              }
            }

    rent = es.search(
                    body=query_rent,
                    size=ROOMS_LENGTH,
                    )['hits']['hits']

    query_sale = {
              "query": {
                "bool": {
                  "must": [{"match_phrase":{"city":city}}, {"match_phrase":{"status":SALE}}],
                  "must_not": [{"match_phrase":{"room_type":{"query": ""}}}]
                }
              }
            }

    sale = es.search(
                    body=query_sale,
                    size=ROOMS_LENGTH,
                    )['hits']['hits']

    query_sold = {
              "query": {
                "bool": {
                  "must": [{"match_phrase":{"city":city}}, {"match_phrase":{"status":SOLD}}],
                  "must_not": [{"match_phrase":{"room_type":{"query": ""}}}]
                }
              }
            }

    sold = es.search(
                    body=query_sold,
                    size=ROOMS_LENGTH,
                    )['hits']['hits']

    listing_price = np.median(np.array(list(item['_source']['house_price_dollar'] for item in sale if isinstance(item['_source']['house_price_dollar'], float))))
    sold_price = np.median(np.array(list(item['_source']['house_price_dollar'] for item in sold if isinstance(item['_source']['house_price_dollar'], float))))
    rent = np.median(np.array(list(item['_source']['rent'] for item in rent if isinstance(item['_source']['rent'], float))))

    return {"listing_price" : listing_price, "sold_price" : sold_price, "rent" : rent}



def reject_outliers(data, m = 2):
    return data[abs(data - np.mean(data)) < m * np.std(data)]

def scoring_neighborhood(city):

    HIGH, MED, LOW = 3, 2, -3
    SCORE_OFFSET = 2
    ADJUST = 30

    res = db.session.execute("select * from neighbor where city = '%s'" % city)
    data = res.fetchall()

    df = pd.DataFrame(columns = ['id', 'neighbor_id', 'centroid', 'name', 'url', 'crime', 'demographic',
     'real_estate', 'overview', 'school', 'property', 'city'])

    columns_zc = ['id', 'neighbor_id', 'centroid', 'name', 'url', 'crime', 'demographic',
     'real_estate', 'overview', 'school', 'property', 'city']

    for i in range(0, 12):
        df[columns_zc[i]] = list(data[j][i] for j in range(0, len(data)))

    centers = list('(' + item + ')' for item in df['centroid'])
    df['centroid'] = centers
    df['general_score'] = df['crime'] * LOW + df['demographic'] * MED + df['real_estate'] + df['school'] * HIGH
    # adjust score
    if min(df['general_score']) < 0:
        df['general_score'] = (df['general_score'] - min(df['general_score'])) * 100 / (max(df['general_score'] - min(df['general_score'])) + SCORE_OFFSET)

    df['school_score'] = df['school'] * 9.8
    df['crime_score'] = 100 - (df['crime'] * 9.8)

    overview = df.sort_values('general_score', ascending=False)[:3]
    school = df.sort_values('school_score', ascending=False)[:3]
    crime = df.sort_values('crime_score', ascending=False)[:3]

    mg_score, ms_score, mc_score = np.mean(reject_outliers(df['general_score'])) + ADJUST, np.mean(reject_outliers(df['school_score'])) + ADJUST, np.mean(reject_outliers(df['crime_score'])) + ADJUST

    stats = {

    "mg_score" : '%.2f' % mg_score,
    "ms_score" : '%.2f' % ms_score,
    "mc_score" : '%.2f' % mc_score,
    "g_first" : overview.loc[overview.index.values[0]]['name'],
    "g_second" : overview.loc[overview.index.values[1]]['name'],
    "g_third" : overview.loc[overview.index.values[2]]['name'],
    "s_first" : school.loc[school.index.values[0]]['name'],
    "s_second" : school.loc[school.index.values[1]]['name'],
    "s_third" : school.loc[school.index.values[2]]['name'],
    "c_first" : crime.loc[crime.index.values[0]]['name'],
    "c_second" : crime.loc[crime.index.values[1]]['name'],
    "c_third" :crime.loc[crime.index.values[2]]['name']


    }

    return stats


def map_geoid(engine, city, state, schema='acs2016_1yr'):

    us_state_abbrev = {

    'Alabama': 'AL',
    'Alaska': 'AK',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY',
}


    states = {v: k for k, v in us_state_abbrev.items()}
    search_str = city + ' city, ' + states[state]
    print(search_str)
    cur = create_engine(engine)
    rs = cur.execute("SELECT geoid FROM {schema}.geoheader WHERE name='{str}';".format(schema=schema, str=search_str))

    data = rs.fetchone()
    if not data:
        return None
    else:
        return rs.fetchone().values()[0]

