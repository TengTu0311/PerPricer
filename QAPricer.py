
# import sqlparse
from test_queries import *
from pandas.errors import EmptyDataError
def replace_count(match):
    return match.group(1) 



def load_query(table, db, type):
    file_name = db + "_" + table + "_"+ type + ".json"
    with open(file_name, 'r') as file:
        query = json.load(file)
    # print(query)
    return query
def load_support_set(table_list, db, support_suffix):
    support_sets = {}
    for table in table_list:
        file_name = db + "_" + table + support_suffix + ".json"
        with open(file_name, 'r') as file:
            loaded_dict = json.load(file)
        support_sets[table] = loaded_dict
    return support_sets
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
    # print('11',table_list)
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

def load_pre_query_results(sql, mark, i, db):
    try:
        df = pd.read_csv(f'pre_rs/{db}-{mark}-{i}-QAPricer-o.txt', header=None, na_values=['\\N'])
        all_results = list(df.itertuples(index=False, name=None))
    except EmptyDataError:
        print(f"No columns to parse from file pre_rs/{db}-{mark}-{i}-QAPricer-o.txt")
        all_results = []
    table_list = parse_sql_statements(sql)
    support_rs = []
    for ii in range(len(table_list)):
        try:
            df = pd.read_csv(f'pre_rs/{db}-{mark}-{i}-QAPricer-{ii}.txt', header=None, na_values=['\\N'])
            tmp_v = list(df.itertuples(index=False, name=None))
        except EmptyDataError:
            print(f"No columns to parse from file pre_rs/{db}-{mark}-{i}-QAPricer-{ii}.txt")
            tmp_v = []
        
        # support_rs.append(df.values)
        support_rs.append(tmp_v)
    return all_results, support_rs


