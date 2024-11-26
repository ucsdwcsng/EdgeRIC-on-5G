# -*- coding: utf-8 -*-
"""
@author: vamsi tallam
"""

import pandas as pd
import random

option = 5

"""
time     = 10
time_min = time
time_sec = time_min * 60
time_ms  = time_sec * 1000
"""

if option == 1:
    # cqi varies from 1 to 15 and goes from 15 to 1
    cqi1_low = 1
    cqi1_high = 15
    cqi2_low = 1
    cqi2_high = 15
    cqi3_low = 1
    cqi3_high = 15
    cqi4_low = 1
    cqi4_high = 15
    cqi_evol_freq = 2
    len_ = 1000

    cqi1 = []
    cqi2 = []
    cqi3 = []
    cqi4 = []
    for i in range(len_):
        j = 1000 - i
        for _ in range(cqi_evol_freq):
            cqi1.append((i % 15) + 1)
            cqi2.append((j % 15) + 1)
            cqi3.append(((i + 9) % 15) + 1)
            cqi4.append(((j + 9) % 15) + 1)

    data = pd.concat(
        [pd.Series(cqi1), pd.Series(cqi2), pd.Series(cqi3), pd.Series(cqi4)], axis=1
    )
    data.to_csv("data_4UE.csv", header=True, index=False)


if option == 2:
    # constant cqi for ue1 and ue2 respectively
    fixed_cqi1 = 9
    fixed_cqi2 = 9
    len_ = 1000

    cqi1 = pd.Series([fixed_cqi1 for _ in range(len_)])
    cqi2 = pd.Series([fixed_cqi2 for _ in range(len_)])

    data = pd.concat([cqi1, cqi2], axis=1)
    data.to_csv("data_const.csv", header=True, index=False)


if option == 3:
    # cqi varies in a given range
    cqi1_low = 8
    cqi1_high = 15
    cqi2_low = 1
    cqi2_high = 7
    cqi_evol_freq = 1
    len_ = 1000

    cqi1 = []
    cqi_range = 2 * (cqi1_high - cqi1_low) + 1
    for i in range(len_):
        if i % cqi_range >= 0 and i % cqi_range <= (cqi1_high - cqi1_low):
            for _ in range(cqi_evol_freq):
                cqi1.append(cqi1_low + i % cqi_range)
        elif i % cqi_range > (cqi1_high - cqi1_low) and i % cqi_range < cqi_range:
            for _ in range(cqi_evol_freq):
                cqi1.append(cqi1_high - (i % cqi_range - (cqi1_high - cqi1_low)))

    cqi2 = []
    cqi_range = 2 * (cqi2_high - cqi2_low) + 1
    for i in range(len_):
        if i % cqi_range >= 0 and i % cqi_range <= (cqi2_high - cqi2_low):
            for _ in range(cqi_evol_freq):
                cqi2.append(cqi2_low + i % cqi_range)
        elif i % cqi_range > (cqi2_high - cqi2_low) and i % cqi_range < cqi_range:
            for _ in range(cqi_evol_freq):
                cqi2.append(cqi2_high - (i % cqi_range - (cqi2_high - cqi2_low)))

    data = pd.concat([pd.Series(cqi1), pd.Series(cqi2)], axis=1)
    data.to_csv("data.csv", header=True, index=False)


if option == 4:
    # random cqi for ue1 and ue2 respectively
    cqi1_low = 1
    cqi1_high = 15
    cqi2_low = 1
    cqi2_high = 15
    len_ = 1000000

    cqi1 = pd.Series([random.randint(cqi1_low, cqi1_high) for _ in range(len_)])
    cqi2 = pd.Series([random.randint(cqi2_low, cqi2_high) for _ in range(len_)])

    data = pd.concat([cqi1, cqi2], axis=1)
    data.to_csv("data_random.csv", header=True, index=False)


if option == 5:
    # random walk cqi varies in a given range
    cqi1_low = 8
    cqi1_high = 8
    cqi1_walk = 1
    # cqi2_low = 1
    # cqi2_high = 15
    # cqi2_walk = 3
    # cqi3_low = 1
    # cqi3_high = 15
    # cqi3_walk = 3
    # cqi4_low = 1
    # cqi4_high = 15
    # cqi4_walk = 3
    cqi_evol_freq = 2
    len_ = 100000

    cqi1 = []
    cqi = cqi1_low
    cqi1.append(cqi)
    for i in range(len_):
        curr_cqi = cqi + random.randint(cqi1_walk * -1, cqi1_walk)
        if curr_cqi <= cqi1_low:
            cqi = cqi1_low
            for _ in range(cqi_evol_freq):
                cqi1.append(cqi)
        elif curr_cqi >= cqi1_high:
            cqi = cqi1_high
            for _ in range(cqi_evol_freq):
                cqi1.append(cqi)
        else:
            cqi = curr_cqi
            for _ in range(cqi_evol_freq):
                cqi1.append(cqi)

    # cqi2 = []
    # cqi = cqi2_low
    # cqi2.append(cqi)
    # for i in range(len_):
    #     curr_cqi = cqi + random.randint(cqi2_walk * -1, cqi2_walk)
    #     if curr_cqi <= cqi2_low:
    #         cqi = cqi2_low
    #         for _ in range(cqi_evol_freq):
    #             cqi2.append(cqi)
    #     elif curr_cqi >= cqi2_high:
    #         cqi = cqi2_high
    #         for _ in range(cqi_evol_freq):
    #             cqi2.append(cqi)
    #     else:
    #         cqi = curr_cqi
    #         for _ in range(cqi_evol_freq):
    #             cqi2.append(cqi)

    # cqi3 = []
    # cqi = cqi3_low
    # cqi3.append(cqi)
    # for i in range(len_):
    #     curr_cqi = cqi + random.randint(cqi3_walk * -1, cqi3_walk)
    #     if curr_cqi <= cqi3_low:
    #         cqi = cqi3_low
    #         for _ in range(cqi_evol_freq):
    #             cqi3.append(cqi)
    #     elif curr_cqi >= cqi3_high:
    #         cqi = cqi3_high
    #         for _ in range(cqi_evol_freq):
    #             cqi3.append(cqi)
    #     else:
    #         cqi = curr_cqi
    #         for _ in range(cqi_evol_freq):
    #             cqi3.append(cqi)

    # cqi4 = []
    # cqi = cqi4_low
    # cqi4.append(cqi)
    # for i in range(len_):
    #     curr_cqi = cqi + random.randint(cqi4_walk * -1, cqi4_walk)
    #     if curr_cqi <= cqi4_low:
    #         cqi = cqi4_low
    #         for _ in range(cqi_evol_freq):
    #             cqi4.append(cqi)
    #     elif curr_cqi >= cqi4_high:
    #         cqi = cqi4_high
    #         for _ in range(cqi_evol_freq):
    #             cqi4.append(cqi)
    #     else:
    #         cqi = curr_cqi
    #         for _ in range(cqi_evol_freq):
    #             cqi4.append(cqi)

    data = pd.concat(
        [pd.Series(cqi1)], axis=1
    )  # pd.Series(cqi2), pd.Series(cqi3), pd.Series(cqi4)], axis=1)
    data.to_csv("data_const_cqi.csv", header=True, index=False)
