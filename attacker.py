

import math
import time
import pandas as pd
from abUtils import *


class Attacker:
    def __init__(self):
        pass 

    def cardinality_attack_limit(self, query, pricer, real_cardinality, max_cardinality, price = -1):
        flag = isinstance(pricer, QAPricer)
        if flag:
            table, aid_list, sid_list = pricer.tmp_rs_price_limit_query(query)
            price = pricer.price_limit_varying_K_query(aid_list, sid_list, max_cardinality, table)
        else:
            price = pricer.price_SQL_query(query)
        if price == 0:
            return real_cardinality
        left, right = 0, max_cardinality
        while left < right:
            mid = (left + right) // 2
            if flag:
                # if right == 20:
                #     print("test")
                new_price = pricer.price_limit_varying_K_query(aid_list, sid_list, mid, table, price)
            else:
                if mid >= real_cardinality:
                    new_price = price
                else:
                    new_price = price * (mid/real_cardinality)
            if new_price >= price:
                right = mid
            else:
                left = mid + 1
        return left
    
    def cardinality_attack_having(self, query, pricer, real_cardinality, max_cardinality, price = -1):
        if not isinstance(pricer, QAPricer):
            return -1
        # get the price of select count(*) if the query 
        price_dic = pricer.price_having_varying_K_query(query)
        price = price_dic[real_cardinality]
        if price == 0:
            return real_cardinality
        left, right = 0, max_cardinality
        while left < right:
            mid = (left + right) // 2
            if mid <= real_cardinality:
                new_price = price
            elif mid == real_cardinality + 1:
                new_price = price_dic[real_cardinality + 1] + price_dic[real_cardinality + 2]
            elif mid == real_cardinality + 2:
                new_price = price_dic[real_cardinality + 2]
            else:
                new_price = 0
            if new_price > 0:
                left = mid + 1
            else:
                right = mid
        inferred_cardinality = 0
        n = 0
        for K in range(left - 5, left + 2):
            if K >= real_cardinality -2 and K <= real_cardinality + 2:
                new_price = price_dic[K]
            else:
                new_price = 0
            if new_price == price:
                inferred_cardinality = n/(n + 1) * inferred_cardinality + 1/(n+1) * K 
                n += 1
        return math.floor(inferred_cardinality)

        
        
    def membership_attack_naive(self, query, pricer, real_membership, price = -1):
        if price == -1:
            price = pricer.price_SQL_query(query)
        if price == 0:
            return real_membership
        else:
            return True
    def membership_attack_fixed_add(self, query, pricer, real_membership, price = -1):
        return True
    def membership_attack_optimized(self, query_list, pricer, real_membership_list, price_list = []):
        # loop the query and price list
        X1 = X2 = -1
        if len(price_list) == 0:
            price_list = [pricer.price_SQL_query(query) for query in query_list]
        p1, p2, p = price_list
        if p1 == 0 or p2 == 0:
            if p1 == 0: 
                X1 = real_membership_list[0]
            if p2 == 0:
                X2 = real_membership_list[1]
        else:
            if p == p1 + p2:
                X1 = X2 = 1 
            elif p == 0:
                X1 = X2 = 0
            elif p == p1:
                X1 = 0
                X2 = 1
            elif p == p2:
                X1 = 1
                X2 = 0
        return X1, X2
        


def test_naive_membership_attack(N, repeat_time = 10, mitigation = ""):
    # get the priced queries from file
    value_list = read_value_list_from_csv(f'./test_values/checked_values_{N}.csv')
    
    pricer_list = initialize_pricer()
    attacker = Attacker()
    
    # read the prepared price list from the csv file 
    if mitigation == "":
        price_list = pd.read_csv(f'./attack_pre_rs/membership_query_prices_{N}.csv')
    else:
        price_list = pd.read_csv(f'./attack_pre_rs/membership_query_prices_{mitigation}_prices_{N}.csv')
    print(len(value_list), len(price_list.values))
    rs = defaultdict(list)
    # compute the accuray of the naive membership attack
    for i, pricer in enumerate(pricer_list):
        cnt_1 = cnt_2 = cnt = 0
        # start to record the time
        start_time = time.time()
        for _ in range(repeat_time):
            for j, value in enumerate(value_list):
                flag = int(value[-3]) > 0
                if attacker.membership_attack_naive(value[-1], pricer, flag, price_list.values[j][i+1]) == flag:
                    cnt += 1
                else:
                    cnt_1 += 1
        end_time = time.time()
        cnt = cnt / repeat_time
        cnt_1 = cnt_1 / repeat_time
        cnt_2 = cnt_2 / repeat_time
        rs["Time"].append((end_time - start_time)/repeat_time/(len(value_list)))
        rs["Accuracy"].append(cnt/(len(value_list)))
        rs["Precision"].append(cnt/(cnt + cnt_1))
        rs["Recall"].append(cnt/(cnt + cnt_2))
        rs["F1"].append(2*rs["Precision"][-1]*rs["Recall"][-1]/(rs["Precision"][-1] + rs["Recall"][-1]))

    # write the dictionary into the csv
    df = pd.DataFrame(rs, index = ['PVPricer', 'QAPricer'])
    print(df)
    if mitigation == "":
        df.to_csv(f'./attack_rs/{database}_naive_membership_rs_{N}.csv')
    else:
        df.to_csv(f'./attack_rs/{database}_naive_membership_{mitigation}_rs_{N}.csv')


