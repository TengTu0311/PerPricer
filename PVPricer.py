
from test_queries import *
from pandas.errors import EmptyDataError
def load_pre_query_results(sql, mark, i, db):
    try:
        df = pd.read_csv(f'pre_rs/{db}-{mark}-{i}-PVPricer-o.txt', header=None, na_values=['\\N'])
        # all_results = df.values
        all_results = list(df.itertuples(index=False, name=None))
    except EmptyDataError:
        print(f"No columns to parse from file pre_rs/{db}-{mark}-{i}-PVPricer-o.txt")
        all_results = []
    
    return all_results
def parse_sql_statements(sql_statement : str):

    if 'where' in sql_statement:
        rule_projections = r'from(.*?)where'
    elif("group" in sql_statement):
        rule_projections = r'from(.*?)group'
    elif("limit" in sql_statement):
        rule_projections = r'from(.*?)limit'
    else:
        rule_projections = r'(?<=from).*$'
    table_list = re.findall(rule_projections, sql_statement)
    # print('11',table_list,sql_statement)
    table_list = table_list[0].replace(' ','').split(',') 
    if 'distinct' in sql_statement:
        rule_selections = r'distinct(.*?)from'
    else:
        rule_selections = r'select(.*?)from'
    # attributes = re.findall(rule_selections, sql_statement)
    # attributes = attributes[0].replace(' ','').split(',')
    # # for att in attributes: # to process the aggregate keywords

    # # Extract the attributes from the parsed statement
    return table_list
class lineage:
    def __init__(self, table_num, lineage_set, is_copy = True):
        self.table_num = table_num
        self.lineage = [set() for i in range(table_num)]
        if(len(lineage_set) != 0 and is_copy):
            for i in range(table_num):
                self.lineage[i] = lineage_set[i].copy()
        if(len(lineage_set) != 0 and not is_copy):
            for i in range(table_num):
                self.lineage[i] = lineage_set[i]
    def add(self, tuple_lineage_set):
        for i in range(self.table_num):
            self.lineage[i].add(tuple_lineage_set[i])
    

    def final(self):
        for i in range(self.table_num):
            self.lineage[i] = set(self.lineage[i])

    def get_price(self, table_price_list):
        # self.final()
        price = 0
        for i in range(self.table_num):
            price += len(self.lineage[i]) * table_price_list[i]
        return price

