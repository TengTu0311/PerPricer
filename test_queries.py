from dbUtils import *
import os
import pandas as pd
from collections import defaultdict
import numpy as np
import time
import re
from collections import Counter
from parse_sql import QueryMetaData
import json
from pandas.errors import EmptyDataError

db = "walmart"

table_list, table_size_list, table_fields = get_fields_of_all_tables(database=db)
tuple_price_list = defaultdict(int)
history = None
domain_list = {
    "walmart.zip_code": [501, 99950],
    "walmart.latitude":[10, 70],
    "walmart.longitude": [-160.0, -66.0],
    }
history_aware = False
for table in table_list:
    tuple_price_list[table] = 1
    
table_price_list = table_size_list    
mark_sql_list = {}



mark = 'S'
sql_list = ['select country, zip_code, street_address, name, longitude, url, state, latitude, end_time, start_time, city, phone_number_1 from walmart where longitude <= -87.5987915', 
            'select country, longitude, city, street_address, latitude, url, name, phone_number_1, state, zip_code from walmart', 
            "select url, latitude, longitude, country, street_address, zip_code, state, city, phone_number_1, end_time, name, start_time from walmart where end_time like '%24:00' AND country like 'US%'", 
            'select start_time, latitude, street_address, longitude, url, city, end_time, country from walmart', 
            "select zip_code, phone_number_1, street_address, longitude, start_time, state, latitude, country from walmart where start_time like '00:%' AND end_time like '24:%'", 
            "select url, start_time, latitude, state, longitude, street_address, country, zip_code, name, phone_number_1 from walmart where zip_code > 70769 AND state like '%OH'", 
            "select phone_number_1, state, street_address, start_time from walmart where url like '%tails' AND city like 'Tha%'", 
            "select name, phone_number_1, zip_code, city from walmart where latitude <= 42.116233 AND country like 'US%' AND zip_code <= 55344", 
            "select country, phone_number_1, url, name, street_address, city, longitude, zip_code, start_time, end_time, latitude, state from walmart where street_address like '%th St' AND start_time like '%00:00'", 
            "select name, city, phone_number_1, end_time, start_time, country, street_address from walmart where state like '%TX' AND country = 'US' AND street_address like '810%'", 
            'select name, url, street_address, start_time, latitude, state, zip_code from walmart where zip_code <= 48912', 
            "select longitude, state, url, end_time, street_address, name, zip_code, latitude, phone_number_1, country from walmart where end_time like '24:%' AND phone_number_1 like '330%'", "select street_address, city, phone_number_1, country, zip_code from walmart where country like 'US%'", 
            "select end_time, country, phone_number_1, longitude, zip_code, city, street_address, url from walmart where longitude <= -98.315814 AND name like 'Kin%' AND country like '%US'", 'select country, end_time, url, zip_code, street_address, city, phone_number_1, latitude, start_time, longitude, name, state from walmart', 
            "select phone_number_1, end_time, street_address, state, url, start_time, country, name, longitude, zip_code, city, latitude from walmart where end_time like '%24:00' AND city = 'Toms River'", 
            'select url, zip_code, country, street_address, state, end_time, latitude, phone_number_1, start_time, name, longitude from walmart',
            "select url, city, zip_code, latitude, end_time, longitude, name, street_address, phone_number_1 from walmart where phone_number_1 like '%-9126' AND end_time like '%24:00' AND zip_code <= 95695", 
            "select url, state, longitude, zip_code, name, street_address, start_time, city from walmart where end_time like '%24:00' AND state = 'WI'", 
            "select state, city, street_address, latitude, zip_code, phone_number_1, url from walmart where url like '%tails' AND city like '%ngton' AND country like 'US%'"
            ]
mark_sql_list[mark] = sql_list

