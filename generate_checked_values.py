import string
import pandas as pd
from abUtils import *
import random
from Utils import *
from PVPricer import load_pre_query_results as load_pre_query_results_PV
from PVPricer import parse_sql_statements
from QAPricer import load_pre_query_results as load_pre_query_results_QA
# generate N values that are not in the database db and the corresponding queries
def generate_non_db_values(N, table_list, table_size_list, fields):
    value_list = []
    # randomly choose N values
    for i in range(N):
        value_list = []
    # randomly choose N values
    while len(value_list) < N:
        table, f1, v1 = get_one_in_value(table_list, table_size_list, fields)
        table, f2, v2 = get_one_in_value(table_list, table_size_list, fields)
        if v1 != '-' and v1 != '' and v2 != '' and v2 != '-':
            query = f"select * from {table} where {f1} = '{v1}' and {f2} = '{v2}'"
            rs = select(query)
            if len(rs) == 0:
                value_list.append([table, f1, v1, f2, v2, len(rs), table_size_list[table], query])
    return value_list


def generate_in_db_values(N, table_list, table_size_list, fields):
    value_list = []
    # randomly choose N values
    while len(value_list) < N:
        table, field, value = get_one_in_value(table_list, table_size_list, fields)
        if value != '-' and value != '':
            query = f"select * from {table} where {field} = '{value}'"
            rs = select(query)
            value_list.append([table, field, value, len(rs), table_size_list[table],query])
    return value_list

def get_one_in_value(table_list, table_size_list, fields, table = None):
    # randomly choose one table or choose the specified table
    if table != None:
        table = table
    else:
        table = random.choice(table_list)
    # get the number of rows in the table
    table_size = table_size_list[table]
    # randomly choose one field
    field = random.choice(fields[table])
    # randomly choose the j-th tuple in the table
    j = random.randint(0, table_size - 1)
    # get the value from the table
    value = get_field_value(table, field, j)
    return [table, field, value]

def extract_strings(lst):
    result = []
    idx = []
    for i, s in enumerate(lst):
        if 'key' in s:
            parts = s.split('_')
            if len(parts) > 1:
                result.append(parts[1])
                idx.append(i)
    return result, idx

def generate_three_queries(a, b, c, t1, t2, f1, f2, joined_keys):
    q1 = f"select * from {t1} where {t1}.{f1} = '{a}' and {t1}.{joined_keys[0]} = '{b}'"
    q2 = f"select * from {t2} where {t2}.{joined_keys[1]} = '{b}' and {t2}.{f2} = '{c}'"
    q3 = f"select * from {t1}, {t2} where {t1}.{joined_keys[0]} = {t2}.{joined_keys[1]} and {t2}.{joined_keys[1]} = '{b}' and {t1}.{f1} == '{a}' and {t2}.{f2} == '{c}'"
    return q1, q2, q3
# def generate_value_from_join_table(table_list, N, fields):
#     # randomly find two jointable tables
#     flag = True
#     joined_keys = []
#     while flag:
#         t1 = random.choice(table_list)
#         t2 = random.choice(table_list)
#         if t1 == t2:
#             continue 
#         f1, idx_1 = extract_strings(fields[t1])
#         f2, idx_2 = extract_strings(fields[t2])
#         for i, s in enumerate(f1):
#             j = f2.index(s)
#             if j != -1:
#                 joined_keys.append(fields[t1][idx_1[i]], fields[t2][idx_2[j]])
#                 break
#     f1 = random.choice(fields[t1])
#     f2 = random.choice(fields[t2])
#     query = f"select distinct {t1}.{f1}, {t2}.{f2}, {t2}.{joined_keys[1]} from {t1}, {t2} where {t1}.{joined_keys[0]} = {t2}.{joined_keys[1]} limit {N}"
#     rs = select(query)
#     value_list = []
#     for i, row in enumerate(rs):
#         a, b, c = row[0], row[1], row[2]
#         q1, q2, q3 = generate_three_queries(a, b, c, t1, t2, f1, f2, joined_keys)
#         value_list.append([a,b,c,q1,q2,q3,1,1])
#         if isinstance(a, (int, float)):
#             a0 = a + random.randint(-100, 100)
#         else:
#             a0 = a + str(random.randint(-100, 100))
#         q1, q2, q3 = generate_three_queries(a0, b, c, t1, t2, f1, f2, joined_keys)
#         value_list.append([a0,b,c,q1,q2,q3,0,1])
#         if isinstance(c, (int, float)):
#             c0 = c + random.randint(-100, 100)
#         else:
#             c0 = c + str(random.randint(-100, 100))
#         q1, q2, q3 = generate_three_queries(a, b, c0, t1, t2, f1, f2, joined_keys)
#         value_list.append([a, b, c0, q1, q2, q3, 1, 0])
#         q1, q2, q3 = generate_three_queries(a0, b, c0, t1, t2, f1, f2, joined_keys)
#         value_list.append([a0, b, c0, q1, q2, q3, 0, 0])
#     price_list = defaultdict(list)
#     pricer_list = initialize_pricer()
    
