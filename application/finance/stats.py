import numpy as np
import pandas as pd
from index import app,db,es,redis_store,limiter,home_cache
from appr import calcappr

EXCELLENT_SCORE = 20
GOOD_SCORE = 18
MEDIUM_SCORE = 16
LOW_SCORE = 14
BAD_SCORE = 12

def GetData(db):
    # all houses with rent data
    # select all the rent_status houses
    #print(str(db[1]['_source']['location']['coordinates'][0]) + ',' + str(db[1]['_source']['location']['coordinates'][1]))

    array = list(i for i in range(len(db)) if isinstance(db[i]['_source']['increase_ratio'], float) and not pd.isnull(db[i]['_source']['increase_ratio']) and db[i]['_source']['size'] > 0
        and db[i]['_source']['status'] == 2 and db[i]['_source']['increase_ratio'] != 'NaN' and not pd.isnull(
            db[i]['_source']['beds']) and not pd.isnull(db[i]['_source']['baths']) and db[i]['_source']['size'] > 0 and isinstance(db[i]['_source']['rent'], float)
            and not pd.isnull(db[i]['_source']['house_price_dollar']))

    for i in array:
        db[i]['_source']['url'] = 'https://www.zillow.com/homedetails/' + str(db[i]['_source']['source_id']) + '_zpid/'

    dbs = pd.DataFrame(columns=['Address', 'RoomType', 'Appr', 'Rent', 'listing_price', 'Beds', 'Baths', 'Size', 'Revenue', 'Ratio', 'Cap', 'Score', 'url', 'coordinate'])

    dbs['Appr'] = list(db[i]['_source']['increase_ratio'] for i in array)
    dbs['Beds'] = list(db[i]['_source']['beds'] for i in array)
    dbs['Baths'] = list(db[i]['_source']['baths'] for i in array)
    dbs['Size'] = list(db[i]['_source']['size'] for i in array)
    dbs['RoomType'] = list(db[i]['_source']['room_type'] for i in array)
    dbs['listing_price'] = list(db[i]['_source']['house_price_dollar'] for i in array)
    dbs['Rent'] = list(db[i]['_source']['rent'] for i in array)
    dbs['Address'] = list(db[i]['_source']['addr'] for i in array)
    dbs['Appr'] *= 100
    dbs['Revenue'] = dbs['Rent'] * 12 - dbs['listing_price'] * 0.035
    dbs['Ratio'] = 100 * ((dbs['Rent'] * 12) / dbs['listing_price'])
    dbs['Cap'] = dbs['Appr'] + dbs['Ratio'] - 3.5
    dbs['url'] = list(db[i]['_source']['url'] for i in array)
    dbs['status'] = list(db[i]['_source']['status'] for i in array)
    dbs['coordinate'] = list(str(db[i]['_source']['location']['coordinates'][1]) + ',' + str(db[i]['_source']['location']['coordinates'][0]) for i in array)

    return dbs

def GetTargets(indexes, frames, item):

    arr = []

    # within 5 miles..first get all the houses with same roomtype
    for i in indexes:

        if (frames.loc[i]['RoomType'] == item['RoomType']) or (frames.loc[i]['Beds'] == item['Beds'] and int(item['Baths']) == int(frames.loc[i]['Baths'])):
            arr.append(i)

    return pd.DataFrame(list(frames.loc[i] for i in arr))


def CalcStats(frame):

    result = {'Revenue' : {}, 'listing_price' : {}, 'Appr' : {}, 'Ratio' : {}, 'Cap' : {}}

    percentile = ['90', '75', '50', '25']

    for item in percentile:

        result['Revenue'][item] = np.percentile(frame['Revenue'], int(item))
        result['listing_price'][item] = int(np.percentile(frame['listing_price'], int(item)))
        result['Appr'][item] = float(np.percentile(frame['Appr'], int(item)))
        result['Ratio'][item] = float(np.percentile(frame['Ratio'], int(item)))
        result['Cap'][item] = float(np.percentile(frame['Cap'], int(item)))


    return result


def GetScore(stats, data, name):

    if float(data) < stats[name]['25']:
        return BAD_SCORE
    elif float(data) < stats[name]['50'] and float(data) >= stats[name]['25']:
        return LOW_SCORE
    elif float(data) < stats[name]['75'] and float(data) >= stats[name]['50']:
        return MEDIUM_SCORE
    elif float(data) < stats[name]['90'] and float(data) >= stats[name]['75']:
        return GOOD_SCORE
    else:
        return EXCELLENT_SCORE

