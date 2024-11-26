"""
Environment to calculate the Whittle index values as a deep reinforcement 
learning environment modelled after the OpenAi Gym API.
Same mini-batch episodes have the same trajectory values for comparing their returns.
This is the wireless scheduling case from the paper.
"""

import gym
import math
import time
import random
import datetime
import numpy as np
import pandas as pd
from gym import spaces
from numpy.random import RandomState
from stream_rl.registry import register_env

# from stable_baselines.common.env_checker import check_env #this test throws errors and needs tensorflow 1.x with python 3.6. it's normal


@register_env("WirelessEnv")
class sizeAwareIndexEnv(gym.Env):
    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        seed,
        numEpisodes,
        HOLDINGCOST,
        Training,
        r1,
        r2,
        q,
        case,
        classVal,
        batchSize,
        load,
        maxLoad,
        episodeLimit,
        fixedSizeMDP,
        noiseVar,
    ):

        super(sizeAwareIndexEnv, self).__init__()
        self.seed = seed
        self.myRandomPRNG = random.Random(self.seed)
        self.G = np.random.RandomState(
            self.seed
        )  # create a special PRNG for a class instantiation

        assert case in [1, 2]
        assert classVal in [1, 2]
        self.time = 0
        self.numEpisodes = numEpisodes
        self.episodeTime = 0
        self.currentEpisode = 0
        self.holdingCost = float(HOLDINGCOST)
        self.case = case
        self.classVal = classVal
        self.noiseVar = noiseVar

        self.goodTransVal = r2
        self.badTransVal = r1
        self.goodProb = q
        self.arm = {0: [1, 1]}
        self.maxLoad = maxLoad

        self.train = Training
        self.load = load
        self.batchSize = batchSize
        self.miniBatchCounter = 0
        self.episodeLimit = episodeLimit
        self.fixedSizeMDP = fixedSizeMDP

        loadVals = []
        if Training:
            for x in range(int(np.ceil(self.numEpisodes / self.batchSize))):
                loadVal = (np.ceil(self.G.randint(1, self.load + 1))).astype(np.float32)
                for i in range(batchSize):
                    loadVals.append(loadVal)
            loadVals = np.array(loadVals)
        else:
            loadVals = np.tile(load, numEpisodes)
        self.initialLoad = loadVals
        self.currentLoad = loadVals

        self.observationSize = 2

        lowState = np.zeros(self.observationSize, dtype=np.float32)
        highState = np.full(self.observationSize, 1.0, dtype=np.float32)

        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(lowState, highState, dtype=np.float32)

    def _findStateIndex(self, state):

        stateLocation = np.where((self.stateArray == state).all(axis=1))[0][0]
        return stateLocation

    def _calReward(self, action):
        """function to calculate next state, and reward given the action"""

        if action == 1:
            prng = RandomState(int(self.arm[0][0]))
            noise = prng.normal(0, np.sqrt(self.noiseVar))
            if self.train:
                reward = self.holdingCost
            else:
                reward = self.holdingCost

            if self.channelState[self.episodeTime - 1] == 1:
                self.arm[0][0] -= self.goodTransVal
            else:
                self.arm[0][0] -= self.badTransVal
            if self.channelState[self.episodeTime] == 1:
                self.arm[0][1] = 1.0
            else:
                self.arm[0][1] = 0.0

            if self.arm[0][0] <= 0:
                self.arm[0][0] = 0

        elif action == 0:
            prng = RandomState(int(self.arm[0][0] + self.maxLoad))
            noise = prng.normal(0, np.sqrt(self.noiseVar))
            if self.train:
                reward = self.holdingCost
            else:
                reward = self.holdingCost

            if self.channelState[self.episodeTime] == 1:
                self.arm[0][1] = 1.0
            else:
                self.arm[0][1] = 0.0

        nextState = np.array([self.arm[0][0], self.arm[0][1]], dtype=np.float32)

        reward = reward + noise * reward
        return nextState, -1 * reward

    def _normalizeState(self, state):
        """Function for normalizing the remaining load against the max load value"""
        state[0] = state[0] / self.maxLoad
        return state

    def step(self, action):
        """Standard Gym function for taking an action. Supplies nextstate, reward, and episode termination signal."""
        assert self.action_space.contains(action)
        assert action in [0, 1]
        self.time += 1
        self.episodeTime += 1
        nextState, reward = self._calReward(action)

        if self.train:
            done = bool((nextState[0] == 0)) or (self.episodeTime == self.episodeLimit)
            if self.fixedSizeMDP:
                done = False
                if nextState[0] == 0:
                    reward = 0
        else:
            done = bool((nextState[0] == 0))

        nextState = self._normalizeState(nextState)

        if done:
            self.currentEpisode += 1
            self.episodeTime = 0
            if self.train == False:
                self.currentEpisode = 0

        info = {}
        return nextState, reward, done, info

    def reset(self):
        """Standard Gym function for supplying initial episode state."""

        if self.miniBatchCounter % self.batchSize == 0:
            self.channelState = self.G.choice(
                [1, 0], self.episodeLimit + 1, p=[self.goodProb, 1 - self.goodProb]
            )

            self.arm[0][0] = self.initialLoad[self.currentEpisode]
            if self.channelState[self.episodeTime] == 1:
                self.arm[0][1] = 1.0
            else:
                self.arm[0][1] = 0.0

            self.arm[0][0] = self.initialLoad[self.currentEpisode]

            initialState = np.array([self.arm[0][0], self.arm[0][1]], dtype=np.float32)
            initialState = self._normalizeState(initialState)
            self.miniBatchCounter = 0
        else:
            self.arm[0][0] = self.initialLoad[self.currentEpisode]
            self.arm[0][1] = self.channelState[self.episodeTime]
            initialState = np.array([self.arm[0][0], self.arm[0][1]], dtype=np.float32)
            initialState = self._normalizeState(initialState)

        self.miniBatchCounter += 1
        return initialState


############################################################################
"""
For environment validation purposes, the below code checks if the nextstate, reward matches
what is expected given a dummy action.
"""
"""
SEED = 70
numEpisodes = 10
HOLDINGCOST = 1
BADTRANS = 1
GOODTRANS = 4
GOODPROB = 0.5
CASE = 1
CLASSVAL = 1
noiseVar = 0.0
LOAD = 100
BATCHSIZE = 5
EPISODELIMIT = 20
FIXEDSIZEMDP = False
env = sizeAwareIndexEnv(numEpisodes=numEpisodes, HOLDINGCOST=HOLDINGCOST, seed=SEED, maxLoad = LOAD,
Training=True, r1 =BADTRANS, r2 = GOODTRANS, q=GOODPROB, noiseVar = noiseVar, 
case=CASE, classVal=CLASSVAL, load=LOAD, batchSize = BATCHSIZE, episodeLimit=EPISODELIMIT, fixedSizeMDP=FIXEDSIZEMDP)
observation = env.reset()
#check_env(env, warn=True)
x = np.array([0,1]) # dummy actions
x = np.tile(x, 100000)
n_steps = np.size(x)
start = time.time()
for step in range(n_steps):
    nextState, reward, done, info = env.step(x[step])
    print(f'action: {x[step]} nextstate: {nextState}  reward: {reward} done: {done}')
    observation = nextState
    if done:
        print(f'Finished episode {env.currentEpisode}/{env.numEpisodes}')
        if env.currentEpisode < env.numEpisodes:
            nextState = env.reset()
        if env.currentEpisode == env.numEpisodes:
            break
print('------------------------------------------')
print(f'DONE. Time taken: {time.time() - start:.4f} seconds')
"""
