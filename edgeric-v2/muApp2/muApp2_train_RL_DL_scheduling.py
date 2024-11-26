import argparse
import hydra
import gym
import os
import sys
import pickle
import time
import logging
import torch
import numpy as np
import zmq

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import math
# from edgeric_messenger import EdgericMessenger

torch.set_printoptions(precision=2)
np.set_printoptions(suppress=True)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import *
from models.mlp_policy import Policy
from models.mlp_critic import Value
from models.mlp_policy_disc import DiscretePolicy
from core.ppo import ppo_step
from core.common import estimate_advantages
from core.agent_original import Agent

from stream_rl.registry import ENVS
from stream_rl.plots import (
    visualize_edgeric_training,
    visualize_edgeric_evaluation,
    plot_cdf,
    visualize_policy_cqi,
    visualize_policy_backlog_len,
)

# A logger for this file
log = logging.getLogger(__name__)


parser = argparse.ArgumentParser(description="PyTorch PPO example")
parser.add_argument(
    "--env-name",
    default="Hopper-v2",
    metavar="G",
    help="name of the environment to run",
)
parser.add_argument("--model-path", metavar="G", help="path of pre-trained model")
parser.add_argument(
    "--render", action="store_true", default=False, help="render the environment"
)
parser.add_argument(
    "--log-std",
    type=float,
    default=-0.0,
    metavar="G",
    help="log std for the policy (default: -0.0)",
)
parser.add_argument(
    "--gamma",
    type=float,
    default=0.9,
    metavar="G",
    help="discount factor (default: 0.99)",
)
parser.add_argument(
    "--tau", type=float, default=0.95, metavar="G", help="gae (default: 0.95)"
)
parser.add_argument(
    "--l2-reg",
    type=float,
    default=1e-4,
    metavar="G",
    help="l2 regularization regression (default: 1e-3)",
)
parser.add_argument(
    "--learning-rate",
    type=float,
    default=1e-3,
    metavar="G",
    help="learning rate (default: 3e-4)",
)
parser.add_argument(
    "--clip-epsilon",
    type=float,
    default=0.2,
    metavar="N",
    help="clipping epsilon for PPO",
)
parser.add_argument(
    "--num-threads",
    type=int,
    default=1,
    metavar="N",
    help="number of threads for agent (default: 1)",
)
parser.add_argument(
    "--seed", type=int, default=1, metavar="N", help="random seed (default: 1)"
)
parser.add_argument(
    "--min-batch-size",
    type=int,
    default=2048, #2048,
    metavar="N",
    help="minimal batch size per PPO update (default: 2048)",
)
parser.add_argument(
    "--eval-batch-size",
    type=int,
    default=2048,
    metavar="N",
    help="minimal batch size for evaluation (default: 2048)",
)
parser.add_argument(
    "--max-iter-num",
    type=int,
    default=100,
    metavar="N",
    help="maximal number of main iterations (default: 500)",
)  # Depreciated : Use num_iters field in config file instead
parser.add_argument(
    "--log-interval",
    type=int,
    default=1,
    metavar="N",
    help="interval between training status logs (default: 10)",
)
parser.add_argument(
    "--save-model-interval",
    type=int,
    default=0,
    metavar="N",
    help="interval between saving model (default: 0, means don't save)",
)
parser.add_argument("--gpu-index", type=int, default=0, metavar="N")
args = parser.parse_args()

@hydra.main(config_path="conf", config_name="edge_ric")
def main(conf):

    dtype = torch.float32
    torch.set_default_dtype(dtype)
    device = (
        torch.device("cuda", index=args.gpu_index)
        if torch.cuda.is_available()
        else torch.device("cpu")
    )
    if torch.cuda.is_available():
        torch.cuda.set_device(args.gpu_index)

    # Initialize the EdgeRIC messenger
    # edgeric_messenger = EdgericMessenger(socket_type="weights")

    def update_params(batch, i_iter):
        # Your code for updating parameters remains the same...
        pass

    def main_loop():
        hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
        output_dir = hydra_cfg["run"]["dir"]
        if not os.path.exists(output_dir):
            print(f"Creating directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        else:
            print(f"Directory already exists: {output_dir}")

        ppo_rewards = []
        for i_iter in range(conf["num_iters"]):
            batch, log_train = agent.collect_samples(args.min_batch_size, render=args.render)
            t0 = time.time()
            update_params(batch, i_iter)
            t1 = time.time()
            _, log_eval = agent.collect_samples(args.eval_batch_size, mean_action=False)
            t2 = time.time()
            ppo_rewards.append(log_eval["avg_reward"]/5000) 
            if i_iter % args.log_interval == 0:
                log.info(
                    "{}\tT_sample {:.4f}\tT_update {:.4f}\tT_eval {:.4f}\ttrain_R_min {:.2f}\ttrain_R_max {:.2f}\ttrain_R_avg {:.2f}\teval_R_avg {:.2f}".format(
                        i_iter,
                        log_train["sample_time"],
                        t1 - t0,
                        t2 - t1,
                        log_train["min_reward"],
                        log_train["max_reward"],
                        log_train["avg_reward"],
                        log_eval["avg_reward"],
                    )
                )

            # Your model saving code remains the same...

            torch.cuda.empty_cache()
        return ppo_rewards


    num_eval_episodes = conf["num_eval_episodes"]
    num_seeds = conf["num_seeds"]
    ppo_train_rewards = []
    env_cls = ENVS[conf["env"]]
    env = env_cls(conf["env_config"])

    for seed in range(num_seeds):
        log.info(f"********* Training for seed {seed+1} *********")
        env_cls = ENVS[conf["env"]]
        env = env_cls(conf["env_config"])
        state_dim = env.observation_space.shape[0]
        is_disc_action = len(env.action_space.shape) == 0
        running_state = None

        if args.model_path is None:
            if is_disc_action:
                policy_net = DiscretePolicy(state_dim, env.action_space.n)
            else:
                policy_net = Policy(
                    state_dim,
                    env.action_space.shape[0],
                    log_std=args.log_std,
                    activation="sigmoid",
                )
            value_net = Value(state_dim)
        else:
            policy_net, value_net, running_state = pickle.load(
                open(args.model_path, "rb")
            )
        policy_net.to(device)
        value_net.to(device)

        optimizer_policy = torch.optim.Adam(
            policy_net.parameters(), lr=args.learning_rate
        )
        optimizer_value = torch.optim.Adam(
            value_net.parameters(), lr=args.learning_rate
        )

        optim_epochs = 10
        optim_batch_size = 64

        agent = Agent(
            env,
            policy_net,
            device,
            running_state=running_state,
            num_threads=args.num_threads,
        )

        ppo_train_rewards.append(main_loop())

    if ppo_train_rewards:
        visualize_edgeric_training(
            ppo_train_rewards
        )

if __name__ == "__main__":
    main()
