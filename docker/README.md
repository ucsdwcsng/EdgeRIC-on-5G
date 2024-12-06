# Multi-Container Solution

This folder contains a multi-container application (development mode), composed of:

- srsRAN gnb: it will build and run the srsRAN network, gnb and UEs.
- Open5g core: an open source core to use with srsRAN gnb.
- EdgeRIC - the realtime RAN controller.
- Prometheus - Database for Grafana
- Grafana - Container for the dashboard application  

## Start the containers 
 
**Terminal 0: Launch the open5gs Core Network** 
```bash
docker-compose up --build 5gc
```
**Terminal 1: Connect your network to the internet**  
```bash
docker exec -it open5gs_5gc bash
sysctl -w net.ipv4.ip_forward=1
iptables -t nat -A POSTROUTING -s 10.45.1.0/16 ! -o ogstun -j MASQUERADE
```

**Terminal 2: Start the Radio Access Network container** 
```bash
docker-compose up gnb
```
**Terminal 3: Start the EdgeRIC container** 
```bash
docker-compose up edgeric
```
# Run the network
The following steps will guide you to run a 2UE network in the virtual radio mode   

You need to run the following from inside the srsRAN gnb container

**Terminal 3: Build srsRAN**
```bash
docker exec -it srsran_gnb bash
./make_ran_er.sh
```
Once built, Start the GNU radio flowgraph in the same terminal
```bash
python3 2ue-zmq-mode-23.04Mhz-nogui.py # for 2ues, to run 4ues - run python3 4ue-zmq-mode-23.04Mhz-nogui.py
```
**Known Issue - Look out for**
```bash
sudo lsof -i :5555
sudo lsof -i :5556
sudo lsof -i :5557
```
Make sure to kill all these in case it is still active ``sudo kill -9 <PID>``    

**Terminal 4: Run the RAN**
```bash
docker exec -it srsran_gnb bash
./run_gnb_multi_ue.sh
```
Press ``t`` to see the console trace  

**Terminal 5: Run the UEs**
```bash
docker exec -it srsran_gnb bash
./run2ue-zmq-mode.sh # for 2ues, to run 4ues - run ./run4ue-zmq-mode.sh
```
The ip addresses assigned to UEs will be 10.45.1.2/24, to run any traffic originating from ues, you need run it from their namespaces ``ip netns exec ue{i}``    
The srsRAN gnb container starts up with 4 UE namespaces, to run more UEs, you need to add more, with command ``ip netns add``

# Run Traffic

For downlink traffic, start the traffic server on the UEs:  
**Terminal 6: start iperf server at the UEs**  
```bash
docker exec -it srsran_gnb bash
cd traffic-generator
./iperf_server_2ues.sh 
```
**Terminal 7: Start iperf client for UE1**  
To run traffic from the open5gs CN container, you have to use ``docker exec -it open5gs_5gc``  
```bash
docker exec -it open5gs_5gc iperf -c 10.45.1.2 -u -i 1 -b 10M -t 1000
```
**Terminal 8: Start iperf client for UE2**  
```bash
docker exec -it open5gs_5gc iperf -c 10.45.1.3 -u -i 1 -b 10M -t 1000
```

# Try out EdgeRIC muApps
You need to run the following from inside the srsRAN gnb container ``docker exec -it edgeric_v2 bash``  

**Known Issue - Look out for**  
```bash
sudo lsof -i :5555
sudo lsof -i :5556
sudo lsof -i :5557
```
Make sure to kill all these in case it is still active ``sudo kill -9 <PID>``   

