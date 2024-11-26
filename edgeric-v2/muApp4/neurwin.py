"""
NEURWIN algorithm: used for learning 
the Whittle index of one restless arm. 
Training is done in a reinforcement learning setting.
"""

import os
import time
import torch
import random
import numpy as np
import pandas as pd
from math import ceil
import torch.nn as nn

# from torchviz import make_dot
import matplotlib.pyplot as plt
import torch.nn.functional as F


class fcnn(nn.Module):
    """Fully-Connected Neural network for NEURWIN to modify its parameters"""

    def __init__(self, stateSize, actionSize):
        super(fcnn, self).__init__()
        # self.linear1 = nn.Linear(stateSize, 16, bias=True)
        # self.linear2 = nn.Linear(16, 4)
        # self.linear3 = nn.Linear(4, 1, bias=True)

        # self.linear1 = nn.Linear(stateSize, 2, bias=True)
        # self.linear2 = nn.Linear(2, 2)
        # self.linear3 = nn.Linear(2, 1, bias=True)

        #self.linear1 = nn.Linear(stateSize+actionSize, 8, bias=True)
        # self.linear1 = nn.Linear(stateSize+2, 8, bias=True)
        # self.linear2 = nn.Linear(8, 4)
        # self.linear3 = nn.Linear(4, 1, bias=True)

        self.linear1 = nn.Linear(stateSize+3, 32, bias=True)
        self.linear2 = nn.Linear(32, 8)
        self.linear3 = nn.Linear(8, 1, bias=True)


    def forward(self, x):
        print(x)
        flat_data = [item for sublist in [d.flatten() if isinstance(d, np.ndarray) else [d] for d in x] for item in sublist]
        x = torch.FloatTensor(flat_data)
        x = F.relu(self.linear1(x))
        x = F.relu(self.linear2(x))
        x = self.linear3(x)

        return x

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=1.0)
            if module.bias is not None:
                module.bias.data.zero_()

    def printNumParams(self):
        total_params = sum(p.numel() for p in self.parameters())
        total_params_trainable = sum(
            p.numel() for p in self.parameters() if p.requires_grad
        )
        print(f"Total number of parameters: {total_params}")
        print(f"Total number of trainable parameters: {total_params_trainable}")


