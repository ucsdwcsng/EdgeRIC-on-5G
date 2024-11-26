import numpy as np
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd
import hydra
import os
import torch
import time

def visualize_neurwin_ppo(neurwin_curve,neurwin_xaxis,ppo_curve,cost,outdir):
    #hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = outdir
    print(ppo_curve,len(ppo_curve))
    fig_1 = go.Figure(
        [
            go.Scatter(
                name="PPO",
                x=np.arange(len(ppo_curve)),
                y=ppo_curve,
            ),
            go.Scatter(
                name="NeurWIN",
                x=neurwin_xaxis,
                y=neurwin_curve,
            ),
        ]
    )
    fig_1.update_layout(yaxis_title="Reward", title=f"Training Curve ; cost = {cost}", hovermode="x")
    fig_1.write_image(os.path.join(output_dir, f"neurwin_ppo_training_curve_cost_{cost}_mu_{0.0}.png"))

    


def visualize_neurwin_training(means, stds):
    means = np.array(means)
    syds = np.array(stds)
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = hydra_cfg["runtime"]["output_dir"]
    fig_1 = go.Figure(
        [
            go.Scatter(
                name="Reward",
                x=np.arange(len(means)),
                y=means,
                mode="lines",
                line=dict(color="rgb(31, 119, 180)"),
            ),
            go.Scatter(
                name="mean+std",
                x=np.arange(len(means)),
                y=means + stds,
                mode="lines",
                marker=dict(color="#444"),
                line=dict(width=0),
                showlegend=False,
            ),
            go.Scatter(
                name="mean-std",
                x=np.arange(len(means)),
                y=means - stds,
                marker=dict(color="#444"),
                line=dict(width=0),
                mode="lines",
                fillcolor="rgba(68, 68, 68, 0.3)",
                fill="tonexty",
                showlegend=False,
            ),
        ]
    )
    fig_1.update_layout(yaxis_title="Reward", title="Training Curve", hovermode="x")
    # try:
    #     fig_1.show()
    # except:
    #     pass
    # Save image to output dir
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = hydra_cfg["runtime"]["output_dir"]
    fig_1.write_image(os.path.join(output_dir, "aneurwin_training_curve.pdf"))
    # df_train.to_csv(
    #     os.path.join(output_dir, "training_curve.csv"), header=True, index=False
    # )


def visualize_policy_cqi(model_dir=None):
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = hydra_cfg["runtime"]["output_dir"]
    if not model_dir:
        model_dir = os.path.join(output_dir, "policy_best.pt")
    model = torch.load(model_dir)
    model.to("cpu")
    model.eval()

    cqis = np.arange(16)
    allocated_RBG = np.zeros((16, 16))
    bl_1 = bl_2 = 150000
    for cqi_1 in cqis:
        for cqi_2 in cqis:
            obs = np.array(
                [bl_1 / 300000, cqi_1 / 15, bl_2 / 300000, cqi_2 / 15], dtype=np.float32
            )
            obs = torch.from_numpy(obs)
            obs = torch.unsqueeze(obs, dim=0)
            with torch.no_grad():
                try:
                    action = torch.squeeze(model.select_action(obs))
                except RuntimeError:
                    obs = np.array(
                        [
                            bl_1 / 300000,
                            cqi_1 / 15,
                            bl_1 * cqi_1 / (300000 * 15),
                            bl_2 / 300000,
                            cqi_2 / 15,
                            bl_2 * cqi_2 / (300000 * 15),
                        ],
                        dtype=np.float32,
                    )
                    obs = torch.from_numpy(obs)
                    obs = torch.unsqueeze(obs, dim=0)
                    action = torch.squeeze(model.select_action(obs))
            action = np.clip(action, a_min=0.00000001, a_max=1.0)
            percentage_RBG = action[0] / sum(action)
            allocated_RBG[cqi_2][cqi_1] = np.round(percentage_RBG * 17)

    fig = go.Figure(data=[go.Surface(x=cqis, y=cqis, z=allocated_RBG)])
    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=1.55, y=1.55, z=1.55),
    )
    fig.update_layout(
        title="Policy (CQI)",
        scene=dict(
            xaxis_title="UE1 CQI",
            yaxis_title="UE2 CQI",
            zaxis_title="UE1 Allocated RBGs",
        ),
        scene_camera=camera,
    )
    if not os.path.exists(os.path.join(output_dir, "policy_visualizations")):
        os.makedirs(os.path.join(output_dir, "policy_visualizations"))
    fig.write_image(os.path.join(output_dir, "policy_visualizations/policy_cqi.pdf"))
    fig.write_html(os.path.join(output_dir, "policy_visualizations/policy_cqi.html"))
    try:
        fig.show()
    except:
        pass


