import mysql.connector
from dbSettings import *


# def select(sql, host = host, user=user, password=password, database=database):
#     cnx = mysql.connector.connect(
#         host = host,
#         user = user,
#         password= password,
#         database= database
#     )
#     # cursor = cnx.cursor()
#     cursor = cnx.cursor(buffered=True)
#     cursor.execute(sql)
#     results = cursor.fetchall()
#     cursor.close()
#     cnx.close()
#     return results
    




def connect(host = host, user=user, password=password, database=database):
    # print(host, user, password, database)
    conn = mysql.connector.connect(host = host, user=user, passwd=password, database=database)
    return conn



def select(sql, host = host, user=user, password=password, database=database):
    conn = connect(host, user, password, database)
    cursor = conn.cursor(buffered=True)
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result
    

def insert(sql, host = host, user=user, password=password, database=database):
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    
def insert_value(sql, value, host = host, user=user, password=password, database=database):
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
    cursor.execute(sql, value)
    conn.commit()
    cursor.close()
    conn.close()
def insert_many(sql, values, host = host, user=user, password=password, database=database):
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
    cursor.executemany(sql, values)
    conn.commit()
    cursor.close()
    conn.close()


def get_size_of_support_size(support_suffix, host = host, user=user, password=password, database=database):
    table_size_list = {}
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
    sql = f"use {database}"
    cursor.execute(sql)
    sql = "show tables"
    cursor.execute(sql)
    tables = cursor.fetchall()
    for table in tables:
        table = str(table[0])
        if("_all" not in table and support_suffix in table):
            query = f"SELECT count(*) FROM {database}.{table}"
            # print(query)
            cursor.execute(query)
            table = table.split(support_suffix)[0]
            table_size_list[table] = cursor.fetchall()[0][0]
    cursor.close()
    conn.close()
    return table_size_list 
def get_fields_of_all_tables(host = host, user=user, password=password, database=database):
    table_list = []
    original_fields = {}
    table_size_list = {}
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
    sql = f"use {database}"
    cursor.execute(sql)
    sql = "show tables"
    cursor.execute(sql)
    tables = cursor.fetchall()
    for table in tables:
        table = str(table[0])
        if(table.islower() and "_support" not in table):
            table_list.append(table)
            original_fields[table] = []
            query = f"SELECT count(*) FROM {database}.{table}"
            # print(query)
            cursor.execute(query)
            table_size_list[table] = cursor.fetchall()[0][0]
            sql = f"desc {database}.{table}"
            cursor.execute(sql)
            result = cursor.fetchall()
            for row in result:
                if(row[0] != 'aID' and row[0] != 'sID'):
                    original_fields[table].append(row[0])
    cursor.close()
    conn.close()
    return table_list, table_size_list, original_fields
def get_field_from_table(table, host = host, user=user, password=password, database=database):
    original_fields = []
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
    query = f"SELECT count(*) FROM {database}.{table}"
    cursor.execute(query)
    table_size = cursor.fetchall()[0][0]
    sql = f"desc {database}.{table}"
    cursor.execute(sql)
    result = cursor.fetchall()
    for row in result:
        if(row[0] != 'aID' and row[0] != 'sID'):
            original_fields.append(row[0])
    cursor.close()
    conn.close()
    return table_size, original_fields


def get_field_domains_from_table(table, host = host, user=user, password=password, database=database):
    primary_fields = []
    original_fields = []
    field_domain = []
    field_domain_count = []
    primary_fields_idx = []
    original_fields_idx = []
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
    query = f"SELECT count(*) FROM {database}.{table}"
    cursor.execute(query)
    table_size = cursor.fetchall()[0][0]
    sql = f"desc {database}.{table}"
    cursor.execute(sql)
    result = cursor.fetchall()
    i = 0
    for row in result:
        if(row[3] == 'PRI'):
            primary_fields.append(row[0])
            primary_fields_idx.append(i)
        else:
            original_fields.append(row[0])
            query = f"SELECT DISTINCT {row[0]} FROM {database}.{table}"
            cursor.execute(query)
            field_domain_temp = cursor.fetchall()
            field_domain.append([field[0] for field in field_domain_temp])
            field_domain_count.append(len(field_domain_temp))
            original_fields_idx.append(i)
        i += 1
    cursor.close()
    conn.close()

    return table_size, primary_fields, primary_fields_idx, original_fields, original_fields_idx, field_domain, field_domain_count


