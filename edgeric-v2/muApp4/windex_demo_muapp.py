import hydra
import numpy as np
import torch
import zmq
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# from neurwin_multi_threshold import NEURWIN
from trainers.core.ppo import ppo_train
from neurwin import NEURWIN
from stream_rl.registry import ENVS
from stream_rl.plots import visualize_neurwin_training, visualize_whittle_function, visualize_neurwin_ppo
import logging
import os
#from sanity_check import Environment
from omegaconf import open_dict
import socket 
import argparse
import time
import os
from edgeric_messenger import EdgericMessenger
log = logging.getLogger(__name__)

from stream_rl.plots import visualize_neurwin_training, visualize_whittle_function, visualize_neurwin_ppo
NUM_UES = 4
num_ues = 4

# Initialize the EdgericMessenger for weights
edgeric_messenger = EdgericMessenger(socket_type="weights")

# context = zmq.Context()
# print("zmq context created") 

# socket_send_action = context.socket(zmq.PUB)
# socket_send_action.bind("ipc:///tmp/socket_weights")

# socket_get_state = context.socket(zmq.SUB)
# socket_get_state.setsockopt(zmq.CONFLATE, 1)
# socket_get_state.connect("ipc:///tmp/socket_metrics")

# socket_get_state.setsockopt_string(zmq.SUBSCRIBE, "")

# #### Added by Archana ######
# context_RANID = zmq.Context()
# socket_send_RANID = context_RANID.socket(zmq.PUB)
# socket_send_RANID.bind("ipc:////tmp/socket_RANID")


ran_index = 0
curricid = 0
recvdricid = 0
f = 0
RNTIs = []
CQIs = []
BLs = []
txs = []
weight = np.zeros(num_ues*2)



import random

def get_whittle_action(indices): 
    action = {}

    # Sort the indices based on their values, in descending order
    sorted_indices = sorted(indices, key=indices.get, reverse=True)

    # Assign action 2 to the highest index (randomly if there are ties)
    top_indices = [index for index, value in indices.items() if value == indices[sorted_indices[0]]]
    selected_index_for_action_2 = random.choice(top_indices)
    action[selected_index_for_action_2] = 2

    # Exclude the index chosen for action 2
    remaining_indices = [i for i in sorted_indices if i != selected_index_for_action_2]

    # Assign action 1 to the next two highest indices (randomly if there are ties)
    if remaining_indices:
        second_highest_value = indices[remaining_indices[0]]
        second_top_indices = [index for index in remaining_indices if indices[index] == second_highest_value]
        selected_index_for_action_1 = random.choice(second_top_indices)

        #selected_indices_for_action_1 = second_top_indices[:2]
        
        action[selected_index_for_action_1] = 1
        remaining_indices.remove(selected_index_for_action_1)

    # Assign action 0 to all other indices
    for ue in remaining_indices:
        action[ue] = 0

    # Ensure all UEs are assigned an action, defaulting to 0 if not assigned yet
    for ue in range(NUM_UES):
        action.setdefault(ue, 0)

    return action



