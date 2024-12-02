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

# Initialize the EdgericMessenger for metrics
edgeric_messenger = EdgericMessenger(socket_type="None")

if __name__ == "__main__":
    try:
        tti_count = 0
        while True:
            try:
                # Retrieve metrics from RAN
                tti_count, ue_data = edgeric_messenger.get_metrics(flag_print=False)
                
                # Print RT-E2 report every 500 timesteps
                if tti_count % 500 == 0:
                    print("RT-E2 Report: \n")
                    print(f"TTI Count: {tti_count}\n")
                    print(f"UE Metrics: {ue_data} \n")
                    
            except redis.exceptions.RedisError as e:
                print("Redis error:", e)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting gracefully.")
