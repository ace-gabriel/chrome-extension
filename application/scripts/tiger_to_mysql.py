# usage:
#   python -m application.scripts.tiger_to_mysql state
#   python -m application.scripts.tiger_to_mysql city
#   python -m application.scripts.tiger_to_mysql city_cbsa
#   python -m application.scripts.tiger_to_mysql zipcode
#   python -m application.scripts.tiger_to_mysql neighbor_city
#

from index import app, db
from ..models import State, City, Zipcode, Neighbor, County, Area
from sqlalchemy import create_engine
import json
import sys


def state(census, schema='tiger2016'):
  cur = census.execute(
    'SELECT geoid, name, stusps, intptlat, intptlon, ST_AsText(geom) '
    'FROM {schema}.state ORDER BY statefp;'.format(schema=schema))
  for row in cur.fetchall():
    state_obj = State.query.filter_by(geoid=row[0]).first()
    if state_obj == None:
      state_obj = State()
    state_obj.geoid = row[0]
    state_obj.name = row[1]
    state_obj.name_abbr = row[2]
    state_obj.lat = row[3]
    state_obj.lng = row[4]
    geom = row[5]
    geom = geom.replace('MULTIPOLYGON', '[')
    geom = geom.replace('(', '[')
    geom = geom.replace(')', ']')
    geom = geom.replace(',', '],[')
    geom = geom.replace(' ', ',')
    geom += ']'
    geom = json.loads(geom)
    state_obj.properties = {
      "type":     "FeatureCollection",
      "features": [
        {
          "type":       "Feature",
          "properties": {},
          "geometry":   {
            "type":        "MultiPolygon",
            "coordinates": geom
          }
        }
      ]
    }
    db.session.add(state_obj)
  db.session.commit()


def city(census, schema='tiger2016'):
  cur = census.execute(
    "SELECT DISTINCT geoid FROM {schema}.geoheader WHERE geoid LIKE '16000US%%';".format(schema=schema))
  geoidlist = []
  for row in cur.fetchall():
    geoidlist.append(str(row[0].split('US')[-1]))
  geoidstr = str(tuple(geoidlist))
  cur = census.execute(
    'SELECT geoid, name, statefp, intptlat, intptlon, ST_AsText(geom) '
    'FROM {schema}.place WHERE geoid in {geoidstr};'.format(schema=schema, geoidstr=geoidstr))
  for row in cur.fetchall():
    city_obj = City.query.filter_by(geoid=row[0]).first()
    if city_obj == None:
      city_obj = City()
    city_obj.geoid = row[0]
    city_obj.name = row[1]
    city_obj.state_geoid = row[2]
    city_obj.lat = row[3]
    city_obj.lng = row[4]
    geom = row[5]
    geom = geom.replace('MULTIPOLYGON', '[')
    geom = geom.replace('(', '[')
    geom = geom.replace(')', ']')
    geom = geom.replace(',', '],[')
    geom = geom.replace(' ', ',')
    geom += ']'
    geom = json.loads(geom)
    city_obj.properties = {
      "type":     "FeatureCollection",
      "features": [
        {
          "type":       "Feature",
          "properties": {},
          "geometry":   {
            "type":        "MultiPolygon",
            "coordinates": geom
          }
        }
      ]
    }
    db.session.add(city_obj)
  db.session.commit()


def city_cbsa(census, schema='tiger2016'):
  for area in Area.query.all():
    poligon = area.properties['features'][0]['geometry']['coordinates']
    poligon = json.dumps(poligon[0])
    poligon = poligon.replace(' ', '')
    poligon = poligon.replace('],[', '~')
    poligon = poligon.replace(',', ' ')
    poligon = poligon.replace('~', ',')
    poligon = poligon.replace('[', '(')
    poligon = poligon.replace(']', ')')
    poligon = 'MULTIPOLYGON' + poligon
    cur = db.session.execute(
      '''SELECT geoid FROM city
         WHERE ST_Contains(ST_GeomFromText('{poligon}'), POINT(lng, lat));
      '''.format(poligon=poligon))
    for row in cur.fetchall():
      city_obj = City.query.filter_by(geoid=row[0]).first()
      city_obj.area_geoid = area.geoid
      db.session.add(city_obj)
  db.session.commit()


