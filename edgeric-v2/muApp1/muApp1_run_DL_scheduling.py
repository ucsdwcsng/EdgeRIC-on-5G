import json
import argparse
import os
import pickle
import sys
from collections import defaultdict
from datetime import datetime
from threading import Thread
import numpy as np

import gym
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import math
import time

import torch
import redis
from edgeric_messenger import EdgericMessenger

import models.mlp_policy

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)

total_brate = []
avg_CQIs  = []

# Initialize the EdgericMessenger for weights
edgeric_messenger = EdgericMessenger(socket_type="weights")

def eval_loop_weight(eval_episodes, idx_algo):
    
    key_index = 0
    global avg_CQIs
    avg_CQIs = np.zeros(2)
    rr_cnt = 0
    
    for i_episode in range(eval_episodes):
        cnt = 0
        flag = True
        cnt_demo = 0
        key_algo = "algo"
        value_algo = "Half resource for each UE" # default algorithm
   
        if(idx_algo == 0):
            flag = False # to be deleted
            weights = fixed_weights()
            edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weights, False)
            value_algo = "Fixed Weights"

        # algo1 Max CQI       
        if(idx_algo == 1):
            weights = algo1_maxCQI_multi()
            edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weights, False)
            value_algo = "MaxCQI"
    
        # algo2 Max Weight
        if(idx_algo == 2):
            weights = algo2_maxWeight_multi()
            edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weights, False)
            value_algo = "MaxWeight"
        
        # algo3 PropFair
        if(idx_algo == 3):
            weights, average_cqis = algo3_propFair_multi(avg_CQIs)
            avg_CQIs = average_cqis 
            edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weights, False)
            value_algo = "Proportional Fairness"

        # algo4 RoundRobin
        if(idx_algo == 4):
            weights = algo4_roundrobin_multi(rr_cnt)
            edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weights, False)
            rr_cnt = rr_cnt + 1
            value_algo = "Round Robin"

        if(flag == True):
            cnt = 0
            flag = False  

    #redis_db.set(key_algo, value_algo)   

def fixed_weights():
    global total_brate
    ran_tti, ue_data = edgeric_messenger.get_metrics(False)
    numues = len(ue_data)
    weights = np.zeros(numues * 2)
    RNTIs = list(ue_data.keys())
    txb = [data['tx_bytes'] for data in ue_data.values()]
    brate = np.sum(txb)
    total_brate.append(brate)

    for i in range(numues):
        weights[i*2+0] = RNTIs[i]
        weights[i*2+1] = 0.3 if i == 0 else 0.7 if i == 1 else 1/numues
    
    return weights

                
def algo1_maxCQI_multi():
    global total_brate
    ran_tti, ue_data = edgeric_messenger.get_metrics(False)
    numues = len(ue_data)
    weights = np.zeros(numues * 2)

    CQIs = [data['cqi'] for data in ue_data.values()]
    RNTIs = list(ue_data.keys())
    txb = [data['tx_bytes'] for data in ue_data.values()]
    brate = np.sum(txb)
    total_brate.append(brate)

    if min(CQIs) > 0:  # Check if all CQIs are positive
        maxIndex = np.argmax(CQIs)
        new_weights = np.zeros(numues)
        
        high = 1 - ((numues - 1) * 0.1)
        low = 0.1
        for i in range(numues):
            if i == maxIndex:
                new_weights[i] = high
            else:
                new_weights[i] = low
            
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = new_weights[i]
        
        return weights
        
    else:  
        for i in range(numues):
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = 1/numues
        
        return weights

def algo2_maxWeight_multi():
    global total_brate
    ran_tti, ue_data = edgeric_messenger.get_metrics(False)
    numues = len(ue_data)
    weights = np.zeros(numues * 2)

    CQIs = [data['cqi'] for data in ue_data.values()]
    RNTIs = list(ue_data.keys())
    BLs = [data['ul_buffer'] for data in ue_data.values()]
    txb = [data['tx_bytes'] for data in ue_data.values()]
    brate = np.sum(txb)
    total_brate.append(brate)

    if min(CQIs) > 0: 
        sum_CQI = np.sum(CQIs)
        sum_BL = np.sum(BLs) 
        if sum_BL != 0:
            new_weights = CQIs/sum_CQI * BLs/sum_BL
        else:
            new_weights = CQIs/sum_CQI
   
        for i in range(numues):
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = new_weights[i]
    
    else:  
        for i in range(numues):
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = 1/numues
    
    return weights 

def algo3_propFair_multi(avg_CQIs):
    global total_brate
    ran_tti, ue_data = edgeric_messenger.get_metrics(False)
    numues = len(ue_data)
    weights = np.zeros(numues * 2)

    CQIs = [data['cqi'] for data in ue_data.values()]
    RNTIs = list(ue_data.keys())
    BLs = [data['ul_buffer'] for data in ue_data.values()]
    txb = [data['tx_bytes'] for data in ue_data.values()]
    brate = np.sum(txb)
    total_brate.append(brate)

    if min(CQIs) > 0: 
        gamma = 0.1 
        avg_CQIs = np.array(avg_CQIs)
        CQIs = np.array(CQIs)
        avg_CQIs = avg_CQIs*(1-gamma) + CQIs*(gamma)
        
        temp_weights = CQIs / avg_CQIs 
        new_weights = np.round(temp_weights / np.sum(temp_weights), 2)

        for i in range(numues):
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = new_weights[i]
        
    else:
        for i in range(numues):
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = 1/numues

    return weights, avg_CQIs

