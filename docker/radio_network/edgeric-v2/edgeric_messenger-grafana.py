
### Updated `edgeric_messenger.py`

import zmq
import time
import control_mcs_pb2
import control_weights_pb2
import metrics_pb2
import random

#########################
from prometheus_client import start_http_server, Gauge
import threading
#########################

class EdgericMessenger:
    def __init__(self, socket_type):
        self.context = zmq.Context()

        # Create a subscriber socket to receive from RAN
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages
        self.subscriber.setsockopt(zmq.CONFLATE, 1)  # Set the socket to conflate mode
        self.subscriber.connect("ipc:///tmp/metrics")  # Connect to the IPC address for metrics (5551)

        self.socket_type = socket_type

        if socket_type == "weights":
            # Create a publisher socket for SchedulingWeights
            self.publisher_socket = self.context.socket(zmq.PUB)
            self.publisher_socket.bind("ipc:///tmp/control_weights_actions")  # Bind to the IPC address for weights (5552)
        elif socket_type == "mcs":
            # Create a publisher socket for MCS
            self.publisher_socket = self.context.socket(zmq.PUB)
            self.publisher_socket.bind("ipc:///tmp/control_mcs_actions")  # Bind to the IPC address for MCS (5553)

        self.ue_dict = {}
        self.ran_tti = 0

    def get_metrics(self, flag_print):
        tti_count = 0
        try:
            # Receive the message
            message = self.subscriber.recv()
            # Parse the received message using Protobuf
            metrics = metrics_pb2.Metrics()
            metrics.ParseFromString(message)
            # Store the TTI count
            tti_count = metrics.tti_cnt
            self.ran_tti = tti_count
            # Store the details for each UE in the dictionary
            self.ue_dict = {ue_metrics.rnti: {
                "cqi": ue_metrics.cqi,
                "snr": ue_metrics.snr,
                "tx_bytes": ue_metrics.tx_bytes,
                "rx_bytes": ue_metrics.rx_bytes,
                "dl_buffer": ue_metrics.dl_buffer,
                "ul_buffer": ue_metrics.ul_buffer,
                "dl_tbs": ue_metrics.dl_tbs
            } for ue_metrics in metrics.ue_metrics}

            # Print the TTI count and UE metrics dictionary for debugging
            if (tti_count % 1000 == 0 and flag_print):
                print("RT-E2 Report: \n")
                print(f"TTI Count: {self.ran_tti}")
                print(f"UE Metrics: {self.ue_dict}")

        except KeyboardInterrupt:
            print("Interrupted")

        return self.ran_tti, self.ue_dict

    def send_scheduling_weight(self, tti_count, weights, flag_print):
        # Create an instance of the SchedulingWeights message
        msg = control_weights_pb2.SchedulingWeights()
        msg.ran_index = tti_count  # Example index based on TTI count
        msg.weights.extend(weights)

        # Serialize the message to a string
        serialized_msg = msg.SerializeToString()

        # Send the serialized message over ZMQ
        self.publisher_socket.send(serialized_msg)

        if (msg.ran_index % 1000 == 0 and flag_print):
            print("RT-E2 Policy (Scheduling): \n")
            print(f"Sent to RAN: {msg} \n")

    def send_mcs(self, tti_count, mcs_array, flag_print):
        # Create an instance of the mcs_control message
        msg = control_mcs_pb2.mcs_control()
        msg.ran_index = tti_count  # Example index based on TTI count
        msg.mcs.extend(mcs_array)

        # Serialize the message to a string
        serialized_msg = msg.SerializeToString()

        # Send the serialized message over ZMQ
        self.publisher_socket.send(serialized_msg)

        if (msg.ran_index % 1000 == 0 and flag_print):
            print("RT-E2 Policy (MCS): \n")
            print(f"Sent to RAN: {msg} \n")

    #########################
    def update_prometheus_metrics(self):
        while True:
            tti_count = self.ran_tti
            ue_dict = self.ue_dict
            #tti_count, ue_dict = self.get_metrics(flag_print=False)
            self.tti_count_gauge.set(tti_count)  # Set the TTI count
            for rnti, metrics in ue_dict.items():
                self.cqi_gauge.labels(rnti=rnti).set(metrics['cqi'])
                self.snr_gauge.labels(rnti=rnti).set(metrics['snr'])
                self.dl_bytes_gauge.labels(rnti=rnti).set(metrics['tx_bytes'])
                self.ul_bytes_gauge.labels(rnti=rnti).set(metrics['rx_bytes'])
                self.dl_buffer_gauge.labels(rnti=rnti).set(metrics['dl_buffer'])
                self.ul_buffer_gauge.labels(rnti=rnti).set(metrics['ul_buffer'])
                self.dl_tbs_gauge.labels(rnti=rnti).set(metrics['dl_tbs'])
            time.sleep(1)

        # while (True):
        #     tti_count, ue_dict = self.get_metrics(flag_print=False)
        #     self.tti_count_gauge.set(tti_count)  # Set the TTI count
        #     print("Hi!")
        #     for rnti, metrics in ue_dict.items():
        #          self.cqi_gauge.labels(rnti=rnti).set(metrics['cqi'])
        #          self.snr_gauge.labels(rnti=rnti).set(metrics['snr'])
        #          self.dl_bytes_gauge.labels(rnti=rnti).set(metrics['tx_bytes'])
        #          self.ul_bytes_gauge.labels(rnti=rnti).set(metrics['rx_bytes'])
        #          self.dl_buffer_gauge.labels(rnti=rnti).set(metrics['dl_buffer'])
        #          self.ul_buffer_gauge.labels(rnti=rnti).set(metrics['ul_buffer'])
        #          self.dl_tbs_gauge.labels(rnti=rnti).set(metrics['dl_tbs'])
        #     time.sleep(25)  # Update every second
    #########################

    #########################
    def start_prometheus_metrics(self, port=8000):
        # Initialize Prometheus metrics
        self.cqi_gauge = Gauge('ue_cqi', 'UE Channel Quality Indicator', ['rnti'])
        self.snr_gauge = Gauge('ue_snr', 'UE Signal-to-Noise Ratio', ['rnti'])
        self.dl_bytes_gauge = Gauge('ue_dl_bytes', 'UE Downlink Bytes', ['rnti'])
        self.ul_bytes_gauge = Gauge('ue_ul_bytes', 'UE Uplink Bytes', ['rnti'])
        self.dl_buffer_gauge = Gauge('ue_dl_buffer', 'UE Downlink Buffer', ['rnti'])
        self.ul_buffer_gauge = Gauge('ue_ul_buffer', 'UE Uplink Buffer', ['rnti'])
        self.dl_tbs_gauge = Gauge('ue_dl_tbs', 'UE Downlink TBS', ['rnti'])
        self.tti_count_gauge = Gauge('ran_tti_count', 'RAN TTI Count')
        # Start Prometheus HTTP server
        start_http_server(port)
        # Start a thread to continuously update Prometheus metrics
        self.prometheus_thread = threading.Thread(target=self.update_prometheus_metrics)
        self.prometheus_thread.daemon = True
        self.prometheus_thread.start()
    #########################


agent = EdgericMessenger("mcs")

#########################

# agent.start_prometheus_metrics(port=9090)
#########################

# i=0
# while(1):
#     i=i+1
#     if (i % 1000 == 0):
#         agent.get_metrics(1)
#     else:
#         agent.get_metrics(0)
#     a="r"


#     if (i % 90000 == 0):
#         input("continue?")
#     if (a=="n") :
#         break

#########################

agent.start_prometheus_metrics(port=8000)
#########################

i=0
while(1):
    i=i+1
    agent.get_metrics(1)
    # if (i % 1000 == 0):
    #     agent.get_metrics(1)
    # else:
    #     agent.get_metrics(0)