import torch.nn as nn
import torch.nn.functional as F

class fcnn(nn.Module):
    """Fully-Connected Neural network for NEURWIN to modify its parameters"""

    def __init__(self, stateSize):
        super(fcnn, self).__init__()
        self.linear1 = nn.Linear(stateSize, 16, bias=True)
        self.linear2 = nn.Linear(16, 4)
        self.linear3 = nn.Linear(4, 1, bias=True)

    def forward(self, x):
        x = torch.FloatTensor(x)
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


def visualize_whittle_function(agent, model_dir, normalizer):
    agent.nn.load_state_dict(torch.load(model_dir + "/trained_model.pt"))
    #model.load_state_dict(torch.load(model_dir+ "/trained_model.pt"))
    # model.to("cpu")
    agent.nn.eval()
    step = 1000
    bls = np.arange(0, 300000 + step, step)
    cqis = 5 #np.arange(1, 16)
    whittle_indices = np.zeros((len(bls)))
    for bl_1 in bls:
        #for cqi in cqis:
            cqi = 5
            obs = np.array([bl_1/300000, cqi], dtype=np.float32)
            obs = obs / normalizer
            obs = torch.from_numpy(obs)
            obs = torch.unsqueeze(obs, dim=0)
            with torch.no_grad():
                whittle_indices[bl_1 // step] = torch.squeeze(
                    agent.nn.forward(obs)
                )
    print(
        whittle_indices.max(),
        whittle_indices.argmax(),
        whittle_indices.min(),
        whittle_indices.argmin(),
        whittle_indices,
    )
    print(len(bls),len(whittle_indices))
    #fig = go.Figure([go.scatter(x=bls, y=whittle_indices)])
    # camera = dict(
    #     up=dict(x=0, y=1),
    #     center=dict(x=0, y=0),
    #     eye=dict(x=1.55, y=1.55),
    # )
    
    # if not os.path.exists(os.path.join(output_dir, "policy_visualizations")):
    #     os.makedirs(os.path.join(output_dir, "policy_visualizations"))
    # fig.write_image(os.path.join(output_dir, "policy_visualizations/policy_bl.pdf"))
    # fig.write_html(os.path.join(output_dir, "policy_visualizations/policy_bl.html"))
    # try:
    #     fig.show()
    # except:
    #     pass
    #     print("Failed to show()")
    # hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    # output_dir = hydra_cfg["runtime"]["output_dir"]
    fig = go.Figure(
        [
            go.Scatter(
                name="Reward",
                x=bls,
                y=whittle_indices,
                mode="lines",
                line=dict(color="rgb(31, 119, 180)"),
            ),
        ]
    )
    fig.update_layout(yaxis_title="whittle index",xaxis_title="UE1 Backlog Buffer", title="whittle function", hovermode="x")
    fig.show()
    print(model_dir)
    print("plotting whittle function")
    fig.write_image(os.path.join(model_dir, "awhittle_func_learnt.jpg"))
    fig.write_html(os.path.join(model_dir, "awhittle_func_learnt.html"))