@hydra.main(config_path="conf", config_name="edge_ric_neurwin_ppo") #, version_base=None)
def main(conf):
    with open_dict(conf):
        conf["logger_name"] = __name__
    env_cls = {}
    env = {}
    agent = {}
    for ue in range(NUM_UES):
        env_cls[ue] = ENVS[conf["env"]]
        env[ue] = env_cls[ue](conf["env_config"])
        env[ue].r = ue_dict[ue]
        #Mu = conf["mu"]
        state_dim = env[ue].observation_space.shape[0]
        #print(state_dim)
        action_dim = env[ue].action_space.n
        hparams = {
        "HP_BATCHSIZE": conf["batch_size"],
        "HP_NUM_UNITS": conf["nn_size"],
        "HP_LEARNINGRATE": conf["lr"],
        "HP_OPTIMIZER": "Adam",
        }
        agent[ue] = NEURWIN(
        run_name="temp_",
        hparams=hparams,
        stateSize=state_dim,
        actionSize=action_dim,
        transformed_states=None,
        transformed_actions=None,
        env=env[ue],
        sigmoidParam=conf["sigmoidParam"],
        numEpisodes=conf["num_episodes"],
        noiseVar=None,
        seed=conf["training_seed"],
        discountFactor=conf["gamma"],
        saveDir="./output", #output_dir[ue],
        episodeSaveInterval=conf["save_interval"],
        logger=log,
        mu_r = 0,
        mu_l = 0
        )

        #iter = agent[ue].episodeRanges[-1]
        # directory[ue] = (
        # f"{agent[ue].directory}"
        # #+ f"/seed_{agent[ue].seed}_sigmoid_5_batchSize_{agent[ue].batchSize}_trainedNumEpisodes_20000"
        # )
        path = "./../../../trained_model_urllc.pt"
        agent[ue].nn.load_state_dict(torch.load(path))
        agent[ue].nn.eval()

    init_ranid = 60000
    count = 0
    ranid = 0

    #random.seed(42)
    violation_tpt_dict = {}
    violation_tsls_dict = {}
    tpt = {}
    for traj in range(5):
        #time.sleep(20)
        done = False
        state = {}
        indices = {}
        time_rr = 0
        tsls = {}
        avg_CQIs = {}
        gamma = 0.1
        reward = {}
        print("Traj loop")
        for ue in range(NUM_UES):
            state[ue] = env[ue].reset()
            tsls[ue] = 0
            avg_CQIs[ue] = 0
            reward[ue] = 0
        flag = False
        while flag:
            #RNTIs, CQIs, BLs, txs, ranid = get_metrics_multi()
            ran_tti, ue_data = edgeric_messenger.get_metrics(False)
            #if ranid == curr_ranid:
            if ranid == init_ranid-1:
                flag = False
                for i in range(len(RNTIs)):
                    weight[i*2+1] = 0.25
                    weight[i*2] = RNTIs[i]
                #send_scheduling_weight(weight, ranid, True)
                edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weight, False)
        done = False
        interval_burst = 0
        count = 0
        np.random.seed(42)
        prev_count = 0
        while not done:
            #print("debug: before get metrics")
            #ue_data = get_metrics_multi()
            ran_tti, ue_data = edgeric_messenger.get_metrics(False)
            print(ue_data)
            #RNTIs, CQIs, BLs, txs, ranid = get_metrics_multi()
            numues = len(ue_data)
            weight = np.zeros(numues * 2)
            # Extract CQIs and RNTIs and BLs from ue_data
            CQIs = [data['cqi'] for data in ue_data.values()]
            RNTIs = list(ue_data.keys())
            print(RNTIs)
            BLs = [data['dl_buffer'] for data in ue_data.values()]
            mbs = np.ones(numues)*300000 
            txb = [data['dl_tbs'] for data in ue_data.values()]   
            txs = np.sum(txb)  
            print("debug: after get metrics")
            print(BLs)
            if count % 10 == 0:
                #### send embb traffic
                data = b'\x00' * 6250  # Create a packet of the specified size
                embb_client.sendall(data)
                print(f"Sent {6250} bytes of data for embb")

                #### send xr traffic
                data = b'\x00' * 9535  # Create a packet of the specified size
                xr_client.sendall(data)
                print(f"Sent {9535} bytes of data for xr")
            if count == prev_count + interval_burst:
                ##### send urllc traffic
                #data = os.urandom(250000)
                data = b'\x00' * 250000
                urllc_client.sendall(data)
                print(f"Sent a burst of size {250000} in interval {interval_burst} for urllc")
                prev_count = count
                interval_burst = np.random.choice([500,1000,1500,2000],size=1)
            print("out of data generation")
            action = {}
            for i in range(len(RNTIs)):
                print(len(RNTIs))
                ue = list(ue_dict.keys())[list(ue_dict.values()).index(RNTIs[i])]
                action[ue] = 0
                state[ue], reward[ue], done, infactiono, allocated_rbg, _ = env[ue].step([ue], RNTIs[i], CQIs[i], BLs[i], txb[i])     # allocated_rbg, _
                if algo == "neurwin":
                    if BLs[i] == 0: 
                        indices[ue] = -100
                    else: 
                        s = [state[ue], [tsls[ue]/5000], [violation_tpt_picked[ue]], [violation_tsls_picked[ue]]]
                        s_0 = [item for sublist in s for item in sublist]
                        indices[ue] = agent[ue].nn.forward(s_0).detach().numpy()[0]
                        if ue == 2:
                            indices[ue] = indices[ue]*(1.4)
                if algo == "maxwt":
                    indices[ue] = BLs[i]*CQIs[i]
                elif algo == "propfair": 
                    avg_CQIs[ue] = avg_CQIs[ue]*(1-gamma) + CQIs[i]*(gamma)   
                    indices[ue] = CQIs[i]/avg_CQIs[ue] 
                elif algo == "maxCQI":  
                    indices[ue] = CQIs[i]
                elif algo == "roundrobin":
                    if ue != 3:
                        indices[ue] = 1 if ue == (time_rr % (NUM_UES-1)) else 0
                if ue == 3:
                    indices[ue] = -100
            time_rr = time_rr + 1
            flag_sendequal = False
            if all(value == -100 for value in indices.values()) == True:
                flag_sendequal = True
                action = {0:2, 1:2, 2:2, 3:0}
            else:
                action = get_whittle_action(indices) 
            print(action)
            for i in range(len(RNTIs)):
                ue = list(ue_dict.keys())[list(ue_dict.values()).index(RNTIs[i])]
                if ue == 3:
                    action[ue] = 0
                if action[ue] == 2:
                    weight[i*2+1] = 0.7
                    tsls[ue] = 0
                elif action[ue] == 1:
                    weight[i*2+1] = 0.1
                    tsls[ue] += 1 if BLs[i] != 0 else 0
                elif action[ue] == 0:
                    weight[i*2+1] = 0.1
                    tsls[ue] += 1 if BLs[i] != 0 else 0
                
                weight[i*2] = RNTIs[i]
    
                episode_reward[ue] += reward[ue]
                
                episodic_tsls[ue] += tsls[ue]
        
            if flag_sendequal == True:
                for i in range(len(RNTIs)):
                    ue = list(ue_dict.keys())[list(ue_dict.values()).index(RNTIs[i])]
                    if ue != 3:
                        weight[i*2+1] = 0.3
                        tsls[ue] = 0
                    else:
                        weight[i*2+1] = 0.1
                        tsls[ue] = 0

            #send_scheduling_weight(weight, True)
            edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weight, False)
            count = count + 1
        
    for ue in range(NUM_UES):
        episode_reward[ue] /= 5
        episodic_tsls[ue] /= 25000   
        tpt[ue] = episode_reward[ue]
        violation_tpt[ue] = ((p[ue]*B[ue])-episode_reward[ue])
        violation_tsls[ue] = episodic_tsls[ue] - lastservice[ue]
        violation_tpt_dict[f"UE{ue}"] = violation_tpt[ue]
        violation_tsls_dict[f"UE{ue}"] = violation_tsls[ue]  

        episode_reward[ue] = 0
        episode_reward[ue] = 0
        violation_tpt[ue] = 0
        violation_tsls[ue] = 0
        episodic_tsls[ue] = 0.0    
    if algo == "maxwt" or algo == "maxCQI" or algo == "propfair" or algo == "roundrobin":
        filefortraditional.write(f"throughput: {tpt}\n")
        filefortraditional.write(f"Violation_TPT: {violation_tpt_dict}\n")
        filefortraditional.write(f"Violation_TSLS: {violation_tsls_dict}\n")
        filefortraditional.write("\n")
        filefortraditional.flush()  # Flush the internal buffer to the OS buffer
        os.fsync(filefortraditional.fileno())
    
    else:
        file.write(f"avg throughput: {tpt}\n")
        file.write(f"avg Violation_TPT: {violation_tpt_dict}\n")
        file.write(f"avg Violation_TSLS: {violation_tsls_dict}\n")
        file.write("\n")
        file.flush()  # Flush the internal buffer to the OS buffer
        os.fsync(file.fileno())  # Ensure OS buffer is written to disk


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="embb Client")
    parser.add_argument('--embbport', type=int, default=12345, help='Port Number')
    parser.add_argument('--urllcport', type=int, default=12345, help='Port Number')
    parser.add_argument('--xrport', type=int, default=12345, help='Port Number')
    args = parser.parse_args()

    loaders = []
    ue_dict = {0: 17923, 1: 17924, 2: 17921, 3: 17922}

    print("client socket connection starting")

    embb_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    embb_client.connect(('10.45.0.2', args.embbport))

    print("clients connected")

    urllc_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    urllc_client.connect(('10.45.0.3', args.urllcport))

    xr_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    xr_client.connect(('10.45.0.4', args.xrport))

   

    
    file = open("./output/neurwin_trace.txt", "a")
    filefortraditional = open("./output/traditional_trace_archana.txt", "a")
    p = {0: 0.90, 1: 0.90, 2: 0.90, 3: 0.90}
    B = {0:3001.817666666539, 1: 894.1566666666675, 2: 4284.159999999739, 3: 0} #trace1
    lastservice = {0: 10, 1: 2, 2: 2, 3: 2}
    violation_tpt_picked = {}
    violation_tsls_picked = {}
    index_tpt = {}
    index_tsls = {}
    for ue in range(NUM_UES):
        index_tpt[ue] = 0
        index_tsls[ue] = 0
        if ue == 0:
            violation_tpt_picked[ue] =  0.5  
            violation_tsls_picked[ue] =  0.5
        if ue == 1:
            violation_tpt_picked[ue] = 0 
            violation_tsls_picked[ue] = 0.61161778
        if ue == 2:
            violation_tpt_picked[ue] =  0  
            violation_tsls_picked[ue] = 0.008559453333
        if ue == 3:
            violation_tpt_picked[ue] =  0 
            violation_tsls_picked[ue] = 0

    violation_tsls = {} 
    violation_tpt = {}
    episode_reward = {}
    episodic_tsls = {}
    Mu_r = {}
    Mu_l = {}
    lr = {}
    output_dir = {}
    directory = {}
    
    # for ue, identifier in ue_dict.items():
    #     if ue == 0:
    #         output_dir[ue] = "/home/wcsng-24/gitrepos/EdgeRIC_whittleIndex/EdgeRIC_rl_emulator/trained-models/neurwin-models/NewModels/embb"
    #         lr[ue] = 0.1
            
    #     elif ue == 1:
    #         output_dir[ue] = "/home/wcsng-24/gitrepos/EdgeRIC_whittleIndex/EdgeRIC_rl_emulator/trained-models/neurwin-models/NewModels/urllc"
    #         lr[ue] = 0.75

    #     elif ue == 2:
    #         output_dir[ue] = "/home/wcsng-24/gitrepos/EdgeRIC_whittleIndex/EdgeRIC_rl_emulator/trained-models/neurwin-models/NewModels/embb"
    #         lr[ue] = 0.1

    #     elif ue == 3:
    #         output_dir[ue] = "/home/wcsng-24/gitrepos/EdgeRIC_whittleIndex/EdgeRIC_rl_emulator/trained-models/neurwin-models/NewModels/urllc"
    #         lr[ue] = 0.75

                    
    for ue in range(NUM_UES):
        episode_reward[ue] = 0
        episode_reward[ue] = 0
        violation_tpt[ue] = 0
        violation_tsls[ue] = 0
        episodic_tsls[ue] = 0.0
    results = [] 
    algos = ["neurwin"] #["maxwt", "maxCQI", "propfair", "roundrobin", "neurwin"]
    violation_tpt_dict = {}
    violation_tsls_dict = {}
    
    for algorithm in algos:
        algo = algorithm
        if algo != "neurwin":
            filefortraditional.write(algo)
            filefortraditional.write("\n")
        else:
            file.write(algo)
            file.write("\n")
        for ue, identifier in ue_dict.items():
            episode_reward[ue] = 0
            violation_tpt[ue] = 0
            violation_tsls[ue] = 0
            episodic_tsls[ue] = 0.0 

        main()
        print("violaition tpt")
        
    file.close() 
    #filefortraditional.close()

    embb_client.close()
    urllc_client.close()
    xr_client.close()
