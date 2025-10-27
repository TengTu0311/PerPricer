from dbUtils import *
import csv
from QAPricer import QAPricer
from PVPricer import PVPricer

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

def read_value_list_from_csv(file_path):
    value_list = []
    # Open the CSV file in read mode
    with open(file_path, 'r') as csvfile:
        # Create a CSV reader object
        reader = csv.reader(csvfile)
        # Skip the header row
        next(reader)
        # Read the values
        for row in reader:
            value_list.append(tuple(row))
    return value_list

def initialize_pricer():
    db = database
    table_list, table_size_list, table_fields = get_fields_of_all_tables(database=db)
    tuple_price = 1
    table_price_list = {}
    support_suffix = "_qa_support"
    history_aware = False
    history = {}
    for table in table_list:
        history[table] = []
        table_price_list[table] = table_size_list[table] * tuple_price
    qa = QAPricer(db, table_list, table_fields, history, table_price_list, table_size_list, support_suffix, history_aware)
    tuple_price_list = defaultdict(int)
    for table in table_list:
        tuple_price_list[table] = 1
    pv = PVPricer(db, table_size_list, tuple_price_list, table_fields)
    pricer_list = [pv, qa]
    return pricer_list

def get_cardinality(query):
    # compute the cardinality of the query
    rs = select(query) 
    return len(rs)