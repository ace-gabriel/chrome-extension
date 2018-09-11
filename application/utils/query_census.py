#!/bin/python
import psycopg2
import psycopg2.extras
import json
from collections import OrderedDict
from sqlalchemy import create_engine

def sum(data, *columns):
  def reduce_fn(x, y):
    if x and y:
      return x + y
    elif x and not y:
      return x
    elif y and not x:
      return y
    else:
      return None

  return reduce(reduce_fn, map(lambda col: data[col], columns))


def maybe_int(i):
  try:
    return int(i)
  except:
    return i


def query_census_detail(engine, geoid, schema='acs2016_1yr'):
  cur = create_engine(engine)
  print(cur)
  doc = OrderedDict(geography=dict())
  ######## Geoheader name ########

  try:
    rs = cur.execute("SELECT name FROM {schema}.geoheader WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    print('data', data)
    doc['geography'] = dict(name=data['name'],
                            geoid=geoid)
  except Exception as e:
      print(e)


  ######## Population - Median Age ########
  try:
    rs = cur.execute("SELECT * FROM {schema}.B01002 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['population'] = OrderedDict()
    doc['population']['median_age'] = dict(total=maybe_int(data['b01002001']),
                                           male=maybe_int(data['b01002002']),
                                           female=maybe_int(data['b01002003']))
  except:
    pass

  ######## Population - Total ########
  try:
    rs = cur.execute("SELECT * FROM {schema}.B01003 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['population']['total'] = maybe_int(data['b01003001'])
  except:
      pass

  ########## Population by Age Range ########
  try:
    rs = cur.execute("SELECT * FROM {schema}.B01001 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['population']['gender'] = OrderedDict([
      ('0-9', dict(male=maybe_int(sum(data, 'b01001003', 'b01001004')),
                   female=maybe_int(sum(data, 'b01001027', 'b01001028')))),
      ('10-19', dict(male=maybe_int(sum(data, 'b01001005', 'b01001006', 'b01001007')),
                     female=maybe_int(sum(data, 'b01001029', 'b01001030', 'b01001031')))),
      ('20-29', dict(male=maybe_int(sum(data, 'b01001008', 'b01001009', 'b01001010', 'b01001011')),
                     female=maybe_int(sum(data, 'b01001032', 'b01001033', 'b01001034', 'b01001035')))),
      ('30-39', dict(male=maybe_int(sum(data, 'b01001012', 'b01001013')),
                     female=maybe_int(sum(data, 'b01001036', 'b01001037')))),
      ('40-49', dict(male=maybe_int(sum(data, 'b01001014', 'b01001015')),
                     female=maybe_int(sum(data, 'b01001038', 'b01001039')))),
      ('50-59', dict(male=maybe_int(sum(data, 'b01001016', 'b01001017')),
                     female=maybe_int(sum(data, 'b01001040', 'b01001041')))),
      ('60-69', dict(male=maybe_int(sum(data, 'b01001018', 'b01001019', 'b01001020', 'b01001021')),
                     female=maybe_int(sum(data, 'b01001042', 'b01001043', 'b01001044', 'b01001045')))),
      ('70-79', dict(male=maybe_int(sum(data, 'b01001022', 'b01001023')),
                     female=maybe_int(sum(data, 'b01001046', 'b01001047')))),
      ('80+', dict(male=maybe_int(sum(data, 'b01001024', 'b01001025')),
                   female=maybe_int(sum(data, 'b01001048', 'b01001049'))))
    ])
  except:
      pass

  ########## Income ########
  try:
    rs = cur.execute("SELECT * FROM {schema}.B19001 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['income'] = OrderedDict()
    ### children ###
    doc['income'] = OrderedDict(
      [
        ('0-50k', maybe_int(sum(data, 'b19001002', 'b19001003', 'b19001004', 'b19001005',
                                'b19001006', 'b19001007', 'b19001008', 'b19001009',
                                'b19001010'))),
        ('50-100k', maybe_int(sum(data, 'b19001011', 'b19001012', 'b19001013'))),
        ('100-200k', maybe_int(sum(data, 'b19001014', 'b19001015', 'b19001016'))),
        ('200k+', maybe_int(sum(data, 'b19001017')))
      ]
    )
  except:
      pass

  ########## Poverty ########
  try:
    rs = cur.execute("SELECT * FROM {schema}.B17001 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['poverty'] = OrderedDict()
    ### children ###
    doc['poverty']['children'] = OrderedDict(
      [
        ('Poverty',
         dict(male=maybe_int(sum(data, 'b17001004', 'b17001005', 'b17001006', 'b17001007', 'b17001008', 'b17001009')),
              female=maybe_int(sum(data, 'b17001018', 'b17001019', 'b17001020', 'b17001021', 'b17001022', 'b17001023')))),
        ('Non-poverty',
         dict(male=maybe_int(sum(data, 'b17001033', 'b17001034', 'b17001035', 'b17001036', 'b17001037', 'b17001038')),
              female=maybe_int(sum(data, 'b17001047', 'b17001048', 'b17001049', 'b17001050', 'b17001051', 'b17001052'))))
      ]
    )
  except:
      pass
  ### seniors ###
  try:
    doc['poverty']['seniors'] = OrderedDict(
      [
        ('Poverty', dict(male=maybe_int(sum(data, 'b17001015', 'b17001016')),
                         female=maybe_int(sum(data, 'b17001029', 'b17001030')))),
        ('Non-poverty',
         dict(male=maybe_int(sum(data, 'b17001044', 'b17001045')), female=maybe_int(sum(data, 'b17001058', 'b17001059'))))
      ]
    )
  except:
      pass

  ########## Transportation to work ########
  try:
    rs = cur.execute("SELECT * FROM {schema}.B08006 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['transport'] = OrderedDict(
      [
        ('Drove alone', maybe_int(sum(data, 'b08006003'))),
        ('Carpooled', maybe_int(sum(data, 'b08006004'))),
        ('Public transit', maybe_int(sum(data, 'b08006008'))),
        ('Bicycle', maybe_int(sum(data, 'b08006014'))),
        ('Walked', maybe_int(sum(data, 'b08006015'))),
        ('Other', maybe_int(sum(data, 'b08006016'))),  # Taxicab, motorcycle, or other means
        ('Worked at home', maybe_int(sum(data, 'b08006017')))
      ]
    )
  except:
      pass

  ########## House ########
  doc['housing'] = OrderedDict()
  ### Occupancy ###
  try:
    rs = cur.execute("SELECT * FROM {schema}.B25002 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['housing']['occupancy'] = OrderedDict(
      [
        ('Occupied', maybe_int(sum(data, 'b25002002'))),
        ('Vacant', maybe_int(sum(data, 'b25002003'))),
        ('Total', maybe_int(sum(data, 'b25002001')))
      ]
    )
  except:
      pass
  ### Tenure ###
  try:
    rs = cur.execute("SELECT * FROM {schema}.B25003 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['housing']['tenure'] = OrderedDict(
      [
        ('Owner occupied', maybe_int(sum(data, 'b25003002'))),
        ('Renter occupied', maybe_int(sum(data, 'b25003003'))),
        ('Total', maybe_int(sum(data, 'b25003001')))
      ]
    )
  except:
      pass
  ### Units in Structure ###
  try:
    rs = cur.execute("SELECT * FROM {schema}.B25024 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['housing']['structure'] = OrderedDict(
      [
        ('Single unit', maybe_int(sum(data, 'b25024002', 'b25024003'))),
        (
        'Multi-unit', maybe_int(sum(data, 'b25024004', 'b25024005', 'b25024006', 'b25024007', 'b25024008', 'b25024009'))),
        ('Mobile home', maybe_int(sum(data, 'b25024010'))),
        ('Boat, RV, van, etc.', maybe_int(sum(data, 'b25024011'))),
        ('Total', maybe_int(sum(data, 'b25024001')))
      ]
    )
  except:
      pass
  ### Year moved in ###
  try:
    rs = cur.execute("SELECT * FROM {schema}.B25026 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['housing']['move-in'] = OrderedDict(
      [
        ('< 1980', maybe_int(sum(data, 'b25026008', 'b25026015'))),
        ('1980s', maybe_int(sum(data, 'b25026007', 'b25026014'))),
        ('1990s', maybe_int(sum(data, 'b25026006', 'b25026013'))),
        ('2000s', maybe_int(sum(data, 'b25026005', 'b25026012'))),
        ('2010-2014', maybe_int(sum(data, 'b25026004', 'b25026011'))),
        ('2005 +', maybe_int(sum(data, 'b25026003', 'b25026010'))),
      ]
    )
  except:
      pass
  ### Value ###
  try:
    rs = cur.execute("SELECT * FROM {schema}.B25075 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['housing']['value'] = OrderedDict(
      [
        ('< 100k', maybe_int(sum(data, 'b25075002', 'b25075003', 'b25075004', 'b25075005', 'b25075006', 'b25075007',
                                 'b25075008', 'b25075009', 'b25075010', 'b25075011', 'b25075012', 'b25075013',
                                 'b25075014'))),
        ('100k-200k', maybe_int(sum(data, 'b25075015', 'b25075016', 'b25075017', 'b25075018'))),
        ('200k-300k', maybe_int(sum(data, 'b25075019', 'b25075020'))),
        ('300k-400k', maybe_int(sum(data, 'b25075021'))),
        ('400k-500k', maybe_int(sum(data, 'b25075022'))),
        ('500k-1m', maybe_int(sum(data, 'b25075023', 'b25075024'))),
        ('1m+', maybe_int(sum(data, 'b25075025', 'b25075026', 'b25075027'))),
        ('Total', maybe_int(sum(data, 'b25075001'))),
      ]
    )
  except:
      pass

  ### Geographical mobility ###
  try:
    rs = cur.execute("SELECT * FROM {schema}.B07003 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['housing']['mobility'] = OrderedDict(
      [
        ('Same house', maybe_int(sum(data, 'b07003004'))),
        ('From same county', maybe_int(sum(data, 'b07003007'))),
        ('From different county', maybe_int(sum(data, 'b07003007'))),
        ('From different state', maybe_int(sum(data, 'b07003013'))),
        ('From abroad', maybe_int(sum(data, 'b07003016'))),
        ('Total', maybe_int(sum(data, 'b07003001'))),
      ]
    )

  except:
      pass

  ########## Education ########
  try:
    rs = cur.execute("SELECT * FROM {schema}.B15002 WHERE geoid='{geoid}';".format(schema=schema, geoid=geoid))
    data = rs.fetchone()
    doc['education'] = dict()
    doc['education']['attainment'] = OrderedDict([
      ('No degree', maybe_int(
        sum(data,
            'b15002003', 'b15002004', 'b15002005', 'b15002006', 'b15002007', 'b15002008', 'b15002009', 'b15002010',
            # male
            'b15002020', 'b15002021', 'b15002022', 'b15002023', 'b15002024', 'b15002025', 'b15002026', 'b15002027'
            # female
            ))),
      ('High school', maybe_int(sum(data, 'b15002011', 'b15002028'))),
      (
      'Some College', maybe_int(sum(data, 'b15002012', 'b15002013', 'b15002029', 'b15002030', 'b15002014', 'b15002031'))),
      ('Bachelor', maybe_int(sum(data, 'b15002015', 'b15002032'))),
      ('Post-grad', maybe_int(sum(data, 'b15002016', 'b15002017', 'b15002018', 'b15002033', 'b15002034', 'b15002035'))),
      ('Total', maybe_int(sum(data, 'b15002001'))),
    ])

  except:
      pass

  return doc

if __name__ == '__main__':
  query_census_detail('05000US02020')
