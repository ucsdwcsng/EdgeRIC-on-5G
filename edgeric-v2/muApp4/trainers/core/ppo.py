import torch
import hydra
import numpy as np
import time
import os
import pickle
import logging

from ..utils import *
from ..models.mlp_policy import Policy
from ..models.mlp_critic import Value
from ..models.mlp_policy_disc import DiscretePolicy
from ..core.common import estimate_advantages
from ..core.agent import Agent
from stream_rl.registry import ENVS
#log = logging.getLogger(__name__)
#@hydra.main(config_path="conf", config_name="edge_ric_neurwin_ppo")


def ppo_step(policy_net, value_net, optimizer_policy, optimizer_value, optim_value_iternum, states, actions,
             returns, advantages, fixed_log_probs, clip_epsilon, l2_reg):

    """update critic"""
    for _ in range(optim_value_iternum):
        values_pred = value_net(states)
        value_loss = (values_pred - returns).pow(2).mean()
        # weight decay
        for param in value_net.parameters():
            value_loss += param.pow(2).sum() * l2_reg
        optimizer_value.zero_grad()
        value_loss.backward()
        optimizer_value.step()

    """update policy"""
    log_probs = policy_net.get_log_prob(states, actions)
    ratio = torch.exp(log_probs - fixed_log_probs)
    surr1 = ratio * advantages
    surr2 = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * advantages
    policy_surr = -torch.min(surr1, surr2).mean()
    optimizer_policy.zero_grad()
    policy_surr.backward()
    torch.nn.utils.clip_grad_norm_(policy_net.parameters(), 40)
    optimizer_policy.step()

