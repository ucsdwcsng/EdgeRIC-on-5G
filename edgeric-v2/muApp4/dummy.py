while not done:
    ran_tti, ue_data = edgeric_messenger.get_metrics(False)
    numues = len(ue_data)
    weight = np.zeros(numues * 2)
    RNTIs = list(ue_data.keys())
    BLs, txb, CQIs = [data['dl_buffer'], data['dl_tbs'], data['cqi'] for data in ue_data.values()]  
    action = {}
    for i in range(len(RNTIs)):
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

    action = get_whittle_action(indices) 
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
    edgeric_messenger.send_scheduling_weight(edgeric_messenger.ran_tti, weight, False)