def generate_value_from_two_table(table_list, N, fields):
    t1 = 'customer'
    t2 = 'lineorder'
    # randomly find two jointable tables
    flag = True
    joined_keys = ['c_custkey', 'lo_custkey']
    f1 = 'c_address'
    f2 = 'lo_discount'
    query = f"select {t1}.{f1}, {t2}.{f2}, {t2}.{joined_keys[1]} from {t1}, {t2} where {t1}.{joined_keys[0]} = {t2}.{joined_keys[1]} limit {N}"
    rs = select(query)
    value_list = []
    for i, row in enumerate(rs):
        a, b, c = row[0], row[1], row[2]
        q1, q2, q3 = generate_three_queries(a, b, c, t1, t2, f1, f2, joined_keys)
        value_list.append([a,b,c,q1,q2,q3,1,1])
        if isinstance(a, (int, float)):
            a0 = a + random.randint(-100, 100)
        else:
            a0 = a + str(random.randint(-100, 100))
        q1, q2, q3 = generate_three_queries(a0, b, c, t1, t2, f1, f2, joined_keys)
        value_list.append([a0,b,c,q1,q2,q3,0,1])
        if isinstance(c, (int, float)):
            c0 = c + random.randint(-100, 100)
        else:
            c0 = c + str(random.randint(-100, 100))
        q1, q2, q3 = generate_three_queries(a, b, c0, t1, t2, f1, f2, joined_keys)
        value_list.append([a, b, c0, q1, q2, q3, 1, 0])
        q1, q2, q3 = generate_three_queries(a0, b, c0, t1, t2, f1, f2, joined_keys)
        value_list.append([a0, b, c0, q1, q2, q3, 0, 0])
    price_list = defaultdict(list)
    pricer_list = initialize_pricer()
    
        
def get_field_value(table, field, j):
    query = f"select {field} from {table} limit {j}, 1"
    return select(query)[0][0]

def write_strings_to_file(strings, filename):
    try:
        # Open the file in 'w' mode to write
        with open(filename, 'w') as file:
            # Iterate through the list of strings
            for string in strings:
                # Write each string to the file
                file.write(string + '\n')  # Add a newline after each string
        print("Strings have been written to", filename)
    except IOError:
        print("Error: Unable to write to the file", filename)

def check(v1, v2 = -1):
    flag = True
    if isinstance(v1, str) and ("'" in v1 or '"' in v1 or ";" in v1):
        flag = False 
    if isinstance(v2, str) and ("'" in v2 or '"' in v2 or ";" in v2):
        flag = False
    return flag


def price_value_query(N):
    value_list = read_value_list_from_csv(f'./test_values/checked_values_{N}.csv')
    pricer_list = initialize_pricer()
    mark = 'S'
    db = database
    pre_rs = []
    cardinality_list = []
    for i in range(N):
        c = 0
        for pricer in pricer_list:
            sql = value_list[i][-1]
            if isinstance(pricer, PVPricer):
                o_results = load_pre_query_results_PV(sql, mark, i, db, 'attack_pre_rs')
                c = len(o_results)
                query_tables = parse_sql_statements(sql)
                is_distinct = "distinct" in sql
                p1 = pricer.pre_price_SQL_query(is_distinct, o_results, query_tables)
            else:
                all_results, support_rs = load_pre_query_results_QA(sql, mark, i, db, 'attack_pre_rs')
                p2 = pricer.pre_price_SQL_query(sql, all_results, support_rs)
        pre_rs.append([i, p1, p2])
        cardinality_list.append([c])


    df = pd.DataFrame(pre_rs, columns=['ID', 'Price of PVPricer', 'Price of QAPricer'])
    df.to_csv('./attack_pre_rs/membership_query_prices.csv', index=False)
    v = pd.DataFrame(value_list, columns=['Table Name', 'Field1 Name', 'Value1', 'Max cardinality', 'Query'])
    c = pd.DataFrame(cardinality_list)
    v.insert(3, 'Cardinality', c)
    v.to_csv(f'./test_values/checked_values_{N}.csv', index=False)
    # write_values_to_csv(v, f'./test_values/checked_values_{N}.csv', v.columns)