class NEURWIN(object):
    def __init__(
        self,
        run_name,  # dummy
        hparams,
        stateSize,
        actionSize,  # dummy
        transformed_states,  # dummy
        transformed_actions,  # dummy
        env,
        sigmoidParam,
        numEpisodes,
        noiseVar,
        seed,
        discountFactor,
        saveDir,
        episodeSaveInterval,
        logger,
        mu_r, 
        mu_l
    ):
        # -------------constants-------------
        self.seed = seed
        torch.manual_seed(self.seed)
        self.myRandomPRNG = random.Random(self.seed)
        self.G = np.random.RandomState(
            self.seed
        )  # create a special PRNG for a class instantiation

        self.numEpisodes = numEpisodes
        self.episodeRanges = np.arange(
            0, self.numEpisodes + episodeSaveInterval, episodeSaveInterval
        )
        self.stateSize = stateSize
        self.actionSize = actionSize
        self.batchSize = hparams["HP_BATCHSIZE"]
        self.sigmoidParam = sigmoidParam
        self.initialSigmoidParam = sigmoidParam
        self.beta = discountFactor
        self.env = env
        self.nn = fcnn(self.stateSize,self.actionSize)
        # self.nn = fcnn(self.stateSize)
        # print(stateSize)
        # self.nn.load_state_dict(torch.load("/home/grads/u/ujwald36/Work/repos/Pytorch-RL-Custom_mobicom/simulator/outputs/2023-04-21/02-47-45/seed_42_lr_0.0001_batchSize_5_trainedNumEpisodes_1000000/trained_model.pt"))
        # self.nn._init_weights(self.nn)
        self.linear1WeightGrad = []
        self.linear2WeightGrad = []
        self.linear3WeightGrad = []

        self.linear1BiasGrad = []
        self.linear2BiasGrad = []
        self.linear3BiasGrad = []

        self.paramChange = []
        self.numOfActions = 2
        self.directory = saveDir
        self.noiseVar = noiseVar

        self.temp = None
        self.LearningRate = hparams["HP_LEARNINGRATE"]
        self.optimizer = torch.optim.Adam(self.nn.parameters(), lr=self.LearningRate)
        # -------------counters-------------
        self.currentMiniBatch = 0
        self.batchCounter = 0
        self.episodeRewards = []
        self.discountRewards = []
        self.hparams = hparams
        self.run_name = run_name
        self.logger = logger
        self.mu_r = mu_r
        self.mu_l = mu_l
        #self.continueLearning()

    def continueLearning(self):
        """Function for continuing with a learned model. Type in the number of episodes to continue from in trainedNumEpisodes"""
        '''self.nn.load_state_dict(
            torch.load(
                f"outputs/2023-11-09/10-00-51/models/properactions/"
                + f"seed_{self.seed}_lr_{self.LearningRate}_sigmoid_{1}_batchSize_{20}_trainedNumEpisodes_{20000}_mur_{self.mu_r}_mul_{self.mu_l}/trained_model.pt"
            )
        )'''
        self.nn.load_state_dict(
            torch.load(
                "/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/myoutputs/training/urllc_new/models/properactions/seed_42_lr_0.05_sigmoid_5_batchSize_20_trainedNumEpisodes_3100_mur_5_mul_15/trained_model.pt"
            )
        )

    def changeSigmoidParam(self):
        """Function for changing the sigmoid value as training happens. If not active, then m value is a constant."""
        self.sigmoidParam = self.sigmoidParam - self.sigmoidParam * 0.01
        if self.sigmoidParam <= 0.000001:
            self.sigmoidParam = 0.000001

    def newMiniBatchReset(self, index, state):
        """Function for new mini-batch procedures. For recovering bandits, the actviation cost is chosen for a random state."""

        # if self.stateSize == 1:

        #     stateVal = self.G.randint(1, 21)
        #     stateVal = np.array([stateVal], dtype=np.float32)
        #     self.cost = self.nn.forward(stateVal).detach().numpy()[0]

        # elif state[0] in np.arange(0, 13):

        #     load = self.G.randint(1, 9 + 1)
        #     timeUntilDeadline = self.G.randint(1, 12 + 1)
        #     stateVal = np.array([timeUntilDeadline, load], dtype=np.float32)
        #     self.cost = self.nn.forward(stateVal).detach().numpy()[0]

        # elif self.env.classVal == 1:

        #     channelState = self.G.choice([1, 0], p=[0.75, 0.25])
        #     load = self.G.randint(1, 1000000 + 1) / 1000000
        #     stateVal = np.array([load, channelState], dtype=np.float32)

        #     self.cost = self.nn.forward(stateVal).detach().numpy()[0]

        # elif self.env.classVal == 2:

        #     channelState = self.G.choice([1, 0], p=[0.1, 0.9])
        #     load = self.G.randint(1, 1000000 + 1) / 1000000
        #     stateVal = np.array([load, channelState], dtype=np.float32)

        #     self.cost = self.nn.forward(stateVal).detach().numpy()[0]


        random_state = np.round(self.env.observation_space.sample())
        #random_action = [self.env.action_space.sample()/2]
        # rs = np.random.choice([0.0,30.],p=[0.5,0.5])
        # random_state[0]=rs
        random_state = random_state / self.env.normalizer
        # print(random_state)
        # a=input("Raju")
        # random_state = int(np.random.choice(self.env.statespace,size=1))
        #random_state = np.array([int(np.random.choice(self.env.statespace,size=1))],dtype=np.float32)
        self.cost = self.nn.forward(random_state).detach().numpy()[0]
        # inputs = list(random_state) + list(random_action)
        # input_list = [i for i in inputs]
        # self.cost = self.nn.forward(input_list).detach().numpy()[0]
        #self.cost = self.nn.forward(np.eye(len(self.env.statespace),dtype=np.float32)[random_state]).detach().numpy()[0]
        # self.cost = 32
        return random_state #,random_action

    def takeAction(self, state):
        """Function for taking action based on the sigmoid function's generated probability distribution."""

        index = self.nn.forward(state)
        if (self.env.t == 0) and (self.currentEpisode % self.batchSize == 0):  # Verify
            random_state = self.newMiniBatchReset(index, state)
            self.logger.info(f"new cost: {self.cost}")
            self.logger.info(f"new state: {random_state}")

        sigmoidProb = torch.sigmoid(self.sigmoidParam * (index - self.cost))
        probOne = sigmoidProb.detach().numpy()[0]
        probs = [probOne, 1 - probOne]
        probs = np.array(probs)
        probs /= probs.sum()

        action = self.G.choice([1, 0], 1, p=probs)
        if action == 1:
            logProb = torch.log(sigmoidProb)

            logProb.backward()

        elif action == 0:
            logProb = torch.log(1 - sigmoidProb)

            logProb.backward()

        return action[0]
    # def takeAction(self, state):
    #     '''Function for taking action based on the sigmoid function's generated probability distribution.'''
    #     if (self.env.t == 0) and (self.currentEpisode % self.batchSize == 0):
    #        random_state, random_action = self.newMiniBatchReset(state)
    #        self.logger.info(f"new cost: {self.cost}")
    #        self.logger.info(f"new state: {random_state}"+f"new action: {random_action}")

    #     problist = []
    #     sigmoidProb1 = {}
    #     sigmoidProb2 = {}
    #     index1 = {}
    #     index2 = {}
        
    #     for a in range(self.env.action_space.n):
    #         if a == 0:
    #             inputs = list(state)+[a]
    #             input_list = [i for i in inputs]
    #             index1[a] = self.nn.forward(input_list)[0]
    #             sigmoidProb1[a] = torch.sigmoid(self.sigmoidParam*(index1[a] - torch.as_tensor(self.cost)))
    #             probOne = 1-(sigmoidProb1[a].detach().numpy())
    #             probTwo = 0.0

    #             sigmoidProb2[a] = torch.zeros(1)
                
    #         elif a != self.env.action_space.n-1:
    #             inputs = list(state)+[(a-1)/2]
    #             input_list = [i for i in inputs]
    #             index1[a] = self.nn.forward(input_list)[0]
            
    #             inputs = list(state)+[a/2]
    #             input_list = [i for i in inputs]
    #             index2[a] = self.nn.forward(input_list)[0]

    #             sigmoidProb1[a] = torch.sigmoid(self.sigmoidParam*(index1[a] - torch.as_tensor(self.cost)))
    #             sigmoidProb2[a] = torch.sigmoid(self.sigmoidParam*(index2[a] - torch.as_tensor(self.cost)))
            
    #             probOne = sigmoidProb1[a].detach().numpy()
    #             probTwo = sigmoidProb2[a].detach().numpy()

    #         else:
    #             inputs = list(state)+[(a-1)/2]
    #             input_list = [i for i in inputs]
    #             index1[a] = self.nn.forward(input_list)[0]
    #             sigmoidProb1[a] = torch.sigmoid(self.sigmoidParam*(index1[a] - torch.as_tensor(self.cost)))
    #             probOne = 1.0
    #             probTwo = 1-(sigmoidProb1[a].detach().numpy())
    #             sigmoidProb2[a] = torch.zeros(1)

    #         probs = probOne * (1-probTwo)
    #         problist.append(float(probs))
        
    #     problist = np.array(problist)

    #     try:
    #         problist /= problist.sum()
        

    #         action = np.random.choice(np.arange(self.env.action_space.n), size=1, p = problist)
    #     except:
    #         #print(problist)
    #         action = np.random.choice(np.arange(self.env.action_space.n),size=1,p=None)

    
            
    #     # if self.currentEpisode % 100 == 0:
    #     #     print(self.currentEpisode)
    #     #     print(index1,index2,self.cost)
    #     #     print(problist)
    #     problisttensor = torch.tensor(problist)
    #     if problisttensor.isnan().any():
    #         print("problist is Nan")
    #     else:
    #         for a in range(self.env.action_space.n):
    #             if action == a:
    #                 logProb =  torch.log(sigmoidProb1[a]) + torch.log(1-sigmoidProb2[a])
    #                 if action == 0:
    #                     logProb =  torch.log(1-sigmoidProb1[a]) + torch.log(1-sigmoidProb2[a])
                
    #                 logProb.backward()

    #     return action[0]

    def _saveEpisodeGradients(self):
        """Function for saving the gradients of each episode in one mini-batch"""

        self.linear1WeightGrad.append(self.nn.linear1.weight.grad.clone())
        self.linear2WeightGrad.append(self.nn.linear2.weight.grad.clone())
        self.linear3WeightGrad.append(self.nn.linear3.weight.grad.clone())

        self.linear1BiasGrad.append(self.nn.linear1.bias.grad.clone())
        self.linear2BiasGrad.append(self.nn.linear2.bias.grad.clone())
        self.linear3BiasGrad.append(self.nn.linear3.bias.grad.clone())

        self.optimizer.zero_grad(set_to_none=False)

    def _performBatchStep(self):
        """Function for performing the gradient ascent step on accumelated mini-batch gradients."""
        print("performing batch gradient step")

        meanBatchReward = sum(self.discountRewards) / len(self.discountRewards)
        for i in range(len(self.discountRewards)):
            self.discountRewards[i] = self.discountRewards[i] - meanBatchReward

            self.nn.linear1.weight.grad += (
                self.discountRewards[i] * self.linear1WeightGrad[i]
            )
            self.nn.linear2.weight.grad += (
                self.discountRewards[i] * self.linear2WeightGrad[i]
            )
            self.nn.linear3.weight.grad += (
                self.discountRewards[i] * self.linear3WeightGrad[i]
            )

            self.nn.linear1.bias.grad += (
                self.discountRewards[i] * self.linear1BiasGrad[i]
            )
            self.nn.linear2.bias.grad += (
                self.discountRewards[i] * self.linear2BiasGrad[i]
            )
            self.nn.linear3.bias.grad += (
                self.discountRewards[i] * self.linear3BiasGrad[i]
            )

        self.linear1WeightGrad = []
        self.linear2WeightGrad = []
        self.linear3WeightGrad = []

        self.linear1BiasGrad = []
        self.linear2BiasGrad = []
        self.linear3BiasGrad = []

        # To stop gradients from exploding
        torch.nn.utils.clip_grad_norm_(self.nn.parameters(),100)
        self.optimizer.step()

        self.optimizer.zero_grad(set_to_none=False)

        self.discountRewards = []

        # self.changeSigmoidParam() # uncomment this to change m value every mini-batch

    def _discountRewards(self, rewards):
        """Function for discounting an episode's reward based on set discount factor."""
        for i in range(len(rewards)):
            rewards[i] = (self.beta**i) * rewards[i]
        return -1 * sum(rewards)

    def learn(self):
        self.start = time.time()
        self.currentEpisode = 0
        self.totalTimestep = 0
        self.episodeTimeStep = 0
        self.episodeTimeList = []
        # self.currentEpisode = 100 # for continuing learning

        while self.currentEpisode < self.numEpisodes:
            if self.currentEpisode in self.episodeRanges:
                self.close(self.currentEpisode)
            episodeRewards = []
            s_0 = self.env.reset()

            done = False
            # self.sigmoidParam = self.initialSigmoidParam #uncomment this for doing param change every timestep in episode

            while done == False:
                action = self.takeAction(s_0)
                
                #s_1, reward, done, info, _, tsls = self.env.step(action)
                RNTI, CQI, BL, tx = self.env.get_metrics_multi()        
                #obs, reward, done, info = env.step(action, RNTIs, CQIs, BLs, tx_bytes, MBs)
                s_1, reward, done, info, _, tsls = self.env.step(action, RNTI, CQI, BL, tx)
                #reward += self.mu*reward
                reward += self.mu_r*reward
                reward -= self.mu_l*tsls
                # if action == 2:
                #     reward -= (8/17)*(self.cost/1000)
                # elif action == 1:
                #     reward -= (3/17)*(self.cost/1000)
                reward -= action*(self.cost/1000)
                episodeRewards.append(reward)
                s_0 = s_1
                # self.changeSigmoidParam() #uncomment this for doing param change every timestep in episode
                self.totalTimestep += 1
                self.episodeTimeStep += 1
                    
                if done:
                    if self.currentEpisode % self.batchSize == 0:
                        self.logger.info(
                            f"finished episode: {self.currentEpisode+1} reward: {sum(episodeRewards)}"
                        )
                    self.discountRewards.append(self._discountRewards(episodeRewards))
                    self.batchCounter += 1

                    self.episodeRewards.append(sum(episodeRewards))
                    self._saveEpisodeGradients()
                    episodeRewards = []
                    self.currentEpisode += 1
                    self.episodeTimeList.append(self.episodeTimeStep)
                    self.episodeTimeStep = 0
                    # self.changeSigmoidParam() # uncomment this to change param every episode in one mini-batch

                    if self.batchCounter == self.batchSize:
                        self._performBatchStep()
                        self.currentMiniBatch += 1
                        self.batchCounter = 0
                        # self.sigmoidParam = self.initialSigmoidParam # uncomment this to change m value every episode in one mini-batch
        self.end = time.time()
        self.close(self.numEpisodes)
        self.trainingEnding()
        print(
            f"---------------------------\nDONE. Time taken: {self.end - self.start:.5f} seconds."
        )
        print(f"total timesteps taken: {self.totalTimestep}")

    def close(self, episode):
        """Function for saving the NN parameters at defined interval *episodeSaveInterval*"""
        #self.log.info(f"directory in close () before saving: {self.directory}")
        directory = (
            f"{self.directory}"
            + f"/models/properactions/seed_{self.seed}\
_lr_{self.LearningRate}_sigmoid_{self.sigmoidParam}_batchSize_{self.batchSize}_trainedNumEpisodes_{episode}_mur_{self.mu_r}_mul_{self.mu_l}"
        )
        #self.log.info(f"directory in close () after saving: {directory}")
        if not os.path.exists(directory):
            os.makedirs(directory)

        torch.save(self.nn.state_dict(), directory + "/trained_model.pt")

    def trainingEnding(self):
        """Function for saving training information once it is over."""

        file = open(self.directory + "/trainingInfo.txt", "w+")
        file.write(f"training time: {self.end - self.start:.5f} seconds\n")
        file.write(f"training episodes: {self.numEpisodes}\n")
        file.write(f"Mini-batch size: {self.batchSize}\n")
        file.write(f"Total timesteps: {self.totalTimestep}\n")
        file.close()

        data = {
            "episode": range(len(self.episodeTimeList)),
            "episode_timesteps": self.episodeTimeList,
        }
        df = pd.DataFrame(data=data)
        df.to_csv(
            self.directory + f"/episode_timesteps_batchsize_{self.batchSize}.csv",
            index=False,
        )

    def whittle_thresh_action(self, threshold, state):
        # whittle_index = {}
        # whittle_index[-1] = 11000
        # whittle_index[self.env.action_space.n+1] = 0
        # for action in range(self.env.action_space.n-1):
        #     inputs = list(state) + [action/2]
        #     input_list = [i for i in inputs]
        #     whittle_index[action] = self.nn.forward(input_list)
        whittle_index = self.nn.forward(state)
        # print(f"W({state})={whittle_index} <> {threshold}")
        # for action in range(1,self.env.action_space.n-1):
        #     if whittle_index[action-1] > threshold and threshold >= whittle_index[action]:
        #         return action
        #     elif whittle_index[action-1] <= threshold:
        #         return 0
        #     elif whittle_index[action] >= threshold:
        #         return 2
        return 1 if whittle_index > threshold else 0

    def eval(self, eval_episodes_per_iter, threshold, directory, mu_r):
        #self.env.cost_high_action = threshold
        # self.env.create_R(W=1.0)
        #text_file_path = 'tx_values.txt'
        f_seq_bytes = open(f"/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/lambda_urllc/tx_values_bytes_highaction_urllc_thresh_{threshold}_mul_{mu_r}.txt","w")
        f_seq_mbps = open(f"/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/lambda_urllc/tx_values_mbps_highaction_urllc_thresh_{threshold}_mul_{mu_r}.txt","w")
        f_seq_tsls = open(f"/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/lambda_urllc/tx_values_tsls_highaction_urllc_thresh_{threshold}_mul_{mu_r}.txt","w")
        rewards_iter_mean = []
        rewards_iter_std = []
        W_ks = []
        #for iter in self.episodeRanges:
        for iter in [1]:    
            #if iter % 500 == 0 or iter == 0 or iter == 1:
            print("finishing iter")
            '''
            directory = (
                f"{self.directory}"
                + f"/models/properactions/seed_{self.seed}\
    _lr_{self.LearningRate}_sigmoid_{self.sigmoidParam}_batchSize_{self.batchSize}_trainedNumEpisodes_{iter}_mur_{self.mu_r}_mul_{self.mu_l}"
            )'''
            #directory = ("/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/models")
            self.nn.load_state_dict(torch.load(directory + "/trained_model.pt"))
            self.nn.eval()
            iter_rewards = []
            for episode in range(eval_episodes_per_iter):
                episode_reward = 0
                done = False
                state = self.env.reset()
                while not done:
                    action = self.whittle_thresh_action(threshold, state)
                    #state, reward, done, info,_, tsls = self.env.step(action)
                    #action = 0
                    RNTI, CQI, BL, tx = self.env.get_metrics_multi() 
                    f_seq_mbps.write(str(tx) + '\n')   
                    #obs, reward, done, info = env.step(action, RNTIs, CQIs, BLs, tx_bytes, MBs)
                    state, reward, done, info, _, tsls = self.env.step(action, RNTI, CQI, BL, tx)
                    f_seq_tsls.write(str(tsls) + '\n') 
                    f_seq_bytes.write(str(reward) + '\n')  
                    #reward += self.mu*reward
                    reward += self.mu_r*reward
                    reward -= self.mu_l*tsls
                    #print(f"Resulting action {action} reward {reward}")
                    episode_reward += reward
                iter_rewards.append(episode_reward)
            rewards_iter_mean.append(np.mean(iter_rewards))
            rewards_iter_std.append(np.std(iter_rewards))
            # w_ks = np.zeros(2,dtype = np.float32)
            # states = {0:[0.,8/15],1:[1.,8/15]}
            # for s in range(len(w_ks)):
            #     ip = states[s]
            #     w_ks[s] = self.nn.forward(ip).detach().numpy()[0]
            # W_ks.append(w_ks)
        self.env.cost_high_action = 0.0
        print(rewards_iter_mean)
        #f_seq.close()
        return rewards_iter_mean, rewards_iter_std #, W_ks