def algo4_roundrobin_multi(rr_cnt):
    global total_brate
    ran_tti, ue_data = edgeric_messenger.get_metrics(False)
    numues = len(ue_data)
    weights = np.zeros(numues * 2)

    CQIs = [data['cqi'] for data in ue_data.values()]
    RNTIs = list(ue_data.keys())
    txb = [data['tx_bytes'] for data in ue_data.values()]
    brate = np.sum(txb)
    total_brate.append(brate)
    index = rr_cnt % numues
    rr_cnt += 1

    if min(CQIs) > 0:  # Check if all CQIs are positive
        new_weights = np.zeros(numues)
        
        high = 1 - ((numues - 1) * 0.1)
        low = 0.1
        for i in range(numues):
            if i == index:
                new_weights[i] = high
            else:
                new_weights[i] = low
            
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = new_weights[i]
        
        return weights
        
    else:  
        for i in range(numues):
            weights[i*2+0] = RNTIs[i]
            weights[i*2+1] = 1/numues
        
        return weights

def eval_loop_model(num_episodes, out_dir):
    output_dir = out_dir 
    global total_brate
    # torch.serialization.add_safe_globals([Policy])
    #model = torch.load(os.path.join(output_dir, "model_demo.pt"), map_location=torch.device('cpu'))


    model = torch.load(os.path.join(output_dir, "model_demo.pt"), map_location=torch.device('cpu'), weights_only=False)
    torch.serialization.add_safe_globals([models.mlp_policy.Policy])

    model.eval()

    for episode in range(num_episodes):
        ran_tti, ue_data = edgeric_messenger.get_metrics(False)
        numues = len(ue_data)
        weight = np.zeros(numues * 2)

        CQIs = [data['cqi'] for data in ue_data.values()]
        RNTIs = list(ue_data.keys())
        BLs = [data['dl_buffer'] for data in ue_data.values()]
        mbs = np.ones(numues) * 300000
        txb = [data['tx_bytes'] for data in ue_data.values()]
        brate = np.sum(txb)
        total_brate.append(brate)

        obs = np.array(
            [
                param[ue]
                for ue in range(numues)
                for param in (BLs, CQIs, mbs)
            ],
            dtype=np.float32,
        )  # [BL1, CQI1, BL2, CQI2,.....]
            
        obs = torch.from_numpy(obs)
        obs = torch.unsqueeze(obs, dim=0)
            
        with torch.no_grad():
            action = model.select_action(obs)
            action = torch.squeeze(action)

        ue_data['percentage_RBG'] = np.zeros(numues)
        ue_data['weight'] = np.zeros(numues*2)
        for ue in range(numues):
            percentage_RBG = action[ue] / sum(action)
            ue_data['percentage_RBG'][ue] = percentage_RBG.numpy()
            weight[ue*2+1] = percentage_RBG
            ue_data['weight'][ue*2+1] = weight[ue*2+1]
            weight[ue*2] = RNTIs[ue]
            ue_data['weight'][ue*2] = weight[ue*2]

        edgeric_messenger.send_scheduling_weight(ran_tti, weight, False)

        ue_data['obs'] = list(obs[0].data.numpy())
        ue_data['action'] = list(action.numpy())

        ari_data_dict_rl['data'].append(ue_data)

    with open('test_dict_rl.json', 'w') as f:
        # None
        # f.write('{'+str(ue_dict)+'},'+'\n')
        # dic = json.load(f)
        # dic.update(ue_dict)
        # dic['data'].append(ue_dict)
        json.dump(ari_data_dict_rl, f, indent=2, cls=MyEncoder)


#################
algorithm_mapping = {
    "Fixed Weight": 0,
    "Max CQI": 1,
    "Max Weight": 2,
    "Proportional Fair": 3,
    "Round Robin": 4,
    "RL": 20  # Adjust according to your specific algorithms and indices
}

rl_model_mapping = {
    "Initial Model": "./rl_model/initial_model",
    "Half Trained Model": "./rl_model/half_trained_model",
    "Fully Trained Model": "./rl_model/fully_trained_model"
}

# Establish a Redis connection (assuming Redis server is running locally)
redis_db = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

if __name__ == "__main__":
    ari_data_dict_rl = {'data': []}
    try:
        while True:
            try:
                selected_algorithm = redis_db.get('scheduling_algorithm')
                if selected_algorithm:
                    idx_algo = algorithm_mapping.get(selected_algorithm, None)

                    if idx_algo is not None:
                        print("Algorithm index: ", idx_algo, " , ", selected_algorithm)
                        if idx_algo < 20:
                            eval_loop_weight(1000, idx_algo)  # For traditional scheduling algorithms
                            print(f"total system throughput: {np.mean(total_brate)*8/1000} \n") 
                            total_brate.clear()
                        elif idx_algo == 20:  # For RL model execution
                            rl_model_name = "Fully Trained Model"
                            if rl_model_name:
                                rl_model_path = rl_model_mapping.get(rl_model_name)
                                if rl_model_path:
                                    print(f"Executing RL model at: {rl_model_path}")
                                    eval_loop_model(1000, rl_model_path)
                                    print(f"total system throughput: {np.mean(total_brate)*8/1000} \n") 
                                    total_brate.clear()
                                else:
                                    print(f"Unknown RL model selected: {rl_model_name}")
                            else:
                                print("No RL model selected or RL model key does not exist in Redis.")
                    else:
                        print("Unknown algorithm selected:", selected_algorithm)
                else:
                    print("No algorithm selected or algorithm key does not exist in Redis.")
                    
            except redis.exceptions.RedisError as e:
                print("Redis error:", e)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting gracefully.")
