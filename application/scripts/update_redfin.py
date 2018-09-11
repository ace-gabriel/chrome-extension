from index import app
import pandas

dproperty = app.config['SQLALCHEMY_DATABASE_URI']
df = pandas.read_csv('/Users/jerry/Desktop/redfin_region_datacenter_metro.csv',
                     sep='\t', encoding='utf-16')

df.to_sql('redfin_market', dproperty, index=False, if_exists='append', chunksize=1000)
