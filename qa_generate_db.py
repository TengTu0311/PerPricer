from dbUtils import *
import random
import string
import json
import pandas as pd
from sqlalchemy import create_engine
import numpy as np

# table_list, table_size_list, table_fields = get_fields_of_all_tables(database=db)
db = 'walmart'
s_size = 1000 
# Create a database engine
engine = create_engine(f'mysql+pymysql://{user}:{password}@localhost/{db}')
table_list, table_size_list, table_fields, primary_fields,primary_domains = get_pre_fields_of_all_tables(database=db)

num_list = {}
data_size = 0
for table in table_list:
    data_size += table_size_list[table]
ratio = s_size/data_size
sql_index_list = []
for table in table_list:
    num = int(table_size_list[table] * ratio)
    num_list[table] = num
    # Write the SQL query
    query = f"SELECT * FROM {table}" 

    # Read the data into a DataFrame
    df = pd.read_sql_query(query, engine)
    support_name = table + "_qa_support"
    support_sets = []
    support_set_list = []
    table_size = df.shape[0]
    column_num = df.shape[1]

    for i in range(num):
        j = random.randint(0, table_size - 1)
        data = df.iloc[j]
        p1 = random.uniform(0, 1)
        if(p1 <= 0.5): # generate N1 neighborhodd
            while(True):
                k = random.randint(0, column_num - 2) + 1
                series = df.iloc[:, k]
                new_v = np.random.choice(series.dropna().drop_duplicates().tolist())
                if(new_v != data[k]):
                    break
            support_set_list.append([df.columns[k], j + 1, j + 1])
            insert_data = list(data) + [i]
            # support_sets.append(insert_data) 
            insert_data[k] = new_v
            support_sets.append(insert_data) 
        else:
            while(True):
                j2 = random.randint(0, table_size - 1)
                n_data = df.iloc[j2]
                k = random.randint(0, column_num - 2) + 1 # ignore the first aID column
                v = data[k]
                new_v = n_data[k]
                if(new_v != v):
                    break
            if(j < j2):
                support_set_list.append([df.columns[k], j + 1, j2 + 1])
                insert_data = list(data) + [i]
                insert_data[k] = new_v
                support_sets.append(insert_data) 
                insert_data = list(n_data) + [i]
                insert_data[k] = v
                support_sets.append(insert_data) 
            else:
                support_set_list.append([df.columns[k], j2 + 1, j + 1])
                insert_data = list(n_data) + [i]
                insert_data[k] = v
                support_sets.append(insert_data) 
                insert_data = list(data) + [i]
                insert_data[k] = new_v
                support_sets.append(insert_data) 
    primary_str = ",".join(primary_fields[table])
    if primary_str:
        sql = f"ALTER TABLE {support_name} ADD PRIMARY KEY ({primary_str});"
        sql_index_list.append(sql)
    # write support set to the file
    print("Start writing")
    file_name = db +"_" + support_name + ".json"
    with open(file_name, 'w') as file:
        json.dump(support_set_list, file)

    # print(df.columns, len(df.columns), len(support_sets[0]))
    column_name = list(df.columns)
    column_name.append('sID')

    new_df = pd.DataFrame(support_sets, columns= column_name)
    new_df.to_sql(name=support_name, con=engine, index=False, if_exists='replace')

conn = pymysql.connect(host = host, user=user, passwd=password, database=db)
cursor = conn.cursor()
sql = f"use {db}"

#for sql in sql_index_list:
#    print(sql)
for sql in sql_index_list:
    cursor.execute(sql)
cursor.close()
print("Complete")


