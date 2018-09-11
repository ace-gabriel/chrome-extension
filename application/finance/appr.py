import pandas as pd
import numpy as np

MAX_UNITS = 21

def GetData(db):
    # all houses with rent data
    # select all the rent_status houses
    array = list(i for i in range(len(db)) if isinstance(db[i]['_source']['increase_ratio'], float) and not pd.isnull(db[i]['_source']['increase_ratio']) and db[i]['_source']['size'] > 0
        and db[i]['_source']['status'] == 2 and db[i]['_source']['increase_ratio'] != 'NaN' and not pd.isnull(
            db[i]['_source']['beds']) and not pd.isnull(db[i]['_source']['baths']) and db[i]['_source']['size'] > 0)

    dbs = pd.DataFrame(columns=['RoomType', 'Appr', 'Beds', 'Baths', 'Size'])

    dbs['Appr'] = list(db[i]['_source']['increase_ratio'] for i in array)
    dbs['Beds'] = list(db[i]['_source']['beds'] for i in array)
    dbs['Baths'] = list(db[i]['_source']['baths'] for i in array)
    dbs['Size'] = list(db[i]['_source']['size'] for i in array)
    dbs['RoomType'] = list(db[i]['_source']['room_type'] for i in array)

    return dbs


def GetTargets(indexes, frames, item):

    arr = []

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



def calcappr(frame, item):

    db = frame['hits']['hits']
    frame = GetData(db)
    target = GetTargets(frame.index.values, frame, item)
    if len(target) == 0:
        return 'N/A'
    else:
        return float(np.percentile(target['Appr'], 50)) * 100