class QAPricer:
    def __init__(self, db, table_list, table_fields, history, table_price_list, table_size_list, support_suffix, history_aware):
        support_sets = load_support_set(table_list, db, support_suffix)
        self.db = db
        self.table_fields = table_fields
        self.price_coeff = {}
        for table in table_list:
            if(len(support_sets[table]) != 0):
                self.price_coeff[table] = table_price_list[table]/len(support_sets[table])
            else:
                self.price_coeff[table] = 0
        self.price_history = history
        self.table_size = table_size_list
        self.support_sets = support_sets
        self.history_aware = history_aware 
        self.support_suffix = support_suffix
        


    def price_SPJ_query(self, sql):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        id_select = ".aID, ".join(query_tables) + ".aID, "
        tmp_sql = sql.replace("select",  "select " + id_select)
        # print(tmp_sql)
        all_results = select(tmp_sql, database=self.db)
        table_num = len(query_tables)

        all_results_groups = defaultdict(list)
        for item in all_results:
            tmp_data = item[table_num:]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
        for ii, table in enumerate(query_tables):
            support_set = self.support_sets[table]
            removed_num = 0
            price_cof = self.price_coeff[table]
            # new_sql = sql.replace(table, table+ "_support")
            new_sql = sql.replace(table + " ", table + self.support_suffix + " ")
            new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
            new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
            new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
            # print(table, new_sql)
            new_rs = select(new_sql, database=self.db)
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)
            support_num = len(support_set)
            for sid in range(support_num):
                # if(sid == 10):
                #     print("111")
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute is selected
                        if(support[0] in selected_attributes[table]):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    # N2 neighbor hood
                    cnt = cn1 = cn2 = 0
                    r1 = []
                    r2 = []
                    s12 = []
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                        cnt = len(s12)
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                        cn1 = len(r1)
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                        cn2 = len(r2)
                    if(cnt != cn1 + cn2):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(cnt == 2 or cnt == 1): # both are results and they are still results after swapped
                        # are outputs same?
                        if(support[0] in selected_attributes[table]):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                            continue
                        else:
                            r12 = r1 + r2
                            if(s12 != r12):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)                           
            price += removed_num * price_cof
        return price

    def tmp_rs_price_limit_query(self, sql):
        # sql = sql.split("limit")[0]
        sql = sql.replace("*", "1")
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table = query_tables[0]
        tmp_sql = sql.replace("select", "select aID,")
        all_results = select(tmp_sql, database=self.db)
        aid_list = [item[0] for item in all_results]
        new_sql = sql.replace(table + " ", table + self.support_suffix + " ")
        new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
        new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
        new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
        # print(table, new_sql)
        new_rs = select(new_sql, database=self.db)
        sid_list = [item[0] for item in new_rs]
        return table, aid_list, sid_list
    def price_limit_varying_K_query(self, aid_list, sid_list, K, table, max_price = -1):
        # sql: select * from table where A = a limit K
        # print(K, len(aid_list), max_price)
        if K >= len(aid_list) + 2 and  max_price != -1:
            return max_price
        if K <= 0:
            return 0
        support_set = self.support_sets[table]
        price = 0
        # print the type of the element in the aid list
        if len(aid_list) > 0 and isinstance(aid_list[0], str): 
            print(aid_list[0])
        for support in support_set:
            sid = support[0]
            aid = support[1]
            bid = support[2]
            f1 = aid in aid_list
            f2 = bid in sid_list
            f3 = sid in sid_list
            g1 = K > len(aid_list) or (K <= len(aid_list) and K >= 1 and aid_list[K - 1] >= aid)  # can aid be in the first K results?
            g2 = K > len(aid_list) or (K <= len(aid_list) and K >= 1 and aid_list[K - 1] >= bid) # can aid be in the first K results?
            if aid == bid:
                # g1 holds, f1 holds, price + 1
                # g1 holds, f1 not holds, f3 holds, price + 1
                # otherwise price + 0
                if (g1 and f1) or (g1 and not f1 and f3):
                    price += 1
            else:
                # g1 or g2 holds, f1 or f2 holds, price + 1
                # g1 or g2 holds, f1 and f2 not holds, f3 holds, price + 1
                if ((g1 or g2) and (f1 or f2)) or ((g1 or g2) and not (f1 and f2) and f3):
                    price += 1
        return price * self.price_coeff[table]

    def price_having_varying_K_query(self, sql):
        # sql: select count(*) from table where A = a having count(*) = K
        # sql = sql.split("having")[0]
        # pattern = r"count\((.*?)\)"
        # replacement = "1"
        # sql = re.sub(pattern, replacement, sql)
        sql = sql.replace("*", "1")
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table = query_tables[0]
        # compute the N_{-1}, N_{-2}, N_{1}, N_{2}
        N_list = [0, 0, 0, 0]
        # start to compute the price of sql and update N_list
        tmp_sql = sql.replace("select", "select aID,")
        all_results = select(tmp_sql, database=self.db)
        aid_list = [item[0] for item in all_results]
        k = len(all_results)
        new_sql = sql.replace(table + " ", table + self.support_suffix + " ")
        new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
        new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
        new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
        # print(table, new_sql)
        new_rs = select(new_sql, database=self.db)
        sid_list = [item[0] for item in new_rs]
        support_set = self.support_sets[table]
        for support in support_set:
            sid = support[0]
            aid = support[1]
            bid = support[2]
            if(aid == bid):
                f1 = aid in aid_list
                f2 = sid in sid_list
                if f1 and not f2:
                    N_list[0] += 1
                elif not f1 and f2:
                    N_list[1] += 1
            else:
                # N2 neighbor hood
                f1 = aid in aid_list
                f2 = bid in aid_list
                f3 = sid in sid_list
                if f1 and f2 and not f3:
                    N_list[2] += 1
                elif not f1 and not f2 and f3:
                    # if sid appears two times in sid_list 
                    if(sid_list.count(sid) == 2):
                        N_list[3] += 1
        price = sum(N_list) * self.price_coeff[table]
        p1 = N_list[0] * self.price_coeff[table]
        p2 = N_list[1] * self.price_coeff[table]
        p3 = N_list[2] * self.price_coeff[table]
        p4 = N_list[3] * self.price_coeff[table]
        return {k-2: p3, k-1: p1, k: price, k +1: p2, k+2: p4}


    def pre_price_SPJ_query(self, sql, all_results, support_rs):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables

        table_num = len(query_tables)

        all_results_groups = defaultdict(list)
        for item in all_results:
            tmp_data = item[table_num:]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
        
        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        for ii, table in enumerate(query_tables):
            support_set = self.support_sets[table]
            support_num = len(support_set)
            removed_num = 0
            price_cof = self.price_coeff[table]
            new_rs = support_rs[ii]
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)
            for sid in range(support_num):
                # if(sid == 10):
                #     print("111")
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute is selected
                        if(support[0] in selected_attributes[table]):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    cnt = cn1 = cn2 = 0
                    r1 = []
                    r2 = []
                    s12 = []
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                        cnt = len(s12)
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                        cn1 = len(r1)
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                        cn2 = len(r2)
                    if(cnt != cn1 + cn2):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(cnt == 2 or cnt == 1): # both are results and they are still results after swapped
                        # are outputs same?
                        if(support[0] in selected_attributes[table]):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                            continue
                        else:
                            r12 = r1 + r2
                            s12 = np.array(s12)
                            r12 = np.array(r12)
                            tmp_flag = (s12 == r12)
                            if(False in tmp_flag):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                    
                                                  
            price += removed_num * price_cof
        return price
    def price_distinct_query(self, sql):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.replace("distinct", "")
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        id_select = ".aID, ".join(query_tables) + ".aID, "
        tmp_sql = sql.replace("select",  "select " + id_select)
        all_results = select(tmp_sql, database=self.db)
        table_num = len(query_tables)
        # get the distinct results and each group size
        distinct_groups = defaultdict(int)
        all_results_groups = defaultdict(list)
        for item in all_results:
            tmp_data = item[table_num:]
            if(len(tmp_data) == 0): # no data
                tmp_data = [1]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
            distinct_groups[tuple(tmp_data)] += 1

        for ii, table in enumerate(query_tables):
            support_set = self.support_sets[table]
            removed_num = 0
            price_cof = self.price_coeff[table]
            # new_sql = sql.replace(table, table+ "_support")
            new_sql = sql.replace(table + " ", table + self.support_suffix + " ")
            new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
            new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
            new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
            # print(table, new_sql)
            new_rs = select(new_sql, database=self.db)
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                if(len(tmp_data) == 0): # no data
                    tmp_data = [1]
                new_rs_groups[tmp_sid].append(tmp_data)
            
            support_num = len(support_set)

            
            for sid in range(support_num):
                # if(sid == 1): # == 3 29
                    # print("1111")
                # if(len(all_results_groups.keys()) != 0):
                    # print(sid)    
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        if(support[0] in selected_attributes[table]):
                            r1 = all_results_groups[aid]
                            r2 = new_rs_groups[sid]
                            old_groups = defaultdict(int)
                            for item in r1:
                                old_groups[item] = distinct_groups[item]
                            for item in r2:
                                old_groups[item] = distinct_groups[item]
                            for item in r1:
                                distinct_groups[item] -= 1
                            for item in r2:
                                distinct_groups[item] += 1
                            for g in old_groups.keys():
                                if((old_groups[g]> 0 and distinct_groups[g] <= 0) or (old_groups[g] <= 0 and distinct_groups[g]>0)):
                                    removed_num += 1
                                    if(self.history_aware):
                                        self.price_history[table].append(sid)
                                    break
                            for item in r1:
                                distinct_groups[item] += 1
                            for item in r2:
                                distinct_groups[item] -= 1         
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        s1 = new_rs_groups[sid][0]
                        if(s1 not in distinct_groups.keys()): # new result
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        r1 = all_results_groups[aid]
                        for item in r1:
                            if(distinct_groups[item] == 1): # lose a result
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    cnt = cn1 = cn2 = 0
                    r1 = []
                    r2 = []
                    s12 = []
                    
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                        cn1 = len(r1)
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                        cn2 = len(r2)
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                        cnt = len(s12)
                    if(cnt == 0): # swapped tuples do not satisfy the conditions
                        if(cn1 == 0 and cn2 == 0): #not results
                            continue                       
                    # evaluate the original results
                    
                    old_groups = defaultdict(int)
                    for item in r1:
                        old_groups[item] = distinct_groups[item]
                    for item in r2:
                        old_groups[item] = distinct_groups[item]
                    for item in s12:
                        old_groups[item] = distinct_groups[item]
                    for item in r1:
                        distinct_groups[item] -= 1
                    for item in r2:
                        distinct_groups[item] -= 1
                    for item in s12:
                        distinct_groups[item] += 1
                    for g in old_groups.keys():
                        if((old_groups[g]> 0 and distinct_groups[g] <= 0) or (old_groups[g] <= 0 and distinct_groups[g]>0)):
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                            break
                    for item in r1:
                        distinct_groups[item] += 1
                    for item in r2:
                        distinct_groups[item] += 1
                    for item in s12:
                        distinct_groups[item] -= 1
                    
            price += removed_num * price_cof
        return price

    def pre_price_distinct_query(self, sql, all_results, support_rs):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.replace("distinct", "")
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table_num = len(query_tables)
        # get the distinct results and each group size
        distinct_groups = defaultdict(int)
        all_results_groups = defaultdict(list)
        for item in all_results:
            tmp_data = item[table_num:]
            if(len(tmp_data) == 0): # no data
                tmp_data = [1]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
            distinct_groups[tuple(tmp_data)] += 1
        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        for ii, table in enumerate(query_tables):
            support_set = self.support_sets[table]
            support_num = len(support_set)
            removed_num = 0
            price_cof = self.price_coeff[table]
            
            new_rs = support_rs[ii]
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                if(len(tmp_data) == 0): # no data
                    tmp_data = [1]
                new_rs_groups[tmp_sid].append(tmp_data)           
            for sid in range(support_num):
                # if(sid == 1): # == 3 29
                    # print("1111")
                # if(len(all_results_groups.keys()) != 0):
                    # print(sid)    
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        if(support[0] in selected_attributes[table]):
                            r1 = all_results_groups[aid]
                            r2 = new_rs_groups[sid]
                            old_groups = defaultdict(int)
                            for item in r1:
                                old_groups[item] = distinct_groups[item]
                            for item in r2:
                                old_groups[item] = distinct_groups[item]
                            for item in r1:
                                distinct_groups[item] -= 1
                            for item in r2:
                                distinct_groups[item] += 1
                            for g in old_groups.keys():
                                if((old_groups[g]> 0 and distinct_groups[g] <= 0) or (old_groups[g] <= 0 and distinct_groups[g]>0)):
                                    removed_num += 1
                                    if(self.history_aware):
                                        self.price_history[table].append(sid)
                                    break
                            for item in r1:
                                distinct_groups[item] += 1
                            for item in r2:
                                distinct_groups[item] -= 1         
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        s1 = new_rs_groups[sid][0]
                        if(s1 not in distinct_groups.keys()): # new result
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        r1 = all_results_groups[aid]
                        for item in r1:
                            if(distinct_groups[item] == 1): # lose a result
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    cnt = cn1 = cn2 = 0
                    r1 = []
                    r2 = []
                    s12 = []
                    
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                        cn1 = len(r1)
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                        cn2 = len(r2)
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                        cnt = len(s12)
                    if(cnt == 0): # swapped tuples do not satisfy the conditions
                        if(cn1 == 0 and cn2 == 0): #not results
                            continue                       
                    # evaluate the original results
                    
                    old_groups = defaultdict(int)
                    for item in r1:
                        old_groups[item] = distinct_groups[item]
                    for item in r2:
                        old_groups[item] = distinct_groups[item]
                    for item in s12:
                        old_groups[item] = distinct_groups[item]
                    for item in r1:
                        distinct_groups[item] -= 1
                    for item in r2:
                        distinct_groups[item] -= 1
                    for item in s12:
                        distinct_groups[item] += 1
                    for g in old_groups.keys():
                        if((old_groups[g]> 0 and distinct_groups[g] <= 0) or (old_groups[g] <= 0 and distinct_groups[g]>0)):
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                            break
                    for item in r1:
                        distinct_groups[item] += 1
                    for item in r2:
                        distinct_groups[item] += 1
                    for item in s12:
                        distinct_groups[item] -= 1
                    
            price += removed_num * price_cof
        return price
    def price_limit_query(self, sql):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        tmp_str = sql.split("limit")
        
        k = int(tmp_str[1])
        if(k == 0):
            return 0
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table_num = len(query_tables)
        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        id_select = ".aID, ".join(query_tables) + ".aID, "
        tmp_sql = sql.replace("select",  "select " + id_select)
        all_results = select(tmp_sql, database=self.db)
        all_results_groups = defaultdict(list)
        for item in all_results[:k]:
            tmp_data = item[table_num:]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
        n = len(all_results)
        # print(tmp_sql)
        # print(n)
        for ii, table in enumerate(query_tables):
            support_set = self.support_sets[table]
            removed_num = 0
            price_cof = self.price_coeff[table]
            # new_sql = new_sql.replace(table, table+ "_support")
            new_sql = tmp_str[0]
            new_sql = new_sql.replace(table + " ", table + self.support_suffix + " ")
            new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
            new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
            new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
            # print(new_sql)
            new_rs = select(new_sql, database=self.db)
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)
            
            
            support_num = len(support_set)
            if(n != 0):
                tmp_id = int(all_results[-1][ii])
            else:
                if(len(new_rs) != 0):
                    tmp_id = int(self.table_size[table])
                else:
                    tmp_id =  ''
            max_id = table + "." + str(tmp_id) 
            
            for sid in range(support_num):
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                # if(sid == 3787):
                    # print("222")
                support = support_set[sid]
                aid = support[1]
                # print(support, aid, table)
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute is selected
                        if(support[0] in selected_attributes[table]):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        # check whether the tuple can be outputted
                        if(k > n):
                            # this tuple can be outputted in N1 neighbor database
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                        if(k <= n):
                            if(aid < max_id):
                                # this tuple can be outputted in N1 neighbor database
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    cnt = cn1 = cn2 = 0
                    r1 = []
                    r2 = []
                    s12 = []
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                        cn1 = len(r1)
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                        cn2 = len(r2)
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                        cnt = len(s12)
                    if(cnt == 0): # swapped tuples do not satisfy the conditions
                        if(cn1 == 0 and cn2 == 0): #not results
                            continue  
                    
                    s1 = [item[1:] for item in s12 if item[0] == support[1]]
                    s2 = [item[1:] for item in s12 if item[0] == support[2]]
                    cnt_1 = len(s1)
                    cnt_2 = len(s2)
                    tmp_n = n
                    # the limit results in the N2 neighbor db
                    if(cnt_1 == 1):
                        if(k <= tmp_n and aid > max_id):
                            # cannot be the results in the limit case 
                            cnt_1 == 0
                            s1 = []
                        else:
                            # can be the results
                            if(cn1 == 0):
                                # the result size increases in the N2 neighbor hood
                                tmp_n += 1
                            max_id = max(max_id, aid)
                    if(cnt_2 == 1):
                        if(k <= tmp_n and bid > max_id):
                            cnt_2 == 0
                            s2 = []
                    
                    s12 = s1 + s2
                    r12 = r1 + r2
                    if(s12 != r12):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                                                  
            price += removed_num * price_cof
        return price
    
    def pre_price_limit_query(self, sql, all_results, support_rs):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        tmp_str = sql.split("limit")
        new_sql = tmp_str[0]
        k = int(tmp_str[1])
        if(k == 0):
            return 0
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table_num = len(query_tables)
        n = len(all_results)
        all_results_groups = defaultdict(list)
        for item in all_results[:k]:
            tmp_data = item[table_num:]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        for ii, table in enumerate(query_tables):
            support_set = self.support_sets[table]
            removed_num = 0
            price_cof = self.price_coeff[table]
            support_num = len(support_set)
            new_rs = support_rs[ii]
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)

            if(n != 0):
                tmp_id = int(all_results[-1][ii])
            else:
                if(len(new_rs) != 0):
                    tmp_id = int(self.table_size[table])
                else:
                    tmp_id = ''
            max_id = table + "." + str(tmp_id)             
            for sid in range(support_num):
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                # if(sid == 3787):
                    # print("222")
                support = support_set[sid]
                aid = support[1]
                # print(support, aid, table)
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute is selected
                        if(support[0] in selected_attributes[table]):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        # check whether the tuple can be outputted
                        if(k > n):
                            # this tuple can be outputted in N1 neighbor database
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                        if(k <= n):
                            if(aid < max_id):
                                # this tuple can be outputted in N1 neighbor database
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    cnt = cn1 = cn2 = 0
                    r1 = []
                    r2 = []
                    s12 = []
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                        cn1 = len(r1)
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                        cn2 = len(r2)
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                        cnt = len(s12)
                    if(cnt == 0): # swapped tuples do not satisfy the conditions
                        if(cn1 == 0 and cn2 == 0): #not results
                            continue  
                    
                    s1 = [item[1:] for item in s12 if item[0] == support[1]]
                    s2 = [item[1:] for item in s12 if item[0] == support[2]]
                    cnt_1 = len(s1)
                    cnt_2 = len(s2)
                    tmp_n = n
                    # the limit results in the N2 neighbor db
                    if(cnt_1 == 1):
                        if(k <= tmp_n and aid > max_id):
                            # cannot be the results in the limit case 
                            cnt_1 == 0
                            s1 = []
                        else:
                            # can be the results
                            if(cn1 == 0):
                                # the result size increases in the N2 neighbor hood
                                tmp_n += 1
                            max_id = max(max_id, aid)
                    if(cnt_2 == 1):
                        if(k <= tmp_n and bid > max_id):
                            cnt_2 == 0
                            s2 = []
                    
                    s12 = s1 + s2
                    r12 = r1 + r2
                    if(s12 != r12):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                                                  
            price += removed_num * price_cof
        return price
    def price_extreme_query(self, sql):
        if("group by" in sql):
            return self.price_extreme_query_with_group(sql)
        else:
            return self.price_extreme_query_no_group(sql)
    
    def pre_price_extreme_query(self, sql, all_results, support_rs):
        if("group by" in sql):
            return self.pre_price_extreme_query_with_group(sql, all_results, support_rs)
        else:
            return self.pre_price_extreme_query_no_group(sql, all_results, support_rs)  
    def price_extreme_query_no_group(self, sql):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        # sql = sql.split("group by")[0]
        flag = True
        if("max(" in sql):
            flag = True
            pattern = r"max\((.*?)\)"
            sql = re.sub(pattern, replace_count, sql)
        if("min(" in sql):
            flag = False
            pattern = r"min\((.*?)\)"
            sql = re.sub(pattern, replace_count, sql)
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        if(len(query_tables) > 1):
            print("cannot process the max/min query on multiple tables")
            return -1
        
        id_select = ".aID, ".join(query_tables) + ".aID, "
        tmp_sql = sql.replace("select",  "select " + id_select)
        # print(tmp_sql)
        all_results = select(tmp_sql, database=self.db)
        table_num = len(query_tables)
        all_results_groups = defaultdict(list)
        v_values = []
        for item in all_results:
            tmp_data = item[table_num:]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
            v_values.append(item[-1])
        for table in query_tables:
            # get the projected attributes on this table 
            selected_attributes = []
            for att in md.projections:
                if "." in att:
                    str_list =  att.split(".")
                    table = str_list[0]
                    selected_attributes.append(str_list[1])
                else:
                    for tt in query_tables:
                        if(att in self.table_fields[tt]):
                            selected_attributes.append(att)
                            break
            support_set = self.support_sets[table]
            removed_num = 0
            price_cof = self.price_coeff[table]
            # new_sql = sql.replace(table, table+ "_support")
            new_sql = sql + ""
            new_sql = new_sql.replace(table + " ", table + self.support_suffix + " ")
            new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
            new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
            new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
            # print(table, new_sql)
            new_rs = select(new_sql, database=self.db)
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)
            
            support_num = len(support_set)

            if(flag):
                old_extreme = max(v_values, key=lambda x: float('-inf') if x is None else x)
                # extreme_value = max(all_results, key=lambda x: float('-inf') if x is None or x[-1] is None else x[-1])[-1]
                # old_extreme = max(v_values)
            else:
                old_extreme = min(v_values, key=lambda x: float('inf') if x is None else x)

            for sid in range(support_num):
                # if(sid == 26):
                #     print("1111")
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute changes the extreme value
                        if(support[0] in selected_attributes):
                            # remove the aid from original group would change the result?
                            r1 = all_results_groups[aid][0]
                            r2 =  new_rs_groups[sid][0]
                            v_values.remove(r1[-1])
                            v_values.append(r2[-1])
                            if(flag):
                                new_extreme = max(v_values, key=lambda x: float('-inf') if x is None else x)
                            else:
                                new_extreme = min(v_values, key=lambda x: float('inf') if x is None else x)
                            if(new_extreme != old_extreme):
                                # the original group changes 
                                # print(sid, aid, support[-2], support[-1])
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                            v_values.append(r1[-1])
                            v_values.remove(r2[-1])
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        # check whether the new value changes another group
                        r2 = [item for item in new_rs if item[0] == sid][0]
                        # test the new tuple
                        new_extreme = old_extreme
                        if(flag):
                            if(r2[-1] is not None):
                                new_extreme = max(old_extreme, r2[-1])
                        else:   
                            if(r2[-1] is not None):
                                new_extreme = min(old_extreme, r2[-1])
                                
                        if(new_extreme != old_extreme):
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        # remove the aid from original group would change the result?
                        r1 = all_results_groups[aid][0]
                        v_values.remove(r1[-1])
                        if(flag):
                            # new_extreme = max(v_values)
                            new_extreme = max(v_values, key=lambda x: float('-inf') if x is None else x)
                        else:
                            # new_extreme = min(v_values)
                            new_extreme = min(v_values, key=lambda x: float('inf') if x is None else x)
                        if(new_extreme != old_extreme):
                            # the original group changes 
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                        v_values.append(r1[-1])
                else:
                    # N2 neighbor hood
                    r1 = all_results_groups[aid]
                    r2 = all_results_groups[bid]
                    s12 = new_rs_groups[sid]
                    if(len(s12) == 0 and len(r1) == 0 and len(r2) == 0):
                        # both are not results
                        continue
                    for item in r1:
                        # remove r1 from the original group
                        v_values.remove(item[-1])
                    for item in r2:
                        # remove r2 from the original group
                        v_values.remove(item[-1])
                    for item in s12:
                        # add s1 and s2 into the groups
                        v_values.append(item[-1])
                    if(flag):
                        # new_extreme = max(v_values)
                        new_extreme = max(v_values, key=lambda x: float('-inf') if x is None else x)
                    else:
                        # new_extreme = min(v_values)
                        new_extreme = min(v_values, key=lambda x: float('inf') if x is None else x)
                    if(new_extreme != old_extreme):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    for item in r1:
                        v_values.append(item[-1])
                    for item in r2:
                        v_values.append(item[-1])
                    for item in s12:
                        v_values.remove(item[-1])
                                                
            price += removed_num * price_cof
        return price
    
    def pre_price_extreme_query_no_group(self, sql, all_results, support_rs):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        # sql = sql.split("group by")[0]
        flag = True
        if("max(" in sql):
            flag = True
            pattern = r"max\((.*?)\)"
            sql = re.sub(pattern, replace_count, sql)
        if("min(" in sql):
            flag = False
            pattern = r"min\((.*?)\)"
            sql = re.sub(pattern, replace_count, sql)
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        if(len(query_tables) > 1):
            print("cannot process the max/min query on multiple tables without the group by clause")
            return -1
        
        table_num = len(query_tables)
        all_results_groups = defaultdict(list)
        v_values = []
        for item in all_results:
            tmp_data = item[table_num:]
            table_name = query_tables[0]
            tmp_aid = int(item[0])
            all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
            v_values.append(item[-1])
        for ii, table in enumerate(query_tables):
            # get the projected attributes on this table 
            selected_attributes = []
            for att in md.projections:
                if "." in att:
                    str_list =  att.split(".")
                    table = str_list[0]
                    selected_attributes.append(str_list[1])
                else:
                    for tt in query_tables:
                        if(att in self.table_fields[tt]):
                            selected_attributes.append(att)
                            break
            support_set = self.support_sets[table]
            support_num = len(support_set)
            removed_num = 0
            price_cof = self.price_coeff[table]
            new_rs_groups = defaultdict(list)
            new_rs = support_rs[ii]
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)
            
            
            if(flag):
                sorted_values = sorted(v_values, key=lambda x: float('-inf') if x is None else x, reverse = True)
                # old_extreme = max(v_values, key=lambda x: float('-inf') if x is None else x)
            else:
                sorted_values = sorted(v_values, key=lambda x: float('-inf') if x is None else x, reverse = False)
                # old_extreme = min(v_values, key=lambda x: float('inf') if x is None else x)
            # as the N2 neighborhood can only change the number of values at most 2.
            # store the top-3 values
            old_extreme = sorted_values[:4]
            if(len(old_extreme) == 0):
                if(flag):
                    old_extreme = [float('-inf')] * 4 
                else:
                    old_extreme = [float('inf')] * 4 
            for sid in range(support_num):
                # if(sid == 26):
                #     print("1111")
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute changes the extreme value
                        if(support[0] in selected_attributes):
                            # remove the aid from original group would change the result?
                            r1 = all_results_groups[aid][0][0] # the original value
                            # print(all_results_groups[aid])
                            r2 =  new_rs_groups[sid][0][0] # the new value
                            # print(r1, r2, old_extreme[0])
                            if((flag and r2 > old_extreme[0]) or (not flag and r2 < old_extreme[0])): # higher/lower than the current extreme
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                            else:
                                new_extreme = [i for i in old_extreme]
                                if(r1 in new_extreme):
                                    new_extreme.remove(r1)
                                new_extreme.append(r2)
                                if((flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                    removed_num += 1
                                    if(self.history_aware):
                                        self.price_history[table].append(sid)
                                
                                
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        # check whether the new value changes another group
                        r2 = new_rs_groups[sid][0]
                        # test the new tuple
                        new_extreme = old_extreme
                        if(flag):
                            if(r2[-1] is not None):
                                new_extreme = max(old_extreme[0], r2[-1])
                        else:   
                            if(r2[-1] is not None):
                                new_extreme = min(old_extreme[0], r2[-1])
                                
                        if(new_extreme != old_extreme):
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        # remove the aid from original group would change the result?
                        r1 = all_results_groups[aid][0][0]
                        new_extreme = [i for i in old_extreme]
                        if(r1 in new_extreme):
                            new_extreme.remove(r1)
                            if((flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    r1 = []
                    r2 = []
                    s12 = []
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                    if(len(s12) == 0 and len(r1) == 0 and len(r2) == 0):
                        # both are not results
                        continue
                    new_extreme = [i for i in old_extreme]
                    for item in r1:
                        if(item[-1] in new_extreme):
                            new_extreme.remove(item[-1])
                    for item in r2:
                        if(item[-1] in new_extreme):
                            new_extreme.remove(item[-1])
                            
                    for item in s12:
                        new_extreme.append(item[-1])     
                    
                    if((flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                                                
            price += removed_num * price_cof
        return price
    def price_extreme_query_with_group(self, sql):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.split("group by")[0]
        flag = True
        if("max(" in sql):
            flag = True
            pattern = r"max\((.*?)\)"
            sql = re.sub(pattern, replace_count, sql)
        if("min(" in sql):
            flag = False
            pattern = r"min\((.*?)\)"
            sql = re.sub(pattern, replace_count, sql)
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        if(len(query_tables) > 1):
            print("cannot process the max/min query on multiple tables")
            return -1
        for table in query_tables:
            # get the projected attributes on this table 
            selected_attributes = []
            for att in md.projections:
                if "." in att:
                    str_list =  att.split(".")
                    table = str_list[0]
                    selected_attributes.append(str_list[1])
                else:
                    for tt in query_tables:
                        if(att in self.table_fields[tt]):
                            selected_attributes.append(att)
                            break
            support_set = self.support_sets[table]
            removed_num = 0
            price_cof = self.price_coeff[table]
            # new_sql = sql.replace(table, table+ "_support")
            new_sql = sql
            new_sql = new_sql.replace(table + " ", table + self.support_suffix + " ")
            new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
            new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
            new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
            # print(table, new_sql)
            new_rs = select(new_sql, database=self.db)
            id_rs = [item[0] for item in new_rs]
            new_sql = sql.replace("select",  "select " + table + ".aID, ")
            all_results = select(new_sql, database=self.db)
            o_id = [item[0] for item in all_results]
            support_num = len(support_set)

            results_groups = defaultdict(list)
            # group by original results
            for item in all_results:
                results_groups[tuple(item[1:-1])].append(item[-1])
                # results_groups[tuple([1])].append(item[-1])
            extreme_groups = {}
            for item in results_groups.keys():
                if(flag):
                    extreme_groups[item] = max(results_groups[item])
                else:
                    extreme_groups[item] = min(results_groups[item])

            for sid in range(support_num):
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                bid = support[2]
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in o_id and sid in id_rs): # both are results
                        # check whether the changed attribute changes the extreme value
                        if(support[0] in selected_attributes):
                            # remove the aid from original group would change the result?
                            is_changed = False 
                            r1 = [item[1:] for item in all_results if item[0] == aid]
                            r2 = [item[1:] for item in new_rs if item[0] == sid]
                            old_extreme_list = {}
                            for item in r1:
                                old_extreme_list[tuple(item[:-1])] = extreme_groups[tuple(item[:-1])]
                            for item in r2:
                                if tuple(item[:-1]) in extreme_groups.keys():
                                    old_extreme_list[tuple(item[:-1])] = extreme_groups[tuple(item[:-1])]   
                                else:
                                    # produce the new group 
                                    if(r2[-1] != None):
                                        is_changed = True
                            if(not is_changed):
                                for item in r1:
                                    results_groups[tuple(item[:-1])].remove(item[-1])
                                for item in r2:
                                    results_groups[tuple(item[:-1])].append(item[-1])
                                
                                for g in old_extreme_list.keys():
                                    if(len(results_groups[g]) == 0):
                                        is_changed = True
                                        break
                                    if(flag):
                                        new_extreme = max(results_groups[g])
                                    else:
                                        new_extreme = min(results_groups[g])
                                    if(new_extreme != old_extreme_list[g]):
                                        is_changed = True
                                        break
                                for item in r1:
                                    results_groups[tuple(item[:-1])].append(item[-1])
                                for item in r2:
                                    results_groups[tuple(item[:-1])].remove(item[-1])
                            if(is_changed):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                    elif(aid not in o_id and sid in id_rs):
                        # check whether the new value changes another group
                        r2 = [item for item in new_rs if item[0] == sid][0]
                        # test the new tuple
                        if tuple(r2[1:-1]) in extreme_groups.keys():
                            old_extreme = extreme_groups[tuple(r2[1:-1])]
                            if(flag):
                                new_extreme = max(old_extreme, r2[-1])
                            else:   
                                new_extreme = min(old_extreme, r2[-1])
                            if(new_extreme != old_extreme):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                        else:
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid in o_id and sid not in id_rs):
                        # remove the aid from original group would change the result?
                        r1 = [item for item in all_results if item[0] == aid][0]
                        results_groups[tuple(r1[1:-1])].remove(r1[-1])
                        is_changed = False
                        if(len(results_groups[tuple(r1[1:-1])]) == 0):
                            is_changed = True
                        else:
                            if(flag):
                                new_extreme = max(results_groups[tuple(r1[1:-1])])
                            else:
                                new_extreme = min(results_groups[tuple(r1[1:-1])])
                            if(new_extreme != extreme_groups[tuple(r1[1:-1])]):
                                is_changed = True
                            # the original group changes 
                            # print(sid, aid, support[-2], support[-1])
                        if(is_changed):
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                        results_groups[tuple(r1[1:-1])].append(r1[-1])
                else:
                    # N2 neighbor hood
                    is_changed = False
                    r1 = [item[1:] for item in all_results if item[0] == aid]
                    r2 = [item[1:] for item in all_results if item[0] == bid]
                    s12 = [item[1:] for item in new_rs if item[0] == sid]
                    if(len(s12) == 0 and len(r1) == 0 and len(r2) == 0):
                        # both are not results
                        continue
                    old_extreme_list = {}
                    for item in r1:
                        old_extreme_list[tuple(item[:-1])] = extreme_groups[tuple(item[:-1])]
                        
                    for item in r2:
                        old_extreme_list[tuple(item[:-1])] = extreme_groups[tuple(item[:-1])]   
                        
                    for item in s12:
                        if tuple(item[:-1]) in extreme_groups.keys():
                            old_extreme_list[tuple(item[:-1])] = extreme_groups[tuple(item[:-1])]
                        else:
                            # produce the new groups
                            is_changed = True
                            break
                    if(not is_changed):
                        
                        for item in r1:
                            # remove r1 from the original group
                            # print(aid, item)
                            # print(results_groups[tuple(item[:-1])], item[-1])
                            results_groups[tuple(item[:-1])].remove(item[-1])
                        for item in r2:
                            # remove r2 from the original group
                            results_groups[tuple(item[:-1])].remove(item[-1])
                        for item in s12:
                            # add s1 and s2 into the groups
                            results_groups[tuple(item[:-1])].append(item[-1])
                        
                        for g in old_extreme_list.keys():
                            if(len(results_groups[g]) == 0):
                                is_changed = True
                                break
                            if(flag):
                                new_extreme = max(results_groups[g])
                            else:
                                new_extreme = min(results_groups[g])
                            if(new_extreme != old_extreme_list[g]):
                                is_changed = True
                                break
                        for item in r1:
                            results_groups[tuple(item[:-1])].append(item[-1])
                        for item in r2:
                            results_groups[tuple(item[:-1])].append(item[-1])
                        for item in s12:
                            results_groups[tuple(item[:-1])].remove(item[-1])
                    if(is_changed):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)                                               
            price += removed_num * price_cof
        return price
    
    def pre_price_extreme_query_with_group(self, sql, all_results, support_rs):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.split("group by")[0]
        flag = True
        if("max(" in sql):
            flag = True
            pattern = r"max\((.*?)\)"
            
        if("min(" in sql):
            flag = False
            pattern = r"min\((.*?)\)"
        
       # get the aggregated attribute
        agg_att = re.findall(pattern, sql)[0] 
                
        sql = re.sub(pattern, replace_count, sql)
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table_num = len(query_tables)

        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        
        if "." in agg_att:
            str_list = att.split(".")
            table = str_list[0]
            agg_table = table
            agg_att = str_list[1]
        else:
            for table in query_tables:
                if(agg_att in self.table_fields[table]):
                    agg_table = table
                    break 
        selected_attributes[agg_table].append(agg_att)      
        
        results_groups = defaultdict(list)
        all_results_groups = defaultdict(list)
        # group by original results
        for item in all_results:
            tmp_data = item[table_num:]
            results_groups[tuple(tmp_data[:-1])].append(tmp_data[-1])
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
        
        for ii, table in enumerate(query_tables):
            
            support_set = self.support_sets[table]
            removed_num = 0
            price_cof = self.price_coeff[table]
            
            new_rs = support_rs[ii]
            support_num = len(support_set)

            
            new_rs_groups = defaultdict(list)
            
                # results_groups[tuple([1])].append(item[-1])
            # print(all_results_groups)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)
                
            extreme_groups = {}
            for item in results_groups.keys():
                if(flag):
                    extreme_groups[item] = sorted(results_groups[item], key=lambda x: float('-inf') if x is None else x, reverse = True)[:4]
                else:
                    extreme_groups[item] = sorted(results_groups[item], key=lambda x: float('-inf') if x is None else x, reverse = False)[:4]

            for sid in range(support_num):
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute changes the extreme value
                        if(support[0] in selected_attributes[table]):
                            # remove the aid from original group would change the result?
                            is_changed = False 
                            r1 = all_results_groups[aid][0]
                            r2 = new_rs_groups[sid][0]
                            if(r1[:-1] == r2[:-1]):
                                # in the same group
                                old_extreme = extreme_groups[r1[:-1]]
                                r1 = r1[-1] # the original value
                                r2 = r2[-1] # the new value    
                                if((flag and r2 > old_extreme[0]) or (not flag and r2 < old_extreme[0])): # higher/lower than the current extreme
                                    removed_num += 1
                                    if(self.history_aware):
                                        self.price_history[table].append(sid)
                                else:
                                    new_extreme = [i for i in old_extreme]
                                    if(r1 in new_extreme):
                                        new_extreme.remove(r1)
                                    new_extreme.append(r2)
                                    if((flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                        removed_num += 1
                                        if(self.history_aware):
                                            self.price_history[table].append(sid)
                            else:           
                                # in the different group
                                # produce a new group
                                if(tuple(r2[:-1]) not in extreme_groups.keys()):
                                    removed_num += 1
                                    if(self.history_aware):
                                        self.price_history[table].append(sid)
                                else:
                                    # change the extreme value of each group?
                                    old_extreme = extreme_groups[r1[:-1]]
                                    new_extreme = [i for i in old_extreme]
                                    if(r1[-1] in new_extreme):
                                        new_extreme.remove(r1[-1])
                                        if(new_extreme == [] or (flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                            removed_num += 1
                                            if(self.history_aware):
                                                self.price_history[table].append(sid)
                                    else:
                                        old_extreme = extreme_groups[r2[:-1]]
                                        new_extreme = [i for i in old_extreme]   
                                        new_extreme.append(r2[-1])
                                        if((flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                            removed_num += 1
                                            if(self.history_aware):
                                                self.price_history[table].append(sid)
                    if(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()): 
                        # check whether the new value changes another group
                        r2 = new_rs_groups[sid][0]
                        # test the new tuple
                        if tuple(r2[:-1]) in extreme_groups.keys():
                            old_extreme = extreme_groups[r2[:-1]]
                            new_extreme = [i for i in old_extreme]   
                            new_extreme.append(r2[-1])
                            if((flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                        else:
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        # remove the aid from original group would change the result?
                        # print(aid, sid, all_results_groups[aid])
                        r1 = all_results_groups[aid][0]
                        # change the extreme value of each group?
                        old_extreme = extreme_groups[r1[:-1]]
                        new_extreme = [i for i in old_extreme]
                        if(r1[-1] in new_extreme):
                            new_extreme.remove(r1[-1])
                            # print(old_extreme, new_extreme)
                            # if(new_extreme != []):
                            if(new_extreme == [] or (flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    is_changed = False
                    r1 = []
                    r2 = []
                    s12 = []
                    if(sid in new_rs_groups.keys()):
                        s12 = new_rs_groups[sid]
                    if(aid in all_results_groups.keys()):
                        r1 = all_results_groups[aid]
                    if(bid in all_results_groups.keys()):
                        r2 = all_results_groups[bid]
                    if(len(s12) == 0 and len(r1) == 0 and len(r2) == 0):
                        # both are not results
                        continue
                    
                    # produce new groups ?
                    old_extreme_groups = {}
                    is_changed = False
                    for item in r1:
                        old_extreme_groups[item[:-1]] = extreme_groups[item[:-1]]
                    for item in r2:
                        old_extreme_groups[item[:-1]] = extreme_groups[item[:-1]]
                    for item in s12:
                        if tuple(item[:-1]) not in extreme_groups.keys():   
                            removed_num += 1
                            is_changed = True
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                            break
                        else:
                            # an existing group
                            old_extreme_groups[item[:-1]] = extreme_groups[item[:-1]]
                    if(not is_changed):
                        for gg in old_extreme_groups.keys():
                            old_extreme = old_extreme_groups[gg]
                            new_extreme = [i for i in old_extreme]
                            for item in r1:
                                if(item[:-1] == gg):
                                    if(item[-1] in new_extreme):
                                        new_extreme.remove(item[-1])
                            for item in r2:
                                if(item[:-1] == gg):
                                    if(item[-1] in new_extreme):
                                        new_extreme.remove(item[-1])     
                            for item in s12:
                                if(item[:-1] == gg):
                                    new_extreme.append(item[-1])    
                            if(new_extreme == [] or (flag and max(new_extreme) != old_extreme[0]) or (not flag and min(new_extreme) != old_extreme[0])):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid) 
                                                      
            price += removed_num * price_cof
        return price
    def price_cnt_query(self, sql):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.split("group by")[0]
        pattern = r"count\((.*?)\)"
        replacement = "1"
        sql = re.sub(pattern, replacement, sql)
        price = self.price_SPJ_query(sql)
        return price
    
    def pre_price_cnt_query(self, sql, all_results, support_rs):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.split("group by")[0]
        pattern = r"count\((.*?)\)"
        replacement = "1"
        sql = re.sub(pattern, replacement, sql)
        price = self.pre_price_SPJ_query(sql, all_results, support_rs)
        return price    
    def price_avg_query(self, sql):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.split("group by")[0]
        sql = sql.replace("sum(", "avg(")
        pattern = r"avg\((.*?)\)"
        sql = re.sub(pattern, replace_count, sql)
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table_num = len(query_tables)
        if(table_num > 1):
            print("cannot process the avg query on multiple tables")
            return -1

        for table in query_tables:
            # get the projected attributes on this table 
            selected_attributes = []
            for att in md.projections:
                if "." in att:
                    str_list =  att.split(".")
                    table = str_list[0]
                    selected_attributes.append(str_list[1])
                else:
                    for tt in query_tables:
                        if(att in self.table_fields[tt]):
                            selected_attributes.append(att)
                            break
            support_set = self.support_sets[table]
            removed_num = 0

            price_cof = self.price_coeff[table]
            # new_sql = sql.replace(table, table+ "_support")
            new_sql = sql.replace(table + " ", table + self.support_suffix + " ")
            new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
            new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
            new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
            # print(table, new_sql)
            new_rs = select(new_sql, database=self.db)
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)

            new_sql = sql.replace("select",  "select " + table + ".aID, ")
            all_results = select(new_sql, database=self.db)
            all_results_groups = defaultdict(list)
            for item in all_results:
                tmp_data = item[table_num:]
                for tmpi in range(table_num):
                    table_name = query_tables[tmpi]
                    tmp_aid = int(item[tmpi])
                    all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)

            support_num = len(support_set)

            for sid in range(support_num):
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute is selected
                        if(support[0] in selected_attributes):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    cnt = len(new_rs_groups[sid])
                    cn1 = len(all_results_groups[aid])
                    cn2 = len(all_results_groups[bid])
                    if(cnt != cn1 + cn2):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(cnt == 2 or cnt == 1): # both are results and they are still results after swapped
                        # are outputs same?                     
                        r1 = all_results_groups[aid]
                        r2 = all_results_groups[bid]
                        s12 = new_rs_groups[sid]
                        r12 = r1 + r2
                        if(s12 != r12):
                            r12 = r2 + r1 # avg ignore the effect of tuple order
                            if(s12 != r12):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)                                      
            price += removed_num * price_cof
        return price    


    def pre_price_avg_query(self, sql, all_results, support_rs):
        # parse the sql and get table name
        # 执行support set上查询
        # 遍历所有support set，看是否有结果
        
        price = 0
        sql = sql.split("group by")[0]
        sql = sql.replace("sum(", "avg(")
        pattern = r"avg\((.*?)\)"
        
        # get the aggregated attribute
        agg_att = re.findall(pattern, sql)[0] 
                
        sql = re.sub(pattern, replace_count, sql)
        md = QueryMetaData(sql)
        # print(md)
        query_tables = md.tables
        table_num = len(query_tables)

        # get the projected attributes on each table 
        selected_attributes = defaultdict(list)
        for att in md.projections:
            if "." in att:
                str_list =  att.split(".")
                table = str_list[0]
                selected_attributes[table].append(str_list[1])
            else:
                for tt in query_tables:
                    if(att in self.table_fields[tt]):
                        selected_attributes[tt].append(att)
                        break
        
        if "." in agg_att:
            str_list = att.split(".")
            table = str_list[0]
            agg_table = table
            agg_att = str_list[1]
        else:
            for table in query_tables:
                if(agg_att in self.table_fields[table]):
                    agg_table = table
                    break 
        selected_attributes[agg_table].append(agg_att)         
        
        
        all_results_groups = defaultdict(list)
        for item in all_results:
            tmp_data = item[table_num:]
            for tmpi in range(table_num):
                table_name = query_tables[tmpi]
                tmp_aid = int(item[tmpi])
                all_results_groups[table_name + "." + str(tmp_aid)].append(tmp_data)
        
        for ii, table in enumerate(query_tables):
            support_set = self.support_sets[table]
            support_num = len(support_set)
            removed_num = 0

            price_cof = self.price_coeff[table]
            
            new_rs = support_rs[ii]
            new_rs_groups = defaultdict(list)
            for item in new_rs:
                tmp_sid = int(item[0])
                tmp_data = item[1:]
                new_rs_groups[tmp_sid].append(tmp_data)

            

            for sid in range(support_num):
                if(self.history_aware and sid in self.price_history[table]):
                    continue
                support = support_set[sid]
                aid = support[1]
                aid = table + "." + str(aid)
                bid = support[2]
                bid = table + "." + str(bid)
                if(aid == bid):
                    # N1 neighborhood
                    if(aid in all_results_groups.keys() and sid in new_rs_groups.keys()): # both are results
                        # check whether the changed attribute is selected
                        if(support[0] in selected_attributes[table]):
                            # print(sid, aid, support[-2], support[-1])
                            removed_num += 1
                            if(self.history_aware):
                                self.price_history[table].append(sid)
                    elif(aid not in all_results_groups.keys() and sid in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(aid in all_results_groups.keys() and sid not in new_rs_groups.keys()):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                else:
                    # N2 neighbor hood
                    cnt = len(new_rs_groups[sid])
                    cn1 = len(all_results_groups[aid])
                    cn2 = len(all_results_groups[bid])
                    if(cnt != cn1 + cn2):
                        removed_num += 1
                        if(self.history_aware):
                            self.price_history[table].append(sid)
                    elif(cnt == 2 or cnt == 1): # both are results and they are still results after swapped
                        # are outputs same?                     
                        r1 = all_results_groups[aid]
                        r2 = all_results_groups[bid]
                        s12 = new_rs_groups[sid]
                        r12 = r1 + r2
                        if(s12 != r12):
                            r12 = r2 + r1 # avg ignore the effect of tuple order
                            if(s12 != r12):
                                removed_num += 1
                                if(self.history_aware):
                                    self.price_history[table].append(sid)                                      
            price += removed_num * price_cof
        return price    

    def price_SQL_query(self, sql):
        price = -1
        sql = sql.split(";")[0]
        sql = sql + " "
        tables = parse_sql_statements(sql)
        if("*" in sql):
            place_str = ""
            str_list = []
            for table in tables:
                # print(table)
                for s in self.table_fields[table]:
                    str_list.append(table+"."+ s)
            place_str = ",".join(str_list)
            sql = sql.replace("*", place_str)
        if("count(" in sql):
            price = self.price_cnt_query(sql)
        elif("distinct" in sql):
            price = self.price_distinct_query(sql)
        elif("limit" in sql):
            price = self.price_limit_query(sql)
        elif("avg(" in sql or "sum(" in sql):
            price = self.price_avg_query(sql)
        elif("max(" in sql or "min(" in sql):
            price = self.price_extreme_query(sql)
        else:
            price = self.price_SPJ_query(sql)
        return price
    
    def pre_price_SQL_query(self, sql, all_results, support_rs):
        price = -1
        sql = sql.split(";")[0]
        sql = sql + " "
        tables = parse_sql_statements(sql)
        if("*" in sql):
            place_str = ""
            str_list = []
            for table in tables:
                # print(table)
                for s in self.table_fields[table]:
                    str_list.append(table+"."+ s)
            place_str = ",".join(str_list)
            sql = sql.replace("*", place_str)
        if("count(" in sql):
            price = self.pre_price_cnt_query(sql, all_results, support_rs)
        elif("distinct" in sql):
            price = self.pre_price_distinct_query(sql, all_results, support_rs)
        elif("limit" in sql):
            price = self.pre_price_limit_query(sql, all_results, support_rs)
        elif("avg(" in sql or "sum(" in sql):
            price = self.pre_price_avg_query(sql, all_results, support_rs)
        elif("max(" in sql or "min(" in sql):
            price = self.pre_price_extreme_query(sql, all_results, support_rs)
        else:
            price = self.pre_price_SPJ_query(sql, all_results, support_rs)
        return price    
    
    def print_required_query(self, sql_list, mark = ""):
        new_sql_list = []
        mark_sql_list = []
        current_directory =  '/var/lib/mysql-files'
        for i, sql in enumerate(sql_list):
            new_sql_list.append([])
            price = -1
            sql = sql.split(";")[0]
            sql = sql + " "
            query_tables = parse_sql_statements(sql)
            table_num = len(query_tables)
            if("*" in sql):
                place_str = ""
                str_list = []
                for table in query_tables:
                    # print(table)
                    for s in self.table_fields[table]:
                        str_list.append(table+"."+ s)
                place_str = ",".join(str_list)
                sql = sql.replace("*", place_str)
            if("count(" in sql):
                if(mark == ""):
                    mark_sql_list.append("SA")
                else:
                    mark_sql_list.append(mark)
                sql = sql.split("group by")[0]
                pattern = r"count\((.*?)\)"
                replacement = "1"
                sql = re.sub(pattern, replacement, sql)
                new_sql = sql + ""

            elif("distinct" in sql):
                sql = sql.replace("distinct", "")
                if(mark == ""):
                    if(table_num > 1):
                        mark_sql_list.append("SPJ")
                    else:
                        mark_sql_list.append("SP")
                else:
                    mark_sql_list.append(mark)
                
                new_sql = sql + ""
            elif("limit" in sql):
                tmp_str = sql.split("limit")
                new_sql = tmp_str[0]
                if(mark == ""):
                    if(table_num > 1):
                        mark_sql_list.append("SJ")
                    else:
                        mark_sql_list.append("S")
                else:
                    mark_sql_list.append(mark)
                
            elif("avg(" in sql or "sum(" in sql):
                if(mark == ""):
                    mark_sql_list.append("SA")
                else:
                    mark_sql_list.append(mark)
                sql = sql.split("group by")[0]
                sql = sql.replace("sum(", "avg(")
                pattern = r"avg\((.*?)\)"
                sql = re.sub(pattern, replace_count, sql)
                new_sql = sql + ""
            elif("max(" in sql or "min(" in sql):
                if(mark == ""):
                    mark_sql_list.append("SA")
                else:
                    mark_sql_list.append(mark)
                sql = sql.split("group by")[0]
                if("max(" in sql):
                    pattern = r"max\((.*?)\)"
                    sql = re.sub(pattern, replace_count, sql)
                if("min(" in sql):
                    pattern = r"min\((.*?)\)"
                    sql = re.sub(pattern, replace_count, sql)
                new_sql = sql + ""
            else:
                if(mark == ""):
                    if(table_num > 1):
                        mark_sql_list.append("SJ")
                    else:
                        mark_sql_list.append("S")
                else:
                    mark_sql_list.append(mark)
                new_sql = sql + ""
            id_select = ".aID, ".join(query_tables) + ".aID, "
            tmp_sql = sql.replace("select",  "select " + id_select)
            outfile_path = current_directory + f"/{self.db}-{mark_sql_list[-1]}-{i}-QAPricer-o.txt"
            tmp_sql = f"{tmp_sql} INTO OUTFILE '{outfile_path}' FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' LINES TERMINATED BY '\\n';"
            new_sql_list[-1].append(tmp_sql)
            tmp_sql = new_sql + ""
            for ii, table in enumerate(query_tables):
                new_sql = tmp_sql.replace(table + " ", table + self.support_suffix + " ")
                new_sql = new_sql.replace(table + ",", table + self.support_suffix + ",")
                new_sql = new_sql.replace(table + ".", table + self.support_suffix + ".")
                new_sql = new_sql.replace("select", "select " + table + self.support_suffix + ".sID, ")
                outfile_path = current_directory + f"/{self.db}-{mark_sql_list[-1]}-{i}-QAPricer-{ii}.txt"
                new_sql = f"{new_sql} INTO OUTFILE '{outfile_path}' FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' LINES TERMINATED BY '\\n';"
                new_sql_list[-1].append(new_sql)
            # print("------------------")
            # for ss in new_sql_list[-1]:
                # print(ss)
            # print(mark_sql_list[-1])
        
        return new_sql_list
    
    
    
if __name__ == "__main__":
    print("--------------------------------")
    support_suffix = "_qa_support"
    qa_pricer = QAPricer(db, table_list, table_fields, history, table_price_list, table_size_list, support_suffix, history_aware)
    
    print("-----------------------")
    for s in mark_sql_list.keys():
        sql_list = mark_sql_list[s]
        print(s)
        qa_pricer.print_required_query(sql_list)