def zipcode(census, schema='tiger2016'):
  cur = census.execute(
    '''SELECT geoid10, {schema}.place.geoid, intptlat10, intptlon10,
              ST_AsText({schema}.zcta5.geom)
        FROM {schema}.zcta5
        INNER JOIN {schema}.place
        ON ST_Contains({schema}.place.geom,
        ST_GeomFromText('POINT(' || ltrim(intptlon10, '+') || ' ' || ltrim(intptlat10, '+') || ')', 4326))
    '''.format(schema=schema))
  for row in cur.fetchall():
    zipcode_obj = Zipcode.query.filter_by(geoid=row[0]).first()
    if zipcode_obj == None:
      zipcode_obj = Zipcode()
    zipcode_obj.geoid = row[0]
    zipcode_obj.city_geoid = row[1]
    zipcode_obj.lat = row[2]
    zipcode_obj.lng = row[3]
    geom = row[4]
    geom = geom.replace('MULTIPOLYGON', '[')
    geom = geom.replace('(', '[')
    geom = geom.replace(')', ']')
    geom = geom.replace(',', '],[')
    geom = geom.replace(' ', ',')
    geom += ']'
    geom = json.loads(geom)
    zipcode_obj.properties = {
      "type":     "FeatureCollection",
      "features": [
        {
          "type":       "Feature",
          "properties": {},
          "geometry":   {
            "type":        "MultiPolygon",
            "coordinates": geom
          }
        }
      ]
    }
    db.session.add(zipcode_obj)
  db.session.commit()


def neighbor_city(census, schema='tiger2016'):
  for city in City.query.all():
    print city.name
    poligon = city.properties['features'][0]['geometry']['coordinates']
    poligon = json.dumps(poligon[0])
    poligon = poligon.replace(' ', '')
    poligon = poligon.replace('],[', '~')
    poligon = poligon.replace(',', ' ')
    poligon = poligon.replace('~', ',')
    poligon = poligon.replace('[', '(')
    poligon = poligon.replace(']', ')')
    poligon = 'MULTIPOLYGON' + poligon
    cur = db.session.execute(
      '''SELECT id FROM neighbor
         WHERE city_geoid is NULL and ST_Contains(ST_GeomFromText('{poligon}'),
           POINT(SUBSTRING_INDEX(centroid, ',', 1), SUBSTRING_INDEX(centroid, ',', -1)));
      '''.format(poligon=poligon))
    for row in cur.fetchall():
      neighbor_obj = Neighbor.query.filter_by(id=row[0]).first()
      neighbor_obj.city_geoid = city.geoid
      db.session.add(neighbor_obj)
    db.session.commit()


def county(census, schema='tiger2016'):
  cur = census.execute(
    'SELECT geoid, name, cbsafp, intptlat, intptlon, ST_AsText(geom) '
    'FROM {schema}.county;'.format(schema=schema))
  for row in cur.fetchall():
    county_obj = County.query.filter_by(geoid=row[0]).first()
    if county_obj == None:
      county_obj = County()
    county_obj.geoid = row[0]
    county_obj.name = row[1]
    county_obj.cbsa_geoid = row[2]
    county_obj.lat = row[3]
    county_obj.lng = row[4]
    geom = row[5]
    geom = geom.replace('MULTIPOLYGON', '[')
    geom = geom.replace('(', '[')
    geom = geom.replace(')', ']')
    geom = geom.replace(',', '],[')
    geom = geom.replace(' ', ',')
    geom += ']'
    geom = json.loads(geom)
    county_obj.properties = {
      "type":     "FeatureCollection",
      "features": [
        {
          "type":       "Feature",
          "properties": {},
          "geometry":   {
            "type":        "MultiPolygon",
            "coordinates": geom
          }
        }
      ]
    }
    db.session.add(county_obj)
  db.session.commit()


if __name__ == '__main__':
  if len(sys.argv) != 2:
    print 'argv error'
    exit()
  
  engine_str = app.config['SQLALCHEMY_BINDS']['datawarehouse']
  census = create_engine(engine_str)
  if sys.argv[1] == 'state':
    state(census)
  elif sys.argv[1] == 'city':
    city(census)
  elif sys.argv[1] == 'city_cbsa':
    city_cbsa(census)
  elif sys.argv[1][:3] == 'zip':
    zipcode(census)
  elif sys.argv[1][:8] == 'neighbor':
    neighbor_city(census)
  elif sys.argv[1] == 'county':
    county(census)