def visualize_policy_backlog_len(model_dir=None):
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = hydra_cfg["runtime"]["output_dir"]
    if not model_dir:
        model_dir = os.path.join(output_dir, "policy_best.pt")
    model = torch.load(model_dir)
    model.to("cpu")
    model.eval()
    step = 10000
    bls = np.arange(0, 300000 + step, step)
    allocated_RBG = np.zeros((len(bls), len(bls)))
    cqi_1 = cqi_2 = 9
    for bl_1 in bls:
        for bl_2 in bls:
            obs = np.array(
                [bl_1 / 300000, cqi_1 / 15, bl_2 / 300000, cqi_2 / 15], dtype=np.float32
            )
            obs = torch.from_numpy(obs)
            obs = torch.unsqueeze(obs, dim=0)
            with torch.no_grad():
                try:
                    action = torch.squeeze(model.select_action(obs))
                except RuntimeError:
                    obs = np.array(
                        [
                            bl_1 / 300000,
                            cqi_1 / 15,
                            bl_1 * cqi_1 / (300000 * 15),
                            bl_2 / 300000,
                            cqi_2 / 15,
                            bl_2 * cqi_2 / (300000 * 15),
                        ],
                        dtype=np.float32,
                    )
                    obs = torch.from_numpy(obs)
                    obs = torch.unsqueeze(obs, dim=0)
                    action = torch.squeeze(model.select_action(obs))
            action = np.clip(action, a_min=0.00000001, a_max=1.0)
            percentage_RBG = action[0] / sum(action)
            allocated_RBG[(bl_2 // step)][(bl_1 // step)] = np.round(
                percentage_RBG * 17
            )

    fig = go.Figure(data=[go.Surface(x=bls, y=bls, z=allocated_RBG)])
    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=1.55, y=1.55, z=1.55),
    )
    fig.update_layout(
        title="Policy (Backlog len)",
        scene=dict(
            xaxis_title="UE1 Backlog",
            yaxis_title="UE2 Backlog",
            zaxis_title="UE1 Allocated RBGs",
        ),
        scene_camera=camera,
    )
    if not os.path.exists(os.path.join(output_dir, "policy_visualizations")):
        os.makedirs(os.path.join(output_dir, "policy_visualizations"))
    fig.write_image(os.path.join(output_dir, "policy_visualizations/policy_bl.pdf"))
    fig.write_html(os.path.join(output_dir, "policy_visualizations/policy_bl.html"))
    try:
        fig.show()
    except:
        pass


def visualize_edgeric_training(train_rewards):
    train_rewards = np.array(train_rewards)
    means = np.mean(train_rewards, axis=0)
    stds = np.std(train_rewards, axis=0)
    df_train = pd.DataFrame(
        list(zip(range(len(means)), means, stds)),
        columns=["train_step", "reward_mean", "reward_std"],
    )
    fig_1 = go.Figure(
        [
            go.Scatter(
                name="Reward",
                x=df_train["train_step"],
                y=df_train["reward_mean"],
                mode="lines",
                line=dict(color="rgb(31, 119, 180)"),
            ),
            go.Scatter(
                name="mean+std",
                x=df_train["train_step"],
                y=df_train["reward_mean"] + df_train["reward_std"],
                mode="lines",
                marker=dict(color="#444"),
                line=dict(width=0),
                showlegend=False,
            ),
            go.Scatter(
                name="mean-std",
                x=df_train["train_step"],
                y=df_train["reward_mean"] - df_train["reward_std"],
                marker=dict(color="#444"),
                line=dict(width=0),
                mode="lines",
                fillcolor="rgba(68, 68, 68, 0.3)",
                fill="tonexty",
                showlegend=False,
            ),
        ]
    )
    fig_1.update_layout(yaxis_title="Reward", title="Training Curve", hovermode="x")
    try:
        fig_1.show()
    except:
        pass
    # Save image to output dir
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = hydra_cfg["runtime"]["output_dir"]
    fig_1.write_image(os.path.join(output_dir, "training_curve.pdf"))
    df_train.to_csv(
        os.path.join(output_dir, "training_curve.csv"), header=True, index=False
    )


def visualize_edgeric_evaluation(
    ppo_agent_rewards,
    max_cqi_agent_rewards,
    max_pressure_agent_rewards,
    max_pressure_chakareski_agent_rewards,
):
    df_eval = pd.DataFrame(
        list(
            zip(
                range(len(ppo_agent_rewards)),
                ppo_agent_rewards,
                max_pressure_agent_rewards,
                max_pressure_chakareski_agent_rewards,
                max_cqi_agent_rewards,
            )
        ),
        columns=[
            "eval_episode",
            "PPO",
            "MaxPressure",
            "MaxPressureChakareski",
            "MaxCQI",
        ],
    ).melt(
        id_vars=["eval_episode"],
        value_vars=["PPO", "MaxCQI", "MaxPressure", "MaxPressureChakareski"],
        var_name="Agent",
        value_name="Reward",
    )
    fig_2 = px.line(
        df_eval, x="eval_episode", y="Reward", color="Agent", title="Evaluation"
    )
    try:
        fig_2.show()
    except:
        pass
    # Save image to output dir
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = hydra_cfg["runtime"]["output_dir"]
    fig_2.write_image(os.path.join(output_dir, "evaluation_curve.pdf"))
    df_eval.to_csv(
        os.path.join(output_dir, "evaluation_curve.csv"), header=True, index=False
    )


