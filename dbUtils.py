import pymysql
from dbSettings import *
from collections import defaultdict


def connect(host = host, user=user, password=password, database=database):
    # print(host, user, password, database)
    conn = pymysql.connect(host = host, user=user, passwd=password, database=database)
    return conn



def select(sql, host = host, user=user, password=password, database=database):
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
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
def get_pre_fields_of_all_tables(host = host, user=user, password=password, database=database):
    table_list = []
    original_fields = {}
    primary_fields = defaultdict(list)
    primary_domains = defaultdict(list)
    table_size_list = {}
    conn = connect(host, user, password, database)
    cursor = conn.cursor()
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
                    if(row[3] == 'PRI'):
                        primary_fields[table].append(row[0])
                        query = f"SELECT max({row[0]}), min({row[0]}) FROM {database}.{table}"
                        # print(query)
                        cursor.execute(query)
                        tmp_rs = cursor.fetchall()
                        max_v = tmp_rs[0][0]
                        min_v = tmp_rs[0][1]
                        primary_domains[f"{table}.{row[0]}"].append(min_v)
                        primary_domains[f"{table}.{row[0]}"].append(max_v)
    cursor.close()
    conn.close()
    return table_list, table_size_list, original_fields,primary_fields,primary_domains
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