def test_limit_cardinality_attack(N, repeat_time = 10, mitigation = ""):
    # get the checked values from file
    value_list = read_value_list_from_csv(f'./test_values/checked_values_{N}.csv')
    non_value_list = []

    pricer_list = initialize_pricer()
    attacker = Attacker()
    rs = defaultdict(list)
    detail_rs = defaultdict(list)
    # compute the accuray of the naive membership attack
    for i, pricer in enumerate(pricer_list):
        n = len(value_list)
        # start to record the time
        MAE, MSE = 0, 0
        start_time = time.time()
        for _ in range(repeat_time):
            for j, value in enumerate(value_list):
                query, max_cardinality, real_cardinality = value[-1], int(value[-2]), int(value[-3])
                inferred_cardinality = attacker.cardinality_attack_limit(query, pricer, real_cardinality, max_cardinality)
                detail_rs[pricer.__class__.__name__].append([j, real_cardinality, inferred_cardinality])
                MAE += abs(inferred_cardinality - real_cardinality)
                MSE += (inferred_cardinality - real_cardinality)**2
            # for j, value in enumerate(non_value_list):
            #     query, max_cardinality, real_cardinality = value[-1], int(value[-2]), int(value[-3])
            #     inferred_cardinality = attacker.cardinality_attack_limit(query, pricer, real_cardinality, max_cardinality)
            #     detail_rs[pricer.__class__.__name__].append([j + n, real_cardinality, inferred_cardinality])
            #     MAE += abs(inferred_cardinality - real_cardinality)
            #     MSE += (inferred_cardinality - real_cardinality)**2
        end_time = time.time()
        MAE = MAE / repeat_time
        MSE = MSE / repeat_time
        # print(MAE, MSE)
        rs["Time"].append((end_time - start_time)/repeat_time/(len(value_list) + len(non_value_list)))
        rs["MAE"].append(MAE/(len(value_list) + len(non_value_list)))
        rs["MSE"].append(MSE/(len(value_list) + len(non_value_list)))
    # write the dictionary into the csv
    df = pd.DataFrame(rs, index = ['PVPricer', 'QAPricer'])
    print(df)
    df.to_csv(f'./attack_rs/{database}_limit_cardinality_rs_{N}.csv')

    df = pd.DataFrame(detail_rs)
    df.to_csv(f'./attack_rs/{database}_limit_cardinality_detail_rs_{N}.csv')