if __name__ == "__main__":
    table_list, table_size_list, fields = get_fields_of_all_tables(database="qa_tpch1g")
    print(table_list)
    print(table_size_list)
    print(fields)
    query1 = 'select o_orderkey, o_orderpriority, l_commitdate, l_receiptdate from orders, lineitem where 	o_orderdate >= date \'1993-07-01\' 	and o_orderdate < date \'1993-07-01\' + interval \'3\' month 	and l_orderkey = o_orderkey 	and l_commitdate < l_receiptdate; '
    rs = select(query1)
    print(len(rs))
    query1 = 'select o_orderkey, o_orderpriority, l_commitdate, l_receiptdate from orders, lineitem where   o_orderdate >= date \'1993-07-01\'   and o_orderdate < date \'1993-07-01\' + interval \'3\' month   and l_orderkey = o_orderkey   and l_commitdate < l_receiptdate; ' 
    query2 = 'select  l_orderkey, o_orderkey,c_custkey,o_custkey, l_suppkey, s_suppkey,c_nationkey, n_nationkey,s_nationkey, n_regionkey, r_regionkey from   customer,   orders,   lineitem,   supplier,   nation,   region where   c_custkey = o_custkey   and l_orderkey = o_orderkey   and l_suppkey = s_suppkey   and c_nationkey = s_nationkey   and s_nationkey = n_nationkey   and n_regionkey = r_regionkey   and r_name = \'ASIA\'   and o_orderdate >= date \'1994-01-01\'   and o_orderdate < date \'1994-01-01\' + interval \'1\' year' 
    query3 = 'select  l_shipdate  from   lineitem where   l_shipdate >= date \'1994-01-01\'   and l_shipdate < date \'1994-01-01\' + interval \'1\' year   and l_discount between 0.05 and 0.07   and l_quantity < 24; ' 
    query4 = 'select o_orderkey,l_orderkey, l_shipmode,o_orderpriority   from   orders,   lineitem where   o_orderkey = l_orderkey   and (l_shipmode = \'MAIL\' or l_shipmode = \'SHIP\')   and l_commitdate < l_receiptdate   and l_shipdate < l_commitdate   and l_receiptdate >= date \'1994-01-01\'   and l_receiptdate < date \'1994-01-01\' + interval \'1\' year' 
    query5 = 'select   ps_partkey, p_partkey, p_type from   partsupp,   part where   p_partkey = ps_partkey   and p_brand <> \'Brand#45\'   and p_type not like \'MEDIUM POLISHED%\'   and p_size in (49, 14, 23, 45, 19, 3, 36, 9)' 
    query6 = 'select  l_partkey, p_partkey from   lineitem,   part where   p_partkey = l_partkey   and p_brand = \'Brand#23\'   and p_container = \'MED BOX\'   and l_quantity < 5.10736 ' 
    query7 = 'select l_shipdate  from   lineitem where   l_shipdate <= date \'1998-09-01\'' 
    query8 = 'select p_partkey,ps_partkey,s_suppkey,ps_suppkey,s_nationkey,n_nationkey,r_regionkey,s_acctbal,s_name,n_name   from   part,   supplier,   partsupp,   nation,   region where   p_partkey = ps_partkey   and s_suppkey = ps_suppkey   and p_size = 15   and p_type like \'%BRASS\'   and s_nationkey = n_nationkey   and n_regionkey = r_regionkey   and r_name = \'EUROPE\'   and ps_supplycost = 100 limit 100; ' 

    # sql_list = [query1, query2, query3, query4, query5, query6, query7, query8]
    sql_list = [query7]
    import time
    for i, sql in enumerate(sql_list):
        start_time = time.time()
        rs = select(sql)
        end_time = time.time()
        print(i, len(rs), end_time - start_time)

