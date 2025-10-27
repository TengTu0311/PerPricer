from generate_checked_values import *
import numpy as np
def naive_attack_to_guess_extreme_value(N = 100):
    print(database)
    if database  == 'ssb1g':
        query = 'select * from lineorder where lo_revneue '
        attribute_range = [0, 1500 * 10000]
        real_range = [81360,  10474950]
        qa_real_range = [81540, 10474950]
    elif database == 'tpch1g':
        query = 'select * from order where o_totalprice '
        attribute_range = [0, 1e+7]
        real_range = [857.71,  555285.16]
        qa_real_range = [857.71, 555590.57]
    elif database == 'employment':
        query = 'select * from employment where employees '
        attribute_range = [0, 2e+9]
        real_range = [11200,  153177000]
        # 153177000 |          11200
        qa_real_range = [11200, 1956903796.7534354]
        # 1956903796.7534354 11200
    all_rs = []
    pricer_list = initialize_pricer()
    for pricer in pricer_list:
        if isinstance(pricer, QAPricer):
            used_min, used_max = qa_real_range 
        else:
            used_min, used_max = real_range
        guess_min_left, guess_min_right = attribute_range
        guess_max_left, guess_max_right = attribute_range
        rs = []
        for i in range(N+1):
            rs.append([abs(guess_min_left - real_range[0]), abs(guess_max_right - real_range[1])])
            # guess min 
            guess_min = (guess_min_left + guess_min_right)/2
            if guess_min > used_min:
                guess_min_right = guess_min
            else:
                guess_min_left = guess_min
            # guess max 
            guess_max = (guess_max_left + guess_max_right)/2
            if guess_max < used_max:
                guess_max_left = guess_max
            else:
                guess_max_right = guess_max
            
            # if N % 100 == 0:
            # print(guess_min, guess_max, used_max, used_min)
            # print(i, guess_max_left, guess_max_right, guess_max, used_max, abs(guess_max - real_range[1]))
            # rs.append([abs(guess_min_left - real_range[0]), abs(guess_max_right - real_range[1])])
        all_rs.append(rs)
    result = np.concatenate((all_rs[0], all_rs[1]), axis=1)
    df = pd.DataFrame(result, columns=['Naive-PBP-Min', 'Naive-PBP-Max' , 'Naive-QIRANA-Min', 'Naive-QIRANA-Max'], index = range(N+1))
    df.to_csv(f'./attack_rs/naive_attack_to_guess_extreme_value_detail_rs_{N}.csv')
    rows_to_select = [0, 1, 3, 5, 10, 20, 40, 100]
    new_df = df.iloc[rows_to_select]
    new_df.to_csv(f'./attack_rs/naive_attack_to_guess_extreme_value_rs_{N}.csv')

    def f(x):
        if database == 'tpch1g':
            tmp = [0, 310, 1e+3, 1e+6, 1e+7, 1e+8]
        elif database == 'ssb1g':
            tmp = [0, 400, 1000, 1e+4, 1e+6, 1e+8]
        elif database == 'employment':
            tmp = [0, 1000, 1e+4, 1e+6, 1e+8, 1e+9]
        for i in range(1, len(tmp)):
            if x <= tmp[i]:
                return i - 1 + (x - tmp[i-1])/(tmp[i] - tmp[i-1])
        return len(tmp)
    processed_rs = new_df.applymap(f)
    processed_rs.to_csv(f'./attack_rs/naive_attack_to_guess_extreme_value_processed_rs_{N}.csv')
    return rs

print(database)
naive_attack_to_guess_extreme_value()
    

    