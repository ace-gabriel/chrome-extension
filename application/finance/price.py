import pandas as pd
import numpy as np
import requests
from scipy.stats import pearsonr


def GetData(db):
    # all houses with rent data
    # select all the rent_status houses
    array = list(i for i in range(len(db)) if isinstance(db[i]['_source']['house_price_dollar'], float) and not pd.isnull(
        db[i]['_source']['beds']) and not pd.isnull(db[i]['_source']['baths']) and db[i]['_source']['size'] > 0
        and db[i]['_source']['status'] == 2)

    dbs = pd.DataFrame(columns=['Beds', 'Baths', 'Price', 'RoomType'])

    dbs['Beds'] = list(db[i]['_source']['beds'] for i in array)
    dbs['Baths'] = list(db[i]['_source']['baths'] for i in array)
    dbs['RoomType'] = list(db[i]['_source']['room_type'] for i in array)
    dbs['Price'] = list(db[i]['_source']['house_price_dollar'] for i in array)
    dbs['Status'] = list(db[i]['_source']['status'] for i in array)
    dbs['update'] = list(db[i]['_source']['updated_at'][:7] for i in array)

    drop_index = []

    for i in dbs.index.values:

        date = dbs.loc[i]['update']
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])

        if year < 2018:
            drop_index.append(i)

    dbs = dbs.drop(drop_index)


    return dbs

# Search Algorithm Logic
# Tasks: Get 10 Houses of same type
# Search within 5 miles
# If we have more than 10...then stops when num_of_houses == 10
# If we don't have enough after the iterations..
# Go find the houses with SIMILAR bathrooms and bedrooms
# Sill not enough...go and get all the off_market_houses within 1 month

def GetTargets(indexes, frames, item):

    arr = []

    MAX_UNITS = 21

    # within 5 miles..first get all the houses with same roomtype
    for i in indexes:

        if frames.loc[i]['RoomType'] == item['RoomType']:
            arr.append(i)

    if len(arr) >= MAX_UNITS:
        # if we have enough..go ahead and return
        targets = pd.DataFrame(list(frames.loc[i] for i in arr))[:MAX_UNITS]
        return targets

    elif len(arr) < MAX_UNITS:

        for i in indexes:
         # if not..find all the rooms with same number of beds and same number of baths
            if frames.loc[i]['Beds'] == item['Beds'] and int(item['Baths']) == int(frames.loc[i]['Baths']):
                arr.append(i)

    if len(arr) >= MAX_UNITS:

        targets = pd.DataFrame(list(frames.loc[i] for i in arr))[:MAX_UNITS]
        return targets

    else:
        return pd.DataFrame(list(frames.loc[i] for i in arr))

    # Finish later...if we still need more..go ahead and grab history data
    # Add on houses based on the past sold data

def GetArgs(frame, args, target):

    result = []

    for arg in args:

        num = np.mean(list(rent for (item, rent) in zip(frame[target], frame['Rent']) if item == arg))
        result.append(num)

    return result


def CalcStats(frame):

    result = {'Rent': {}, 'Size': {}, 'Size_Price': {}, 'Year': {}, 'Baths' : {}, 'Beds' : {}, 'Avg_Bath' : {}, 'Avg_Bed' : {}, 'Avg_Year' : {}}

    percentile = ['90', '75', '50', '25']

    for item in percentile:

        result['Rent'][item] = np.percentile(frame['Rent'], int(item))
        result['Size'][item] = np.percentile(frame['Size'], int(item))
        result['Size_Price'][item] = np.percentile(frame['Size_Price'], int(item))
        result['Year'][item] = int(np.percentile(frame['YearBuilt'], int(item)))
        result['Baths'][item] = int(np.percentile(frame['Baths'], int(item)))
        result['Beds'][item] = int(np.percentile(frame['Beds'], int(item)))

    bath = GetArgs(frame, list(result['Baths'].values()), 'Baths')
    bed = GetArgs(frame, list(result['Beds'].values()), 'Beds')
    year = GetArgs(frame, list(result['Year'].values()), 'YearBuilt')



    for p, t in zip(percentile, range(0,4)):

        result['Avg_Bath'][p] = bath[t]
        result['Avg_Bed'][p] = bed[t]
        result['Avg_Year'][p] = year[t]


    return result


def GetRent(item, stats, weights):

    target = max(weights.values())
    key = weights.keys()[weights.values().index(target)]

    if (key == 'size' or key == 'size_price') and not pd.isnull(item['size']):
        return 0.6 * stats['Rent']['50'] + 0.4 * stats['Size_Price']['50'] * item['size']

    elif (key == 'size' or key == 'size_price') and pd.isnull(item['size']):
        return 0.6 * stats['Rent']['50'] + 0.4 * stats['Size_Price']['25'] * stats['Size']['25']

    elif key == 'baths':
        return 0.6 * stats['Rent']['50'] + 0.4 * stats['Avg_Bath']['50']

    elif key == 'beds':
        return 0.6 * stats['Rent']['50'] + 0.4 * stats['Avg_Bed']['50']

    elif key == 'year':
        return 0.6 * stats['Rent']['50'] + 0.4 * stats['Avg_Year']['50']


def CalcWeights(frame):

    index_beds = float(pearsonr(frame['Beds'], frame['Rent'])[0])
    index_baths = float(pearsonr(frame['Baths'], frame['Rent'])[0])
    index_size = float(pearsonr(frame['Size'], frame['Rent'])[0])
    index_size_price = float(pearsonr(frame['Size_Price'], frame['Rent'])[0])
    index_year = float(pearsonr(frame['YearBuilt'], frame['Rent'])[0])

    return {"beds": index_beds, "baths": index_baths, "size": index_size, "size_price": index_size_price, "year": index_year}


def calcrent(frame, item):

    db = frame['hits']['hits']
    frames = GetData(db)
    weight = CalcWeights(frames)
    targets = GetTargets(frames.index.values, frames, item)
    if len(targets) == 0:
        return 'N/A'
    else:
        stats = CalcStats(targets)

    return float('%.2f' % GetRent(item, stats, weight))