mark = 'SP'
sql_list = ['select distinct url from walmart', "select distinct street_address, state, end_time, zip_code, city, start_time, phone_number_1, longitude, name, country from walmart where longitude > -82.785025 AND zip_code > 66210 AND city = 'Hickory'", 'select distinct zip_code, latitude, state, start_time, longitude, end_time from walmart', "select distinct state, city from walmart where start_time like '00:%' AND street_address = '1351 Marchand Dr.'", "select distinct zip_code, country, phone_number_1, street_address, name, city, end_time, start_time, latitude from walmart where name = 'Tampa Neighborhood Market'", 'select distinct country, street_address, name, latitude, phone_number_1, end_time, zip_code, longitude, url, city, start_time, state from walmart', "select distinct city, start_time, street_address, longitude, zip_code, name, state, phone_number_1, latitude, url, country, end_time from walmart where city like '%ville'", "select distinct street_address, zip_code, start_time from walmart where end_time = '24:00' AND name like 'Cav%' AND phone_number_1 = '972-279-8700'", 'select distinct street_address from walmart', "select distinct longitude, end_time, street_address, country, start_time, zip_code, name, url, latitude, city, phone_number_1 from walmart where phone_number_1 like '309%'", "select distinct zip_code from walmart where state like 'VA%'", "select distinct longitude, start_time, name, latitude from walmart where name like 'Roc%' AND city like 'Roc%'", 'select distinct country, phone_number_1, longitude, street_address, end_time, name, zip_code, city from walmart where longitude > -82.430723', "select distinct name, longitude, country, latitude, street_address, zip_code from walmart where state like '%MO' AND start_time like '07:%'", "select distinct url, latitude, country, longitude, end_time, city from walmart where city like '%Haven' AND street_address like '%on Dr' AND start_time like '06:%'", 'select distinct state, country from walmart', 'select distinct street_address, phone_number_1, zip_code, longitude, end_time, name, state, start_time from walmart', "select distinct state, city, street_address, zip_code, name, phone_number_1, latitude, url, longitude from walmart where longitude <= -91.930707 AND city like '%tings' AND end_time like '24:%'", 'select distinct zip_code, state, city, longitude from walmart', "select distinct state, street_address, start_time, latitude, zip_code, name, end_time, url, city, country, longitude, phone_number_1 from walmart where end_time like '%24:00' AND state = 'WI'"]
mark_sql_list[mark] = sql_list

mark = 'SA'
# sql_list = ["select url, city, street_address, min(latitude) from walmart where latitude > 40.900025 AND zip_code > 47421 AND end_time like '%24:00' group by url, city, street_address", 
            # "select country, min(latitude) from walmart where city like '%ta Fe' AND country = 'US' AND street_address like '%ghway' group by country", 
            # 'select url, min(latitude) from walmart group by url', 'select start_time, state, name, min(latitude) from walmart where zip_code <= 35216 AND latitude > 36.003161 group by start_time, state, name', 
            # 'select state, street_address, name, avg(zip_code) from walmart where zip_code > 55901 group by state, street_address, name', 
            # 'select name, sum(longitude) from walmart group by name', 'select avg(zip_code) from walmart', 
            # "select start_time, sum(longitude) from walmart where state like 'WI%' AND city = 'Denton' AND longitude > -89.710518 group by start_time", 
            # "select phone_number_1, url, sum(longitude) from walmart where start_time like '%00:00' group by phone_number_1, url", 
            # 'select country, min(latitude) from walmart group by country', 
            # 'select sum(longitude) from walmart', 
            # "select start_time, url, avg(zip_code) from walmart where start_time like '00:%' AND latitude <= 40.031675 AND phone_number_1 like '407%' group by start_time, url", 
            # "select name, country, phone_number_1, avg(zip_code) from walmart where zip_code <= 7069 AND state like 'MO%' group by name, country, phone_number_1", 
            # "select url, avg(zip_code) from walmart where latitude <= 32.147489 AND url like '%tails' AND state like '%NH' group by url", 
            # 'select city, name, start_time, min(latitude) from walmart group by city, name, start_time', 
            # 'select sum(longitude) from walmart', 
            # "select country, sum(longitude) from walmart where url like 'htt%' group by country", 
            # 'select end_time, start_time, sum(longitude) from walmart group by end_time, start_time', 
            # 'select state, start_time, end_time, sum(longitude) from walmart group by state, start_time, end_time', 
            # 'select start_time, sum(longitude) from walmart where latitude <= 40.147006 group by start_time'
            # ]