def test_having_cardinality_attack(N, repeat_time = 10, mitigation = ""):
    # get the checked values from file
    value_list = read_value_list_from_csv(f'./test_values/checked_values_{N}.csv')
    non_value_list = []
    # read_value_list_from_csv('./test_values/non_checked_values.csv')
    # print(len(value_list), len(non_value_list))
    pricer_list = initialize_pricer()
    pricer = pricer_list[1]
    attacker = Attacker()
    rs = defaultdict(list)
    detail_rs = defaultdict(list)
    # compute the accuray of the naive membership attack
    n = len(value_list)
    # start to record the time
    MAE, MSE = 0, 0
    start_time = time.time()
    for _ in range(repeat_time):
        for j, value in enumerate(value_list):
            query, max_cardinality, real_cardinality = value[-1], int(value[-2]), int(value[-3])
            inferred_cardinality = attacker.cardinality_attack_having(query, pricer, real_cardinality, max_cardinality)
            detail_rs[pricer.__class__.__name__].append([j, real_cardinality, inferred_cardinality])
            MAE += abs(inferred_cardinality - real_cardinality)
            MSE += (inferred_cardinality - real_cardinality)**2
        # for j, value in enumerate(non_value_list):
            # query, max_cardinality, real_cardinality = value[-1], int(value[-2]), int(value[-3])
            # inferred_cardinality = attacker.cardinality_attack_having(query, pricer, real_cardinality, max_cardinality)
            # detail_rs[pricer.__class__.__name__].append([j + n, real_cardinality, inferred_cardinality])
            # MAE += abs(inferred_cardinality - real_cardinality)
            MSE += (inferred_cardinality - real_cardinality)**2
    end_time = time.time()
    MAE = MAE / repeat_time
    MSE = MSE / repeat_time
    # print(MAE, MSE)
    rs["Time"].append((end_time - start_time)/repeat_time/(len(value_list) + len(non_value_list)))
    rs["MAE"].append(MAE/(len(value_list) + len(non_value_list)))
    rs["MSE"].append(MSE/(len(value_list) + len(non_value_list)))
    # write the dictionary into the csv
    df = pd.DataFrame(rs, index = ['QAPricer'])
    print(df)
    df.to_csv(f'./attack_rs/{database}_having_cardinality_rs_{N}.csv')

    df = pd.DataFrame(detail_rs)
    df.to_csv(f'./attack_rs/{database}_having_cardinality_detail_rs_{N}.csv')


def test_optimized_membership_attack(N, repeat_time = 10, mitigation = ""):
    # get the priced queries from file
    value_list = read_value_list_from_csv(f'./test_values/checked_values_{N}.csv')
    
    pricer_list = initialize_pricer()
    attacker = Attacker()
    
    # read the prepared price list from the csv file 
    if mitigation == "":
        price_list = pd.read_csv(f'./attack_pre_rs/membership_query_prices_{N}.csv')
    else:
        price_list = pd.read_csv(f'./attack_pre_rs/membership_query_prices_{mitigation}_prices_{N}.csv')
    print(len(value_list), len(price_list.values))
    rs = defaultdict(list)
    # compute the accuray of the optimized membership attack
    for i, pricer in enumerate(pricer_list):
        cnt_1 = cnt_2 = cnt = 0
        # start to record the time
        start_time = time.time()
        for _ in range(repeat_time):
            for j, value in enumerate(value_list):
                flag = int(value[-3]) > 0
                if attacker.membership_attack_optimized(value[-1], pricer, flag, price_list.values[j][i+1]) == flag:
                    cnt += 1
                else:
                    cnt_1 += 1
        end_time = time.time()
        cnt = cnt / repeat_time
        cnt_1 = cnt_1 / repeat_time
        cnt_2 = cnt_2 / repeat_time
        rs["Time"].append((end_time - start_time)/repeat_time/(len(value_list)))
        rs["Accuracy"].append(cnt/(len(value_list)))
        rs["Precision"].append(cnt/(cnt + cnt_1))
        rs["Recall"].append(cnt/(cnt + cnt_2))
        rs["F1"].append(2*rs["Precision"][-1]*rs["Recall"][-1]/(rs["Precision"][-1] + rs["Recall"][-1]))

    # write the dictionary into the csv
    df = pd.DataFrame(rs, index = ['PVPricer', 'QAPricer'])
    print(df)
    if mitigation == "":
        df.to_csv(f'./attack_rs/{database}_optimized_membership_rs_{N}.csv')
    else:
        df.to_csv(f'./attack_rs/{database}_optimized_membership_{mitigation}_rs_{N}.csv')



if __name__ == "__main__":
    N = 10000
    repeat_time = 10
    test_naive_membership_attack(N, repeat_time)
    test_limit_cardinality_attack(N, repeat_time)
    test_having_cardinality_attack(N, repeat_time)
    if "test_fixed_membership_attack" in globals():
        test_fixed_membership_attack(N, repeat_time)
    else:
        print("Skip test_fixed_membership_attack: function not defined.")

    test_naive_membership_attack(N, repeat_time, mitigation="PerPricer")
    test_limit_cardinality_attack(N, repeat_time, mitigation="PerPricer")
    test_having_cardinality_attack(N, repeat_time, mitigation="PerPricer")
    if "test_fixed_membership_attack" in globals():
        test_fixed_membership_attack(N, repeat_time, mitigation="PerPricer")
    else:
        print("Skip test_fixed_membership_attack with mitigation: function not defined.")
