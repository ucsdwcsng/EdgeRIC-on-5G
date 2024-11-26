import numpy as np
import pandas as pd
import torch
import gym
from gym.spaces import MultiDiscrete, Box, Discrete
from stream_rl.registry import register_env, create_reward
from ray.rllib.env.env_context import EnvContext
from collections import deque
import random

gym.logger.set_level(40)


@register_env("EdgeRICApp0")
class EdgeRICApp0(gym.Env):
    """EdgeRIC Env: Simulation of the realtime RIC setup + Application (Model 0)"""

    def __init__(self, config: EnvContext):
        self.seed = config["seed"]
        if self.seed != -1:
            random.seed(self.seed)
            np.random.seed(self.seed)
        self.T = config["T"]
        self.t = None
        self.num_UEs = config["num_UEs"]
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
        self.cqi_traces_df = pd.read_csv(config["cqi_trace"])
        self.cqi_traces = [
            self.cqi_traces_df.iloc[:, ue].tolist() for ue in range(self.num_UEs)
        ]
        self.cqi_timesteps = [None] * self.num_UEs

        # Media Bufer Elements
        self.max_len_media = int(config["application"]["max_len"])
        self.media_lens = []
        self.playout_process_params = config["playout_process"]
        self.stalling = [None] * self.num_UEs
        self.stall_counts = [None] * self.num_UEs

        # Action and Observation Space Definitions
        self.action_space = Box(
            low=0.0, high=1.0, shape=(self.num_UEs,), dtype=np.float32
        )
        self.observation_space = Box(
            low=np.array([0, 1, 0] * self.num_UEs),
            high=np.array(
                [self.max_len_backlog, 15, self.max_len_media] * self.num_UEs
            ),
            dtype=np.float32,
        )
        self.num_state_variables = 3
        if self.augment_state_space:
            self.observation_space = Box(
                low=np.array([0, 1, 0, 0] * self.num_UEs),
                high=np.array(
                    [
                        self.max_len_backlog,
                        15,
                        15 * self.max_len_backlog,
                        self.max_len_media,
                    ]
                    * self.num_UEs
                ),
                dtype=np.float32,
            )

        self.normalize_state_space = config["normalize_state_space"]
        self.normalizer = (
            (
                np.array(
                    [
                        self.max_len_backlog * 0.2,
                        15,
                        self.max_len_backlog * 0.2 * 15,
                        self.max_len_media * 0.006,
                    ]
                    * self.num_UEs,
                    dtype=np.float32,
                )
                if self.augment_state_space
                else np.array(
                    [
                        self.max_len_backlog * 0.2,
                        15,
                        self.max_len_media * 0.006,
                    ]
                    * self.num_UEs,
                    dtype=np.float32,
                )
            )
            if self.normalize_state_space
            else 1
        )

        self.reward_func = create_reward(config["reward"])

    def reset(self):
        self.t = 0
        self.backlog_lens = [0] * self.num_UEs
        self.media_lens = [0] * self.num_UEs
        self.stalling = [False] * self.num_UEs
        self.stall_counts = [0] * self.num_UEs
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

        if self.augment_state_space:
            init_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (
                        self.backlog_lens,
                        self.cqis,
                        self.back_pressures,
                        self.media_lens,
                    )
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, BP1, MB1, BL2, CQI2, BP2, MB2.....]
        else:
            init_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis, self.media_lens)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, MB1, BL2, CQI2, MB2,.....]

        self.state_history.append(init_state)
        return self.state_history[0] / self.normalizer

    def step(self, action):
        """Order of operations within a step - transfers from :
        1.) Cloud to backlog buffer
        2.) Backlog buffer to playback(media) buffer
        3.) Playback bufffer to out
        """

        # Add delay to action
        self.action_history.append(action)
        action = self.action_history[0]

        action = np.clip(
            action, a_min=0.00000001, a_max=1.0
        )  # Project action back to action space + add epsilon to prevent divide by zero error

        # Update time
        self.t += 1
        # Update CQI for all UEs according to trace
        total_bytes_transferred = 0
        for ue in range(self.num_UEs):
            self.cqi_timesteps[ue] += 1
            self.cqi_timesteps[ue] %= len(self.cqi_traces[ue])
            self.cqis[ue] = self.cqi_traces[ue][self.cqi_timesteps[ue]]

            # Update BLs
            inter_arrival_time, chunk_size = self.backlog_population_params[ue]
            if self.t % inter_arrival_time == 0:
                self.backlog_lens[ue] += chunk_size
                self.backlog_lens[ue] = min(self.backlog_lens[ue], self.max_len_backlog)

            # Compute RBGs allocated for this UE
            percentage_RBG = action[ue] / sum(action)
            allocated_RBG = np.round(percentage_RBG * self.total_rbgs)

            # Transfer data from BL to UE
            mean, std = self.cqi_map[self.cqis[ue]]
            bytes_transferred = (
                allocated_RBG
                * np.random.normal(mean, std)
                # * np.random.binomial(1, 0.9)  # BLER 10%
                * 1000
            ) // 8
            bytes_transferred = min(bytes_transferred, self.backlog_lens[ue])
            total_bytes_transferred += bytes_transferred
            self.backlog_lens[ue] -= bytes_transferred
            self.media_lens[ue] += bytes_transferred

            # Playout from UE
            inter_departure_time, chunk_size = self.playout_process_params[ue]
            if self.t % inter_departure_time == 0:
                if self.media_lens[ue] >= chunk_size:
                    self.stalling[ue] = False
                    self.media_lens[ue] -= chunk_size
                else:
                    self.stalling[ue] = True
                    self.stall_counts[ue] += 1

        reward = self.reward_func(
            total_bytes_transferred, self.backlog_lens, self.stalling
        )
        if self.augment_state_space:
            self.back_pressures = [
                cqi * backlog_len
                for cqi, backlog_len in zip(self.cqis, self.backlog_lens)
            ]
            next_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (
                        self.backlog_lens,
                        self.cqis,
                        self.back_pressures,
                        self.media_lens,
                    )
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, BP1, MB1, BL2, CQI2, BP2, MB2,.....]
        else:
            next_state = np.array(
                [
                    param[ue]
                    for ue in range(self.num_UEs)
                    for param in (self.backlog_lens, self.cqis, self.media_lens)
                ],
                dtype=np.float32,
            )  # [BL1, CQI1, MB1, BL2, CQI2, MB2,.....]

        done = self.t == self.T
        info = {"stall_counts": self.stall_counts}
        self.state_history.append(next_state)  # Add delay to state observation
        return self.state_history[0] / self.normalizer, reward, done, info