def calcscore(res_score, item):

    db = GetData(res_score['hits']['hits'])

    target = GetTargets(db.index.values, db, item)

    if len(target) == 0:
        return 'N/A'

    stats = CalcStats(db)


    def score(res = res_score, stats = stats, fact1 = 'listing_price', fact2 = 'Appr', fact3 = 'Revenue', fact4 = 'Cap', item = item):

        cost_score = 32 - GetScore(stats, item[fact1], fact1)
        appreciation_score = GetScore(stats, item[fact2], fact2)
        cap_score = GetScore(stats, item[fact4], fact4)


        if appreciation_score == EXCELLENT_SCORE:
            risk_score = BAD_SCORE
        elif appreciation_score == GOOD_SCORE:
            risk_score = LOW_SCORE
        elif appreciation_score == MEDIUM_SCORE:
            risk_score = MEDIUM_SCORE
        elif appreciation_score == LOW_SCORE:
            risk_score = GOOD_SCORE
        else:
            risk_score = EXCELLENT_SCORE

        rent_score = GetScore(stats, item[fact3], fact3)



        frame_risk_score = []
        frame_cost_score = np.array(list(32 - GetScore(stats, target.loc[i][fact1], fact1) for i in target.index.values))
        frame_appr_score = np.array(list(GetScore(stats, target.loc[i][fact2], fact2) for i in target.index.values))
        frame_rent_score = np.array(list(GetScore(stats, target.loc[i][fact3], fact3) for i in target.index.values))
        frame_cap_score = np.array(list(GetScore(stats, target.loc[i][fact4], fact4) for i in target.index.values))

        for score in frame_appr_score:
            if score == EXCELLENT_SCORE:
                risk_score = BAD_SCORE
            elif score == GOOD_SCORE:
                risk_score = LOW_SCORE
            elif score == MEDIUM_SCORE:
                risk_score = MEDIUM_SCORE
            elif score == LOW_SCORE:
                risk_score = GOOD_SCORE
            else:
                risk_score = EXCELLENT_SCORE
            frame_risk_score.append(score)

        frame_risk_score = np.array(frame_risk_score)
        frame_score = frame_risk_score + frame_appr_score + frame_rent_score + frame_cost_score + frame_cap_score
        risk_score = 32 - appreciation_score
        total_score = cost_score + appreciation_score + risk_score + rent_score + cap_score
        #print(total_score, cost_score, appreciation_score, risk_score, rent_score, cap_score)
        #print(np.median(frame_cost_score), np.median(frame_appr_score), np.median(frame_risk_score), np.median(frame_rent_score), np.median(frame_cap_score))

        return {'item-total-score': total_score, 'cost-score': cost_score, 'appreciation-score': appreciation_score,
                 'risk-score': risk_score, 'rent-score': rent_score, 'cap-score': cap_score, 'frame-score': frame_score,
                 'nm-cost': np.median(frame_cost_score), 'nm-appr': np.median(frame_appr_score), 'nm-risk': np.median(frame_risk_score),
                 'nm-rent': np.median(frame_rent_score), 'nm-cap': np.median(frame_cap_score)}

    data = score()

    target['Score'] = data['frame-score']
    median_score = np.median(data['frame-score'])

    res_db = target.sort_values('Score', ascending = False)
    #print(res_db)
    first_index, second_index, third_index = res_db.index.values[0], res_db.index.values[1], res_db.index.values[2]
    first, second, third = res_db.loc[first_index]['Address'], res_db.loc[second_index]['Address'], res_db.loc[third_index]['Address']
    first_addr, second_addr, third_addr = res_db.loc[first_index]['url'], res_db.loc[second_index]['url'], res_db.loc[third_index]['url']
    first_price, second_price, third_price = res_db.loc[first_index]['listing_price'], res_db.loc[second_index]['listing_price'], res_db.loc[third_index]['listing_price']

    # start fix appreciation
    top_indexes = [first_index, second_index, third_index]
    top_apprs = []

    for index in top_indexes:
        # make iterative new es_calls
        centroid = res_db.loc[index]['coordinate']
        nearby_range = "3mi"
        room_length = 6000

        query = {
                    "query": {
                      "bool": {
                        "must": [],
                        "filter": {
                            "geo_distance" : {
                                      "distance" : nearby_range,
                                      "location_point" : centroid,
                                  }
                        },
                        #"must": [{"match_phrase":{"status":rent_status}}],
                        "must_not": [{"match_phrase":{"room_type":{"query": ""}}}]
                      }
                    },
                    "sort":[
                      {
                        "_geo_distance" : {
                          "location_point" : centroid,
                          "order": "asc",
                          "unit": "mi"
                        }
                      }
                    ]
                  }

        res = es.search(
                        body=query,
                        size=room_length,
                        )
        item = {'RoomType': res_db.loc[index]['RoomType'], 'Beds': res_db.loc[index]['Beds'], 'Baths':
        res_db.loc[index]['Baths'], 'size': res_db.loc[index]['Size'], 'Revenue': res_db.loc[index]['Revenue'],
        'Cap': res_db.loc[index]['Cap'], 'Appr': res_db.loc[index]['Appr'], 'listing_price':res_db.loc[index]['listing_price']}

        top_apprs.append(calcappr(res, item))

    first_appr, second_appr, third_appr = top_apprs[0],top_apprs[1],top_apprs[2]
    #print("TOP", top_apprs)
    # end fix appreciation
    first_cash, second_cash, third_cash = res_db.loc[first_index]['Ratio'], res_db.loc[second_index]['Ratio'], res_db.loc[third_index]['Ratio']


    result = {'price': stats['listing_price']['50'], 'appr': stats['Appr']['50'], 'revenue': stats['Revenue']['50'], 'score': data['item-total-score'],
    'cost-score': data['cost-score'],'appr-score': data['appreciation-score'],'risk-score': data['risk-score'], 'rent-score': data['rent-score'],
    'cap-score': data['cap-score'],'ratio' : stats['Ratio']['50'], 'cap': stats['Cap']['50'], 'median_score': median_score, 'first': first, 'second' : second, 'third': third,
              'first_address': first_addr, 'second_address': second_addr, 'third_address': third_addr, 'nm-cost': data['nm-cost'], 'nm-appr': data['nm-appr'], 'nm-risk': data['nm-risk'],
              'nm-rent': data['nm-rent'], 'nm-cap': data['nm-cap'], 'first_price': first_price, 'first_appr': first_appr, 'first_cash': first_cash,
              'second_price': second_price, 'second_appr': second_appr, 'second_cash': second_cash, 'third_price': third_price, 'third_appr': third_appr, 'third_cash': third_cash}

    return result
