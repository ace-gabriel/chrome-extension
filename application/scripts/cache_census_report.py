from ..utils.query_census import query_census_detail
from index import app,db
from ..models import Area, CensusReport
from ..utils.type import *
from sqlalchemy import create_engine, text
import sys

engine_str = app.config['SQLALCHEMY_BINDS']['datawarehouse']

def upsert_census_report(type, geoid):
    result_census = query_census_detail(engine_str, geoid)
    cr = CensusReport(type=type, geoid=geoid, census=result_census)
    cr.geoid = cr.geoid.split('US')[-1]

    try:
        db.session.add(cr)
        db.session.commit()
    except:
        db.session.rollback()
    print "Finished geoid:{}".format(geoid)

def get_pattern_geoid_from_geoheader(pattern,schema='acs2016_1yr'):
    cur = create_engine(engine_str)
    print(cur)
    result = []
    try:
        query = text( "Select distinct geoid from {schema}.geoheader where geoid like '{pattern}';".format(schema=schema,pattern=pattern))
        print query
        rs = cur.execute(query)
        for row in rs:
            result.append(row[0])
    except Exception as e:
        print e
        pass

    return result

if __name__ == '__main__':
    if len(sys.argv)!=2:
        print("Invalid paras")
        exit()

    region_type = int(sys.argv[1])
    # insert census of state
    if region_type==0:
        type = CENSUS_REPORT_TYPE_STATE
        # insert census of state
        states = ['01','02','04','05','06','08','09','10','11','12','13','15','16','17','18','19','20','21','22','23','24',
                  '25','26','27','28','29','30','31','32','33','34','35','36','37','38','39','40','41','42','44','45','46',
                  '47','48','49','50','51','53','54','55','56','60','66','69','72','78']
        for state in states:
            long_geoid = '04000US'+state
            upsert_census_report(type=type,geoid=long_geoid)

    # insert census of area
    if region_type==1:
        type = CENSUS_REPORT_TYPE_MSA
        areas = db.session.query(Area).all()
        for area in areas:
            long_geoid = '31000US'+area.geoid
            upsert_census_report(type=type, geoid=long_geoid)

    # insert census of county
    if region_type==2:
        type = CENSUS_REPORT_TYPE_COUNTY
        geoids = get_pattern_geoid_from_geoheader(pattern='05000US')
        for g in geoids:
            upsert_census_report(type=type,geoid=g)

    # insert census of city
    if region_type==3:
        type = CENSUS_REPORT_TYPE_CITY
        geoids = get_pattern_geoid_from_geoheader(pattern='16000US%')
        for g in geoids:
            upsert_census_report(type=type, geoid=g)