def ppo_train(conf, cost):
    log = logging.getLogger(conf["logger_name"])
    #log = logging.getLogger(__name__)
    #@hydra.main(config_path="conf", config_name="edge_ric_neurwin_ppo")
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    #output_dir = hydra_cfg["run"]["dir"]
    output_dir = "/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/models/ppo"
    dtype = torch.float32
    torch.set_default_dtype(dtype)
    device = (
        torch.device("cuda", index=conf["gpu_index"])
        if torch.cuda.is_available()
        else torch.device("cpu")
    )
    if torch.cuda.is_available():
        torch.cuda.set_device(conf["gpu_index"])

    def update_params(batch, i_iter):
        states = torch.from_numpy(np.stack(batch.state)).to(dtype).to(device)
        actions = torch.from_numpy(np.stack(batch.action)).to(dtype).to(device)
        rewards = torch.from_numpy(np.stack(batch.reward)).to(dtype).to(device)
        masks = torch.from_numpy(np.stack(batch.mask)).to(dtype).to(device)
        with torch.no_grad():
            values = value_net(states)
            fixed_log_probs = policy_net.get_log_prob(states, actions)

        """get advantage estimation from the trajectories"""
        advantages, returns = estimate_advantages(
            rewards, masks, values, conf["gamma"], conf["tau"], device
        )

        """perform mini-batch PPO update"""
        optim_iter_num = int(math.ceil(states.shape[0] / optim_batch_size))
        for _ in range(optim_epochs):
            perm = np.arange(states.shape[0])
            np.random.shuffle(perm)
            perm = LongTensor(perm).to(device)

            states, actions, returns, advantages, fixed_log_probs = (
                states[perm].clone(),
                actions[perm].clone(),
                returns[perm].clone(),
                advantages[perm].clone(),
                fixed_log_probs[perm].clone(),
            )

            for i in range(optim_iter_num):
                ind = slice(
                    i * optim_batch_size,
                    min((i + 1) * optim_batch_size, states.shape[0]),
                )
                states_b, actions_b, advantages_b, returns_b, fixed_log_probs_b = (
                    states[ind],
                    actions[ind],
                    advantages[ind],
                    returns[ind],
                    fixed_log_probs[ind],
                )

                ppo_step(
                    policy_net,
                    value_net,
                    optimizer_policy,
                    optimizer_value,
                    1,
                    states_b,
                    actions_b,
                    returns_b,
                    advantages_b,
                    fixed_log_probs_b,
                    conf["clip_epsilon"],
                    conf["l2_reg"],
                )

    def main_loop():
        ppo_rewards = []
        best_model_from_iter = None
        for i_iter in range(conf["num_iters"]):
            """generate multiple trajectories that reach the minimum batch_size"""
            batch, log_train = agent.collect_samples(
                conf["min_batch_size"], render=conf["render"]
            )
            t0 = time.time()
            update_params(batch, i_iter)
            t1 = time.time()
            """evaluate with determinstic action (remove noise for exploration)"""
            _, log_eval = agent.collect_samples(
                conf["eval_batch_size"], mean_action=False
            )
            t2 = time.time()
            ppo_rewards.append(log_eval["avg_reward"])

            if max(ppo_rewards) == log_eval["avg_reward"]:
                torch.save(
                    policy_net,
                    os.path.join(".", f'{conf["exp"]["name"]}_random_policy_best.pt'),
                )
                best_model_from_iter = i_iter
                policy_net_best.load_state_dict(policy_net.state_dict())
                value_net_best.load_state_dict(value_net.state_dict())
            if (
                conf["save_model_interval"] > 0
                and (i_iter + 1) % conf["save_model_interval"] == 0
            ):
                if not os.path.exists(
                    os.path.join(
                        output_dir,
                        "learned_models",
                    )
                ):
                    os.makedirs(
                        os.path.join(
                            output_dir,
                            "learned_models",
                        )
                    )
                pickle.dump(
                    (policy_net_best, value_net_best, running_state),
                    open(
                        os.path.join(
                            output_dir,
                            "learned_models/{}_ppo.p".format(conf["env"]),
                        ),
                        "wb",
                    ),
                )

            if i_iter % conf["train_log_interval"] == 0:
                log.info(
                    "{}\tT_sample {:.4f}\tT_update {:.4f}\tT_eval {:.4f}\ttrain_R_min {:.2f}\ttrain_R_max {:.2f}\ttrain_R_avg {:.2f}\teval_R_avg {:.2f}\tbest_model_from_iter {}".format(
                        i_iter,
                        log_train["sample_time"],
                        t1 - t0,
                        t2 - t1,
                        log_train["min_reward"],
                        log_train["max_reward"],
                        log_train["avg_reward"],
                        log_eval["avg_reward"],
                        best_model_from_iter,
                    )
                )

            """clean up gpu memory"""
            torch.cuda.empty_cache()
        return ppo_rewards

    num_seeds = conf["num_seeds"]
    ppo_train_rewards = []

    """environment"""
    env_cls = ENVS[conf["env"]]
    env = env_cls(conf["env_config"])
    state_dim = env.observation_space.shape[0]
    is_disc_action = len(env.action_space.shape) == 0
    running_state = None

    """define actor and critic"""
    if conf["pretrained_path"] is None:
        if is_disc_action:
            policy_net = DiscretePolicy(state_dim, env.action_space.n, hidden_size=(conf["nn_size"],conf["nn_size"]))
            policy_net_best = DiscretePolicy(state_dim, env.action_space.n, hidden_size=(conf["nn_size"],conf["nn_size"]))
        else:
            policy_net = Policy(
                state_dim,
                env.action_space.shape[0],
                hidden_size=(conf["nn_size"],conf["nn_size"]),
                log_std=conf["log_std"],
                activation="sigmoid",
            )
            policy_net_best = Policy(
                state_dim,
                env.action_space.shape[0],
                hidden_size=(conf["nn_size"],conf["nn_size"]),
                log_std=conf["log_std"],
                activation="sigmoid",
            )
        value_net = Value(state_dim)
        value_net_best = Value(state_dim)
    else:
        policy_net, value_net, running_state = pickle.load(
            open(conf["pretrained_path"], "rb")
        )
        policy_net_best, value_net_best, running_state = pickle.load(
            open(conf["pretrained_path"], "rb")
        )
    torch.save(policy_net, os.path.join(output_dir, "policy_best.pt"))
    policy_net.to(device)
    value_net.to(device)

    optimizer_policy = torch.optim.Adam(
        policy_net.parameters(), lr=conf["learning_rate"]
    )
    optimizer_value = torch.optim.Adam(value_net.parameters(), lr=conf["learning_rate"])

    # optimization epoch number and batch size for PPO
    optim_epochs = 10
    optim_batch_size = 64

    """create agent"""
    agent = Agent(
        env,
        policy_net,
        device,
        running_state=running_state,
        num_threads=conf["num_threads"],
    )

    for seed in range(num_seeds):
        log.info(f"********* Training for seed {seed+1} *********")
        """environment"""
        env_cls = ENVS[conf["env"]]
        env = env_cls(conf["env_config"])
        env.cost_high_action = cost
        state_dim = env.observation_space.shape[0]
        is_disc_action = len(env.action_space.shape) == 0
        running_state = None

        """define actor and critic"""
        if conf["pretrained_path"] is None:
            if is_disc_action:
                policy_net = DiscretePolicy(state_dim, env.action_space.n,  hidden_size=(conf["nn_size"],conf["nn_size"]))
            else:
                policy_net = Policy(
                    state_dim,
                    env.action_space.shape[0],
                    log_std=conf["log_std"],
                    activation="sigmoid",
                )
            value_net = Value(state_dim)
        else:
            policy_net, value_net, running_state = pickle.load(
                open(conf["pretrained_path"], "rb")
            )
        policy_net.to(device)
        value_net.to(device)

        optimizer_policy = torch.optim.Adam(
            policy_net.parameters(), lr=conf["learning_rate"]
        )
        optimizer_value = torch.optim.Adam(
            value_net.parameters(), lr=conf["learning_rate"]
        )

        # optimization epoch number and batch size for PPO
        optim_epochs = 10
        optim_batch_size = 64

        """create agent"""
        agent = Agent(
            env,
            policy_net,
            device,
            running_state=running_state,
            num_threads=conf["num_threads"],
        )

        ppo_train_rewards.append(main_loop())
    return ppo_train_rewards