## muApp1: Run the scheduling muApp
**Terminal 9: Set the scheduling algorithm**  
```bash
docker exec -it edgeric_v2 bash
redis-cli set scheduling_algorithm "Max CQI" # Other options "Proportional Fair"
                                             # "Max Weight", "Round Robin", "RL"
```
**Terminal 10: Start the muApp** 
```bash
docker exec -it edgeric_v2 bash
cd muApp1
python3 muApp1_run_DL_scheduling.py
```
### What to observe 
Terminal 10 will show the algorithms selected and will print the total average system throughput observed
```bash
Algorithm index:  2  ,  Max Weight
total system throughput: 8.781944 

Algorithm index:  2  ,  Max Weight
total system throughput: 8.063600000000001 

Algorithm index:  2  ,  Max Weight
total system throughput: 8.093352 

Algorithm index:  2  ,  Max Weight
total system throughput: 8.071168 
```
**Terminal 9** - To observe the throughput updates, update the scheduler with the following command 
```bash
redis-cli set scheduling_algorithm "RL" 
```

**Terminal 10** - Increased system throughput observed with our trained RL model
```bash
Algorithm index:  20  ,  RL
Executing RL model at: ./rl_model/fully_trained_model
total system throughput: 12.071200000000001 

Algorithm index:  20  ,  RL
Executing RL model at: ./rl_model/fully_trained_model
total system throughput: 11.727624 

Algorithm index:  20  ,  RL
Executing RL model at: ./rl_model/fully_trained_model
total system throughput: 11.714879999999999 

Algorithm index:  20  ,  RL
Executing RL model at: ./rl_model/fully_trained_model
total system throughput: 11.710384 

Algorithm index:  20  ,  RL
Executing RL model at: ./rl_model/fully_trained_model
total system throughput: 11.743776 
```

## muApp3 - Running the Monitoring muApp
This muApp will help us see the RT-E2 Report Message from the RAN and the RT-E2 Policy message sent to RAN  

```bash
docker exec -it edgeric_v2 bash
cd muApp3
python3 muApp3_monitor_terminal.py 
```
**What to observe**  
```bash
RT-E2 Report: 

RAN Index: 791000, RIC index: 790998 

UE Dictionary: {70: {'CQI': 7, 'SNR': 115.46858215332031, 'Backlog': 384977, 'Pending Data': 0, 'Tx_brate': 1980.0, 'Rx_brate': 0.0}, 71: {'CQI': 8, 'SNR': 116.41766357421875, 'Backlog': 1503, 'Pending Data': 0, 'Tx_brate': 0.0, 'Rx_brate': 0.0}} 

```

## Try out fixed weight scheduling and MCS control - Build your policies on top of these helper files
Edit the python files to chose fixed scheduling and mcs actions  
```bash
docker exec -it edgeric_v2 bash
python3 send_mcs.py
```

```bash
docker exec -it edgeric_v2 bash
sudo python3 send_weight.py
```
**What will you see**
```bash
RT-E2 Policy (Scheduling): 
Sent to RAN: ran_index: 790999
weights: 70.0
weights: 0.7
weights: 71.0
weights: 0.3
```

# Dashboard Support with Grafana
## Prometheus and Grafana
Start the prometheus data base and the grafana dashboard containers
```bash
cd prometheus
docker compose up prometheus
```

```bash
cd grafana
docker compose up grafana
```
## Create the Docker network between edgeric, prometheus and grafana
```bash
docker network create monitoring
docker network connect monitoring prometheus
docker network connect monitoring edgeric_v2
docker network connect monitoring grafana
```
check https://localhost:3000 web whether Grafana can run correctly  

## Pulling Metrics with edgeric rt-e2 agent 
From the edgeric container, start the monitoring_grafana muApp 
```bash
docker exec -it edgeric_v2 bash
cd muApp3
python3 muApp3_monitor_grafana.py
```
check https://localhost:9090 web whether Prometheus can run correctly  
check https://localhost:8000 - edgeric muApp writes the metrics here, for Prometheus  

## Opening the Dashboard 
Step 1: https://localhost:3000 - Dashboard  
Step 2: Import the dashboard provided in the repository - located in ``grafana/dashboard.json``  
Step 3: Add data source   


### TODO: how to add subsribers, sim card provisioning 