class PVPricer:
    def __init__(self, db, table_size_list, tuple_price_list, table_fields):
        self.db = db
        self.table_size_list = table_size_list
        self.tuple_price_list = tuple_price_list
        self.table_fields = table_fields




    
    
    def __price_distinct_query__(self, sql):
        sql = sql.replace("distinct", "")
        query_tables = parse_sql_statements(sql)

        if("*" in sql):
            place_str = ""
            str_list = []
            for table in query_tables:
                # print(table)
                for s in self.table_fields[table]:
                    str_list.append(table+"."+ s)
            place_str = ",".join(str_list)
            sql = sql.replace("*", place_str)
        
        str1 = sql.split("select")[1]
        selected_attributes = [table + ".aID" for table in query_tables]
        str2 = ",".join(selected_attributes)
        new_sql = "select " + str2 + ", " + str1
        # print(new_sql)
        table_num = len(query_tables)
        o_results = select(new_sql, database= self.db)
        o_results = np.array(o_results)
        # get the lineage set of each query result
        tuple_lineage_set = defaultdict(list)
        for item in o_results:
            aID_list = item[:table_num]
            tuple_lineage_set[tuple(item[table_num:])].append(aID_list)
        
        # compute the lineage sets of all query results
        all_possible_lineage_sets = []
        last_lineage_sets = [lineage(table_num, [])]
        for item in tuple_lineage_set.keys(): # one query result
            all_possible_lineage_sets =  []
            for ss in last_lineage_sets: # the lineage sets of the previous query results
                for tuple_lineage in tuple_lineage_set[item]:
                    new_ss = lineage(table_num, ss.lineage)
                    new_ss.add(tuple_lineage)
                    all_possible_lineage_sets.append(new_ss)
            last_lineage_sets = all_possible_lineage_sets
        
        table_price_list = []
        for i in range(table_num):
            table_price_list.append(self.tuple_price_list[query_tables[i]])
        price = -1
        for lineage_set in last_lineage_sets:
            one_price = lineage_set.get_price(table_price_list)
            if(price > 0):
                price = min(price, one_price)
            else:
                price = one_price
        return price
        

    def __price_normal_query__(self, sql): # limit query, * query
        query_tables = parse_sql_statements(sql)
        
        selected_attributes = [table + ".aID" for table in query_tables]
        str2 = ",".join(selected_attributes)
        if("*" in sql):
            str1 = sql.split("*")[1]
            new_sql = "select " + str2 + " " + str1
        else:
            str1 = sql.split("from")[1]
            new_sql = "select " + str2 + " from " + str1
        # print(new_sql)
        table_num = len(query_tables)
        o_results = select(new_sql, database= self.db)
        o_results = np.array(o_results)
        # get the lineage set of each query result
        tuple_lineage_set = defaultdict(list)
        for i, item in enumerate(o_results):
            aID_list = item[:table_num]
            tuple_lineage_set[i].append(aID_list)
        
        # compute the lineage sets of all query results
        all_possible_lineage_sets = []
        last_lineage_sets = [lineage(table_num, [])]
        for item in tuple_lineage_set.keys(): # one query result
            all_possible_lineage_sets =  []
            for ss in last_lineage_sets: # the lineage sets of the previous query results
                for tuple_lineage in tuple_lineage_set[item]:
                    new_ss = lineage(table_num, ss.lineage, False)
                    new_ss.add(tuple_lineage)
                    all_possible_lineage_sets.append(new_ss)
            last_lineage_sets = all_possible_lineage_sets
        
        table_price_list = []
        for i in range(table_num):
            table_price_list.append(self.tuple_price_list[query_tables[i]])
        price = -1
        for lineage_set in last_lineage_sets:
            one_price = lineage_set.get_price(table_price_list)
            if(price > 0):
                price = min(price, one_price)
            else:
                price = one_price
        return price  

    

                
 
    def print_required_query(self, sql_list, mark):
        new_sql_list = []
        # current_directory = os.getcwd()
        current_directory =  '/var/lib/mysql-files/'
        for i, sql in enumerate(sql_list):
            # print(i, sql)
            sql = sql.split(";")[0]
            sql  = sql + " "
            new_sql = ""
            if("distinct" in sql):
                md = QueryMetaData(sql)
                # print(md)
                query_tables = md.tables
                sql = sql.replace("distinct", "")
                if("*" in sql):
                    place_str = ""
                    str_list = []
                    for table in query_tables:
                        # print(table)
                        for s in self.table_fields[table]:
                            str_list.append(table+"."+ s)
                    place_str = ",".join(str_list)
                    sql = sql.replace("*", place_str)
                
                str1 = sql.split("select")[1]
                selected_attributes = [table + ".aID" for table in query_tables]
                str2 = ",".join(selected_attributes)
                new_sql = "select " + str2 + ", " + str1
            elif("count(" in sql or "max(" in sql or "min(" in sql or "avg(" in sql or "sum(" in sql):
                print("Provenance-based methods do not support aggregate queries!")
            else:
                md = QueryMetaData(sql)
                # print(md)
                query_tables = md.tables
                
                selected_attributes = [table + ".aID" for table in query_tables]
                str2 = ",".join(selected_attributes)
                # print(sql, sql.split("from"))
                str1 = sql.split("from")[1]
                new_sql = "select " + str2 + " from " + str1
            

            outfile_path = current_directory + f'{self.db}-{mark}-{i}-PVPricer-o.txt'
            new_sql = f"{new_sql} INTO OUTFILE '{outfile_path}' FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' LINES TERMINATED BY '\\n';"
            # print(new_sql)
            new_sql_list.append(new_sql)

        return new_sql_list
    def price_SQL_query(self, sql):
        sql = sql.split(";")[0]
        sql  = sql + " "
        if("distinct" in sql):
            price = self.__price_distinct_query__(sql)

        elif("count(" in sql or "max(" in sql or "min(" in sql or "avg(" in sql or "sum(" in sql):
            print("Provenance-based methods do not support aggregate queries!")
            price = -1
        else:
            price = self.__price_normal_query__(sql)
        return price
    

    def pre_price_SQL_query(self, is_distinct, o_results, query_tables):
        # get the lineage set of each query result
        tuple_lineage_set = defaultdict(list)
        table_num = len(query_tables)
        for i, item in enumerate(o_results):
            aID_list = item[:table_num]
            if(is_distinct):
                tuple_lineage_set[tuple(item[table_num:])].append(aID_list)
            else:
                tuple_lineage_set[i].append(aID_list)
        # print(tuple_lineage_set.keys())
        # compute the lineage sets of all query results
        all_possible_lineage_sets = []
        last_lineage_sets = [lineage(table_num, [])]
        for item in tuple_lineage_set.keys(): # one query result
            all_possible_lineage_sets =  []
            for ss in last_lineage_sets: # the lineage sets of the previous query results
                for tuple_lineage in tuple_lineage_set[item]:
                    new_ss = lineage(table_num, ss.lineage, is_distinct)
                    new_ss.add(tuple_lineage)
                    all_possible_lineage_sets.append(new_ss)
            last_lineage_sets = all_possible_lineage_sets
        
        table_price_list = []
        for i in range(table_num):
            table_price_list.append(self.tuple_price_list[query_tables[i]])
        price = -1
        for lineage_set in last_lineage_sets:
            one_price = lineage_set.get_price(table_price_list)
            if(price > 0):
                price = min(price, one_price)
            else:
                price = one_price
        return price  





if __name__ == '__main__':
    pricer= PVPricer(db, table_size_list, tuple_price_list)
    for mark in mark_sql_list.keys():
        # if("A" not in mark):
        if(mark == "SP"):
            sql_list = mark_sql_list[mark]
            print(pricer.print_required_query(sql_list, mark))
            
