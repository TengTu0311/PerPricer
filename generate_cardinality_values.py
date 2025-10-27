import csv
import pandas as pd
from abUtils import *
from QAPricer import QAPricer
from PVPricer import PVPricer
import random
# generate N values that are not in the database db and the corresponding queries


value_list = read_value_list_from_csv('./test_values/checked_values.csv')
pricer_list = initialize_pricer()


# record the prices for all values 
pre_rs = []
# calculate the price of each query in the list
for i, value in enumerate(value_list):
    query = value[-1]
    # compute the cardinality of the query 
    cardinality = get_cardinality(query)
    # compute the query price under PVPricer
    p1 = pricer_list[0].price_SQL_query(query)
    # compute the query price under QAPricer
    p2 = pricer_list[1].price_SQL_query(query)
    # compute the price of having clause under QAPricer
    pre_rs.append([i, p1, p2])


# write the list value_list[N][table_name, field_name, value] into the csv file 

import csv

def write_values_to_csv(value_list, file_path, head):
    # Open the CSV file in write mode
    with open(file_path, 'w', newline='') as csvfile:
        # Create a CSV writer object
        writer = csv.writer(csvfile)
        
        # Write the header row
        writer.writerow(head)
        
        # Write the values
        for value in value_list:
            writer.writerow(value)

head = ['Table Name', 'Field Name', 'Value', 'Query']
write_values_to_csv(value_list, './test_values/checked_values.csv', head)
head = ['Table Name', 'Field1 Name', 'Value1', 'Field2 Name', 'Value2', 'Query']
write_values_to_csv(non_value_list, './test_values/non_checked_values.csv', head)

# generate the price of each query in the list
df = pd.DataFrame(pre_rs, columns=['ID', 'Price of PVPricer', 'Price of QAPricer'])
df.to_csv('./attack_pre_rs/membership_query_prices.csv', index=False)

