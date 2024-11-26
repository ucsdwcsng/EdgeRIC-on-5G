import numpy as np
import pandas as pd
import torch
import gym
from gym.spaces import MultiDiscrete, Box, Discrete
from stream_rl.registry import register_env, create_reward
from ray.rllib.env.env_context import EnvContext
from collections import deque
import random
import zmq
import time
import sys

gym.logger.set_level(40)


@register_env("EdgeRIC")
class EdgeRIC(gym.Env):
    """EdgeRIC Env: Simulation of the realtime RIC setup"""

    def __init__(self, config: EnvContext):
        self.seed = config["seed"]
        self.app = config["app"] 
        if self.seed != -1:
            random.seed(self.seed)
            np.random.seed(self.seed)
        self.T = config["T"]
        self.r = 70
        self.t = None
        self.num_UEs = config["num_UEs"]
        self.numArms = 2 #config["num_UEs"]
        self.RNTIs = np.zeros(self.numArms)
        self.numParams = 3
        self.total_rbgs = config["num_RBGs"]
        self.cqi_map = config["cqi_map"]
        self.augment_state_space = config["augment_state_space"]

        # Delay mechanism
        self.state_delay = config["delay_state"]
        self.action_delay = config["delay_action"]
        self.state_history = deque(
            [np.array([0, 1] * self.num_UEs, dtype=np.float32)]
            * (self.state_delay + 1),
            maxlen=self.state_delay + 1,
        )
        if self.augment_state_space:
            self.state_history = deque(
                [np.array([0, 1, 0] * self.num_UEs, dtype=np.float32)]
                * (self.state_delay + 1),
                maxlen=self.state_delay + 1,
            )
        self.action_history = deque(
            [np.zeros(shape=(self.num_UEs,), dtype=np.float32)]
            * (self.action_delay + 1),
            maxlen=self.action_delay + 1,
        )
        # print(self.action_history)
        # a=input("check")

        # Backlog Buffer Elements
        self.max_len_backlog = int(config["base_station"]["max_len"])
        self.backlog_lens = []
        self.backlog_population_params = config["backlog_population"]
        if (
            len(self.backlog_population_params) != self.num_UEs
        ):  # same params to all UEs backlog population
            self.backlog_population_params = [
                self.backlog_population_params
            ] * self.num_UEs

        # CQI Elements
        self.cqis = []
        #self.cqi_traces = [
        #    pd.read_csv(config["cqi_traces"][ue]).squeeze().tolist()
        #    for ue in range(self.num_UEs)
        #]
        #self.cqi_timesteps = [None] * self.num_UEs

        # Action and Observation Space Definitions
        self.action_space_type = config["action_space_type"]
        if self.action_space_type == "continuous":
            self.action_space = Box(
                low=0.0, high=1.0, shape=(self.num_UEs,), dtype=np.float32
            )
        elif self.action_space_type == "discrete":
            self.action_space = Discrete(config["num_RBGs"])
            assert (
                self.num_UEs == 1
            ), "Whittle learning supoported for only one UE currently!!"
        elif self.action_space_type == "binary":
            #self.action_space = Discrete(2)
            self.action_space = Discrete(3)
            self.binary_high_RBGs = config["binary_high_RBGs"]
            self.binary_low_RBGs = config["binary_low_RBGs"]
            self.binary_zero_RBGs = config["binary_zero_RBGs"]
            self.num_RBGs = config["num_RBGs"]
        self.cost_high_action = config["cost_high_action"]
        # assert (
        #     self.num_UEs == 1
        # ), "Whittle learning supoported for only one UE currently!!"
        self.num_state_variables = 2
        self.observation_space = Box(
            low=np.array([0, 1] * self.num_UEs),
            high=np.array([self.max_len_backlog, 15] * self.num_UEs),
            dtype=np.float32,
        )
        if self.augment_state_space:
            self.num_state_variables = 3
            self.observation_space = Box(
                low=np.array([0, 1, 0] * self.num_UEs),
                high=np.array(
                    [self.max_len_backlog, 15, 15 * self.max_len_backlog] * self.num_UEs
                ),
                dtype=np.float32,
            )

        self.normalize_state_space = config["normalize_state_space"]
        self.normalizer = (
            (
                np.array(
                    [
                        self.max_len_backlog ,
                        15,
                        self.max_len_backlog * 15,
                    ]
                    * self.num_UEs,
                    dtype=np.float32,
                )
                if self.augment_state_space
                else np.array(
                    [
                        self.max_len_backlog,
                        15,
                    ]
                    * self.num_UEs,
                    dtype=np.float32,
                )
            )
            if self.normalize_state_space
            else 1
        )

        self.reward_func = create_reward(config["reward"])
        self.observation_space.seed(self.seed)
        self.tsls = 0

        # zmq parameters
        self.context = zmq.Context()
        print("zmq context created") 

        self.socket_send_action = self.context.socket(zmq.PUB)
        self.socket_send_action.bind("ipc:///tmp/socket_weights")

        #self.socket_send_action2 = self.context.socket(zmq.PUB)
        #self.socket_send_action2.bind("ipc:///tmp/socket_checking")

        # for subbing state
        #int conflate = 1
        self.socket_get_state = self.context.socket(zmq.SUB)
        self.socket_get_state.setsockopt(zmq.CONFLATE, 1)
        self.socket_get_state.connect("ipc:///tmp/socket_metrics")
        
        self.socket_get_state.setsockopt_string(zmq.SUBSCRIBE, "")


        self.ran_index = 0
        self.curricid = 0
        self.recvdricid = 0
        self.f = 0
        self.f_seq = open("edgeric_seq_2.txt","w")
        self.f_seq_4 = open("edgeric_seq_4.txt","w")

        self.queue_metrics = []
        self.delay_metrics = 0
        self.maxdelay_metrics = 0
        self.queue_weights = []
        self.delay_weights = 0
        self.maxdelay_weights = 0

        self.wts = np.zeros(self.numArms*2)

    def reset(self):
        self.t = 0
        self.tsls = 0
        self.ran_index = 0
        self.curricid = 0
        self.recvdricid = 0
        self.f = 0

        self.backlog_lens = [0] * self.num_UEs
        self.cqis = [1] * self.num_UEs

        '''
        self.cqi_timesteps = [
            random.randint(0, len(self.cqi_traces[ue]) - 1)
            for ue in range(self.num_UEs)
        ]
        self.cqis = [
            self.cqi_traces[ue][self.cqi_timesteps[ue]] for ue in range(self.num_UEs)
        ]
        self.back_pressures = [
            cqi * backlog_len for cqi, backlog_len in zip(self.cqis, self.backlog_lens)
        ]
        '''
        if self.augment_state_space:
            init_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis, self.back_pressures)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, BP1, BL2, CQI2, BP2.....]
        else:
            init_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, BL2, CQI2,.....]

        self.state_history.append(init_state)
        # print(f"sate history:{self.state_history}")

        # print(f"s0 = {(self.state_history[0] / self.normalizer)}")
        return self.state_history[0] / self.normalizer

    def step(self, action, RNTI, CQI, BL, tx):
        """Order of operations within a step - transfers from :
        1.) Backlog buffer to playback buffer
        2.) Cloud to backlog buffer
        """
        #print("RNTI, CQI, BL: " + str(RNTI) + str(CQI) + str(BL))

        #rntitrain = RNTI
        # print(f"\n\nstate of system at start of time {self.t+1}\n {self.backlog_lens}, {self.cqis}")
        # print(f"action recommended by agent:{action}")
        # Add delay to action
        self.action_history.append(action)
        action = self.action_history[0]
        print("action is: " + str(action))
        #print(action)
        if self.action_space_type == "continuous":
            action = np.clip(
                action, a_min=0.00000001, a_max=1.0
            )  # Project action back to action space + add epsilon to prevent divide by zero error
        if self.action_space_type == "discrete":
            raise NotImplementedError(
                "Haven't figured out the specifics of this action space!"
            )
        '''
        if self.action_space_type == "binary":
            action = [action]
            #print("action is: " + str(action))
            #print(action)
            assert sum(action)<=self.num_high_actions'''
        
        if self.action_space_type == "binary":
            action = [action]
            action_sum = np.sum(action)
            #assert np.all(action_sum <= self.num_high_actions)

        # Update time
        self.t += 1

        # Update TSLS
        self.tsls = 0 if action == 2 else self.tsls + 1
        
        
        weight = np.zeros(self.numArms*2)
        # Update CQI for all UEs according to trace
        total_bytes_transferred = 0
        training_wt = 0.0
        for ue in range(self.num_UEs):
            #self.cqi_timesteps[ue] += 1
            #self.cqi_timesteps[ue] %= len(self.cqi_traces[ue])
            #self.cqis[ue] = self.cqi_traces[ue][self.cqi_timesteps[ue]]

            self.cqis[ue] = CQI

            

            # Compute RBGs allocated for this UE
            if self.action_space_type == "continuous":
                percentage_RBG = action[ue] / sum(action)
                allocated_RBG = np.round(percentage_RBG * self.total_rbgs)
            elif self.action_space_type == "discrete":
                allocated_RBG = action
            elif self.action_space_type == "binary":
                if action == [2]:
                    allocated_RBG = self.binary_high_RBGs
                    #print("I am in action 2: " + str(allocated_RBG))
                elif action == [1]:
                    allocated_RBG = self.binary_low_RBGs
                    #print(" I am in action 1: " + str(allocated_RBG))
                else:
                    allocated_RBG = self.binary_zero_RBGs
                    #print(" I am in action 0:" + str(allocated_RBG))

            training_wt = allocated_RBG/self.total_rbgs
            print("action: " + str(action) + " allocated RBG: " + str(allocated_RBG))
            # Transfer data from BL to UE
            #mean, std = self.cqi_map[self.cqis[ue]]
            #bytes_transferred = (
            #    allocated_RBG
            #    * np.random.normal(mean, std)
            #    # * np.random.binomial(1, 0.9)  # BLER 10%
            #    * 1000
            #) // 8
            
            #bytes_transferred = min(bytes_transferred, self.backlog_lens[ue])
            #bytes_transferred = np.minimum(bytes_transferred, self.backlog_lens[ue])

            # print(bytes_transferred)
            total_bytes_transferred = (tx*1000)/8.0
            #total_bytes_transferred = tx
            #self.backlog_lens[ue] -= bytes_transferred
            #print("total bytes transferred " + str(total_bytes_transferred))
            # Update BLs
            #inter_arrival_time, chunk_size = self.backlog_population_params[ue]
            self.backlog_lens[ue] = BL

            ''' 
            if self.t % inter_arrival_time == 0:
                self.backlog_lens[ue] += chunk_size
                self.backlog_lens[ue] = min(self.backlog_lens[ue], self.max_len_backlog)
            '''
        if action == 2:

            reward = (
                self.reward_func(total_bytes_transferred, self.backlog_lens)/1000
                - (self.cost_high_action/1000)*(self.binary_high_RBGs/self.num_RBGs)
                )
        elif action == 1:
            reward = (
                self.reward_func(total_bytes_transferred, self.backlog_lens)/1000
                - (self.cost_high_action/1000)*(self.binary_low_RBGs/self.num_RBGs)
                )
        else:
            reward = self.reward_func(total_bytes_transferred, self.backlog_lens)/1000
        rem_weight = 1-training_wt
        for ue in range(self.numArms):
            
            
            if self.RNTIs[ue] != self.r:
                weight[ue*2+1] = rem_weight
                weight[ue*2] = self.RNTIs[ue]
            if self.RNTIs[ue] == self.r:
                weight[ue*2+1] = training_wt
                weight[ue*2] = RNTI

        
        # print(reward,action,self.cost_high_action)
        if self.augment_state_space:
            self.back_pressures = [
                cqi * backlog_len
                for cqi, backlog_len in zip(self.cqis, self.backlog_lens)
            ]
            next_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis, self.back_pressures)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, BP1, BL2, CQI2, BP2,.....]
        else:
            next_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, BL2, CQI2,.....]
        #print(next_state)
        done = self.t == self.T
        info = {}
        self.state_history.append(next_state)  # Add delay to state observation
        # print(f"state of system at end of time {self.t}\n {self.backlog_lens}, {self.cqis}")
        
        # print(f"action : {self.action_history[0]}")
        # print(f"action_history: {self.action_history}")
        # print(f"reward: {reward}")
        # a=input(f"{self.t} continue?")
        # print(reward)

        flag = True
        self.wts = weight
        self.send_weight(weight, flag)

        #print(self.state_history[0])
        #print(reward)

        return self.state_history[0] / self.normalizer, reward, done, info, allocated_RBG, self.tsls

    def get_metrics_multi(self):
        #ZMQ sub
        RNTI = 0
        CQI = 0
        BL = 0
        tx = 0

        string = " "
        # print("mark1")
        #f = 0
        if(self.recvdricid>1):
            self.f=1

        self.curricid+=1
        numParams = self.numParams
        try:

            # Every 1ms  - recieve info from RAN (blocking)
            string_recv = self.socket_get_state.recv()
            print(string_recv)
            messagedata= string_recv.split()
            self.recvdricid = int(messagedata[numParams*self.numArms + self.numArms*2])

            print(f'received RIC ID:', self.recvdricid, self.curricid)

            
            while(self.curricid-self.recvdricid>1 and self.f==1):
                #sys.exit()
            #    string_temp = self.socket_get_state.recv()
                string = self.socket_get_state.recv()
                messagedata= string.split()
                self.recvdricid = int(messagedata[numParams*self.numArms + self.numArms*2])
                string_recv = string
            #    print(self.curricid, recvdricid)
            #    string_recv = string

            #print("temp: ", string_temp)
            # 2. RIC received state information from RAN: UE metrics + tti index

            string_temp = string_recv
            string_temp = str(string_temp).replace(" ", ",\t")
            string_temp = str(string_temp).replace("b'", "")
            string_temp = str(string_temp).replace("\\x00'","")
            seq_2 = str(time.time()) + ",\t" + str(string_temp) + ",\t" + str(self.curricid) + ",\t" + str(self.recvdricid) + "\n"
            self.f_seq.write(seq_2)

            #seq_2 = str(time.time()) + ",\t" + str(string_temp) + "2 \n"
            #self.f_seq.write(seq_2)

            self.queue_metrics.append(string_recv)
            
            if(self.delay_metrics >= self.maxdelay_metrics ):
                string = self.queue_metrics.pop(0)
                #self.delay_metrics = 0
            else:
                self.delay_metrics = self.delay_metrics + 1

            #print("recved string: ", string)
            #print("messagesata: ", messagedata)

            messagedata= string.split() 
            #if(len(messagedata)):

            #print("string", string, len(messagedata))
            
            #print(messagedata[0], messagedata[1], messagedata[2])
            self.RNTIs = np.zeros(self.numArms)
            CQIs = np.zeros(self.numArms)
            BLs = np.zeros(self.numArms)
            txs = np.zeros(self.numArms)
            MBs = np.zeros(self.numArms)
            
            '''
            for i in range(self.numArms):
                RNTIs[i] = self.arm[0][i*numParams+0]            
                CQIs[i] = self.arm[0][i*numParams+1]
                BLs[i] = self.arm[0][i*numParams+2]            
            
            '''
            # self.episodeTime = 0
            
            if len(messagedata) >= self.numArms*self.numParams:
                # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Raini - extract CQI

                #print("entered if statement")
                msg_data_str = str(messagedata[numParams*self.numArms+ self.numArms*2 +2])
                _frst = msg_data_str.find("'") + 1
                _last = msg_data_str.find("\\")
                msg_data_int = int(msg_data_str[_frst:_last])

                self.ran_index = msg_data_int
                #txb = float(messagedata[self.numArms*self.numParams+1])

                #self.ran_index = (messagedata[numParams*self.numArms])

                for i in range(self.numArms):
                    self.RNTIs[i] = int(messagedata[i*numParams+0])
                    CQIs[i] = int(messagedata[i*numParams+1])
                    BLs[i] = int(messagedata[i*numParams+2]) 
                    for j in range(self.numArms):
                        if int(messagedata[self.numArms*numParams+j*2]) == self.RNTIs[i]:
                            txs[i] = float(messagedata[self.numArms*numParams+j*2+1])
                            break 

                    #txs[i] = int(messagedata[i*numParams+3]) 
                   
                    if self.RNTIs[i] == self.r:
                        RNTI = self.RNTIs[i]
                        CQI = CQIs[i]
                        BL = BLs[i]
                        tx = txs[i]
            
            #print(RNTI)
            
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                pass
            else:
                traceback.print_exec()
                print("blimey")
        
        #print("RNTI, CQI, BL (get metrics func): " + str(RNTI) + str(CQI) + str(BL))
        return RNTI, CQI, BL, tx

    def send_weight(self, weights, flag):
        ''' Standard Gym function for taking an action. Supplies nextstate, reward, and episode termination signal.'''
        # self.time += 1
        #self.episodeTime += 1
        # if self.start:
        #     print("time between steps = ", time.time() - self.start)
        # self.start = time.time()

        # nextState, reward = self._calReward(action)

        #PUB action
        # action = 1
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Raini - sending action to ran. action=1 corresponds to requesting high_rb for this UE (and 0 low_RB)
        #print(weights)
        idx = 0
        str_to_send = ""
        while idx <len(weights):
            str_to_send = str_to_send + str(round(weights[idx],4)) + " "
            idx = idx +1
        #str_to_send = str_to_send+ "\n"

        str_to_send = str_to_send + str(self.curricid) + " " + str(self.ran_index) + " " + "\n"

        #str_to_send = str_to_send + str(self.ran_index) + "\n"


        
        #print("str_to_send: ", str_to_send)
        #myfile.write('%s\n", str_to_send)

        #seq_4 = str(time.time()) + ",\t" + str_to_send + "\n"
        #self.f_seq_4.write(seq_4)

        try:
            self.queue_weights.append(str_to_send)
            str_to_send_cur = ""

            if(self.delay_weights >= self.maxdelay_weights ):
                str_to_send_cur = self.queue_weights.pop(0)
                #if(flag == True): print("str_to_send_cur: ", str_to_send_cur)
                self.socket_send_action.send_string(str_to_send_cur)
                
                #self.delay_weights = 0
            else:
                self.delay_weights = self.delay_weights + 1
         
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                pass
            else:
                traceback.print_exec()
                print("blimey")
        
        seq_4 = str(time.time()) + ",\t" + str_to_send_cur  
        seq_4 = seq_4.replace("b'", "")
        seq_4 = seq_4.replace(" ", ",\t")
        seq_4 = seq_4.replace("\\x00'","")

        self.f_seq_4.write(seq_4)

        

        if(flag == True): print("str_to_send_cur: ", str_to_send_cur)
        #self.socket_send_action.send_string(str_to_send_cur)
        #self.socket_send_action2.send_string(str_to_send_cur)