sql_list = ["select avg(zip_code) from walmart where zip_code > 78213 AND street_address = '710 E Ben White Blvd'", 'select sum(latitude) from walmart where latitude > 38.76932', "select street_address, city, end_time, avg(zip_code) from walmart where state like 'NV%' AND city = 'Yelm' AND name like 'Hou%' group by street_address, city, end_time", "select sum(latitude) from walmart where name = 'Doral Supercenter'", "select street_address, start_time, end_time, sum(latitude) from walmart where country = 'US' group by street_address, start_time, end_time", "select max(longitude) from walmart where name like 'Hue%' AND end_time = '24:00'", "select street_address, sum(latitude) from walmart where start_time = '00:00' AND phone_number_1 = '919-852-0651' group by street_address", "select city, start_time, state, avg(zip_code) from walmart where street_address like '130%' AND name like 'For%' group by city, start_time, state", "select end_time, state, start_time, avg(zip_code) from walmart where street_address like '%s Hwy' AND zip_code <= 20186 AND end_time = '24:00' group by end_time, state, start_time", 'select avg(zip_code) from walmart where latitude <= 31.786216', "select avg(zip_code) from walmart where longitude <= -80.728675 AND end_time like '%24:00' AND latitude <= 34.3662191", "select start_time, country, end_time, max(longitude) from walmart where longitude <= -108.378319 AND start_time like '%00:00' AND name like '%enter' group by start_time, country, end_time", 'select city, state, avg(zip_code) from walmart where zip_code <= 29650 group by city, state', "select max(longitude) from walmart where end_time like '%24:00' AND name like '%enter' AND country = 'US'", "select url, avg(zip_code) from walmart where city like '% City' group by url", "select phone_number_1, name, max(longitude) from walmart where name like 'Gre%' group by phone_number_1, name", "select avg(zip_code) from walmart where end_time like '%24:00' AND zip_code <= 55811 AND url like '%tails'", "select url, max(longitude) from walmart where name like '%Store' group by url", "select state, name, country, avg(zip_code) from walmart where start_time like '00:%' AND country like '%US' AND phone_number_1 like '%-2048' group by state, name, country", "select state, avg(zip_code) from walmart where end_time like '24:%' AND city like 'Hor%' AND url like '%tails' group by state"]

mark_sql_list[mark] = sql_list
#
mark = 'SS'
sql_list =['select * from walmart where zip_code <= 29574', 'select * from walmart where zip_code <= 40143', 'select * from walmart where zip_code <= 64468', 'select * from walmart where zip_code <= 78245', 'select * from walmart where zip_code <= 99901']

# mark = 'SPV1'
# sql_list = [
    # 'select distinct url from walmart',
    # 'select distinct city from walmart',
    # 'select distinct start_time from walmart',
    # 'select distinct zip_code from walmart',
    #
    # ]
# mark_sql_list[mark] = sql_list
# mark = 'SPV2'
# sql_list = [
    # 'select url from walmart',
    # 'select city from walmart',
    # 'select start_time from walmart',
    # 'select zip_code from walmart',
    # ]
# mark_sql_list[mark] = sql_list

mark = 'SPV1'
sql_list = []
for table in table_list:
    for field in table_fields[table]:
        if(field != 'aID'):
            sql_list.append(f"select {field} from {table}")
            
mark_sql_list[mark] = sql_list
mark = 'SPV2'
sql_list = []
for table in table_list:
    for field in table_fields[table]:
        if(field != 'aID'):
            sql_list.append(f"select distinct {field} from {table}")
mark_sql_list[mark] = sql_list

mark = 'SAV1'
sql_list = [
    'select count(*) from walmart',
    'select max(latitude) from walmart',
    'select min(latitude) from walmart',
    'select avg(latitude) from walmart',
    ]
mark_sql_list[mark] = sql_list

mark = 'SAV2'
sql_list = [
    'select latitude from walmart',
    ]
mark_sql_list[mark] = sql_list


mark = 'ID1'
sql_list = [
    'select latitude,longitude from walmart',
    'select latitude,longitude from walmart',
    'select zip_code from walmart where zip_code <= 29574',
    ]
mark_sql_list[mark] = sql_list

mark = 'ID2'
sql_list = [
    'select latitude,longitude, zip_code from walmart',
    'select latitude,longitude, city from walmart',
    'select zip_code, state from walmart where zip_code <= 29574',
    ]
mark_sql_list[mark] = sql_list