def generated_values_on_single_table(N, table_list, table_size_list, fields, table = 'customer'):
    value_list = []
    value_sql_list = []
    q_list = []
    
    for table in [table]:
        f_num = len(fields[table])
        n = int(N // f_num) + 1000
        query = f"select * from {table} limit {n}"
        rs = select(query)
        i = 0 
        ni = 0
        while ni < N:
            for j in range(f_num):
                v = rs[i][j]
                if random.choice([0,1]):
                    if isinstance(v, str):
                        v = "v" + ''.join(random.choices(string.ascii_letters, k=6))
                    else:
                        v = v + random.randint(-100, 100)
                if check(v):
                    value_list.append([table, fields[table][j], v, table_size_list[table], f"select * from {table} where {fields[table][j]} = '{v}'"])
                    q_list.append(value_list[-1][-1] + ";")
                    ni += 1
                    if ni == N:
                        break 
            i += 1
    value_sql_list.extend(q_list)
    # for table in table_list:
    #     n = int(N *(table_size_list[table] / total_table_size))
    #     print(table, n, table_size_list[table])
    #     if n == 0:
    #         continue
        # query = f"select * from {table} limit {n}"
        # rs = select(query)
        # for i in range(n):
        #     strategy = random.choice([0, 1])
        #     if strategy:
        #         while True:
        #             j = random.randint(1, len(fields[table]) -1)
        #             if check(v):
        #                 break
        #         value_list.append([table, fields[table][j], v, fields[table][j], v, table_size_list[table], f"select * from {table} where {fields[table][j]} = '{v}'"])
        #         q_list.append(value_list[-1][-1] + ";")
        #     else:
        #         while True:
        #             i1, i2 = random.randint(1, len(fields[table]) -1), random.randint(1, len(fields[table]) -1)
        #             if i < n - 1:
        #                 v1, v2 = rs[i][i1], rs[i+1][i2]
        #             else:
        #                 v1, v2 = rs[i][i1], rs[0][i2]
        #             flag = check(v1, v2)
        #             if flag:
        #                 break
        #         f1, f2 = fields[table][i1], fields[table][i2]
        #         q = f'select * from {table} where {fields[table][i1]} = "{v1}" and {fields[table][i2]} = "{v2}"'
        #         value_list.append([table, f1, v1, f2, v2, table_size_list[table], q])
        #         q_list.append(q + ";")
        # value_sql_list.extend(q_list)
   
    # head = ['Table Name', 'Field1 Name', 'Value1', 'Field2 Name', 'Value2', 'Max cardinality', 'Query']
    head = ['Table Name', 'Field1 Name', 'Value1', 'Max cardinality', 'Query']
    write_values_to_csv(value_list, f'./test_values/checked_values_{N}.csv', head)
    # print(q_list[:10])
    # obtain the pre sql for each query in the value_sql_list
    pricer_list = initialize_pricer()
    for pricer in pricer_list:
        all_pre_sqls = []
        all_pre_sqls.append(f"use {database};")
        new_sql_list = pricer.print_required_query(value_sql_list, mark = 'S')
        for l in new_sql_list:
            if(isinstance(pricer, PVPricer)):
                all_pre_sqls.append(l)
            else:
                for s in l:
                    all_pre_sqls.append(s)
        file_name = f"./attack_pre_sql/{database}-all-{pricer.__class__.__name__}-single-table-{N}.txt"  
        write_strings_to_file(all_pre_sqls, file_name)  
    

if __name__ == "__main__":
    N = 10000
    # N= 1000， 000
    table_list, table_size_list, fields = get_fields_of_all_tables()
    total_table_size = sum(table_size_list.values())
    print(total_table_size)
    generated_values_on_single_table(N, table_list, table_size_list, fields, 'customer')
    price_value_query(N)