def plot_cdf(data):
    df_data = pd.DataFrame(data, columns=["forward_pass_time"])
    fig = px.ecdf(df_data, x="forward_pass_time")
    try:
        fig.show()
    except:
        pass
    # Save image to output dir
    hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
    output_dir = hydra_cfg["runtime"]["output_dir"]
    fig.write_image(os.path.join(output_dir, "fwd_pass_times.pdf"))


def plot_training(path_to_data, filename):
    df_train = pd.read_csv(os.path.join(path_to_data, filename))
    fig_1 = go.Figure(
        [
            go.Scatter(
                name="Reward",
                x=df_train["train_step"],
                y=df_train["reward_mean"],
                mode="lines",
                line=dict(color="rgb(31, 119, 180)"),
            ),
            go.Scatter(
                name="mean+std",
                x=df_train["train_step"],
                y=df_train["reward_mean"] + df_train["reward_std"],
                mode="lines",
                marker=dict(color="#444"),
                line=dict(width=0),
                showlegend=False,
            ),
            go.Scatter(
                name="mean-std",
                x=df_train["train_step"],
                y=df_train["reward_mean"] - df_train["reward_std"],
                marker=dict(color="#444"),
                line=dict(width=0),
                mode="lines",
                fillcolor="rgba(68, 68, 68, 0.3)",
                fill="tonexty",
                showlegend=False,
            ),
        ]
    )
    fig_1.update_layout(yaxis_title="Reward", title="Training Curve", hovermode="x")
    try:
        fig_1.show()
    except:
        pass
    # Save image to output dir
    plotname = filename.split(".")[0]
    fig_1.write_image(
        os.path.join(path_to_data, f"{plotname}.pdf"),
        format="pdf",
    )
    time.sleep(2)
    fig_1.write_image(
        os.path.join(path_to_data, f"{plotname}.pdf"),
        format="pdf",
    )
    fig_1.write_html(os.path.join(path_to_data, f"{plotname}.html"))


def plot_edgeric_evaluation(path_to_data, filename):
    df_eval = pd.read_csv(os.path.join(path_to_data, filename))
    fig_2 = px.line(
        df_eval, x="eval_episode", y="Reward", color="Agent", title="Evaluation"
    )
    try:
        fig_2.show()
    except:
        pass
    # Save image to output dir
    fig_2.write_image(os.path.join(path_to_data, f"{filename}.pdf"))
    df_eval.to_csv(
        os.path.join(output_dir, "evaluation_curve.csv"), header=True, index=False
    )


def plot_cqi_trace(path_to_data, cqi_scenario, filename):
    pass


def plot_cqi_cdf(path_to_data, cqi_scenario, filename):
    pass

def read_values_from_file(file_path):
    with open(file_path, 'r') as file:
        return [float(line.strip()) for line in file]

def main():
    COST_VALUES=[29.32]
    base_dir_ppo = "/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/myoutputs/ppo_embb"
    base_dir_neurwin = "/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/myoutputs/neurwin_embb"

    for cost in COST_VALUES:
        file_ppo = os.path.join(base_dir_ppo, f"ppo_{cost}.txt")
        file_neurwin = os.path.join(base_dir_neurwin, f"neurwin_{cost}.txt")

        ppo_values = read_values_from_file(file_ppo)
        neurwin_values = read_values_from_file(file_neurwin)

        output_directory = "/home/wcsng-24/gitrepos/EdgeRIC_indexing/EdgeRIC_rl_emulator/myoutputs/embb_plots"
        episode = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        visualize_neurwin_ppo(neurwin_values, episode, ppo_values, cost, output_directory)

if __name__ == "__main__":
    main()