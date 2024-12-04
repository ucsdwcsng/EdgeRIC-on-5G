import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from edgeric_messenger import EdgericMessenger
import threading
import time
import numpy as np

#########################
from prometheus_client import start_http_server, Gauge
import threading
#########################

class PrometheusMonitor:
    def __init__(self, port=8000):

        self.messenger = EdgericMessenger("")

        self.port = port
        self.ue_dict = {}
        self.tx_bytes_history = {}
        self.rx_bytes_history = {}
        self.dl_buffer_history = {}
        self.ul_buffer_history = {}
        self.first_tti = {}

        # Initialize Prometheus metrics
        self.cqi_gauge = Gauge('ue_cqi', 'UE Channel Quality Indicator', ['rnti'])
        self.snr_gauge = Gauge('ue_snr', 'UE Signal-to-Noise Ratio', ['rnti'])
        #self.dl_bytes_gauge = Gauge('ue_dl_bytes', 'UE Downlink Bytes', ['rnti'])
        #self.ul_bytes_gauge = Gauge('ue_ul_bytes', 'UE Uplink Bytes', ['rnti'])
        #self.dl_buffer_gauge = Gauge('ue_dl_buffer', 'UE Downlink Buffer', ['rnti'])
        #self.ul_buffer_gauge = Gauge('ue_ul_buffer', 'UE Uplink Buffer', ['rnti'])
        #self.dl_tbs_gauge = Gauge('ue_dl_tbs', 'UE Downlink TBS', ['rnti'])
        #self.tti_count_gauge = Gauge('ran_tti_count', 'RAN TTI Count')
        self.avg_dl_buffer_gauge = Gauge('ue_avg_dl_buffer', 'UE Average DL Buffer', ['rnti'])
        self.avg_ul_buffer_gauge = Gauge('ue_avg_ul_buffer', 'UE Average UL Buffer', ['rnti'])
        self.avg_tx_throughput_gauge = Gauge('ue_avg_tx_throughput', 'UE Average TX Throughput', ['rnti'])
        self.avg_rx_throughput_gauge = Gauge('ue_avg_rx_throughput', 'UE Average RX Throughput', ['rnti'])
        

        self.avg_tot_dl_buffer_gauge = Gauge('tot_avg_dl_buffer', 'tot Average DL Buffer', ['non'])
        self.avg_tot_ul_buffer_gauge = Gauge('tot_avg_ul_buffer', 'tot Average UL Buffer', ['non'])
        self.avg_tot_tx_throughput_gauge = Gauge('tot_avg_tx_throughput', 'tot Average TX Throughput', ['non'])
        self.avg_tot_rx_throughput_gauge = Gauge('tot_avg_rx_throughput', 'tot Average RX Throughput', ['non'])
        
        start_http_server(self.port)


    def update_metrics(self):
        while True:
            self.tti_count, self.ue_dict = self.messenger.get_metrics(True)
            #self.tti_count_gauge.set(self.ran_tti)
            avg_tx_throughput_tot=[]
            avg_rx_throughput_tot=[]
            avg_dl_buffer_tot=[]
            avg_ul_buffer_tot=[]
            for rnti, metrics in self.ue_dict.items():
                if rnti not in self.first_tti.keys():
                    #print("hiiii")
                    self.first_tti[rnti] = self.tti_count
                    #print(self.first_tti)
                avg_tx_throughput, avg_rx_throughput, avg_dl_buffer, avg_ul_buffer = self.calculate_moving_avg(rnti=rnti,metrics=metrics)
                
                avg_tx_throughput_tot.append(avg_tx_throughput)
                avg_rx_throughput_tot.append(avg_rx_throughput)
                avg_dl_buffer_tot.append(avg_dl_buffer)
                avg_ul_buffer_tot.append(avg_ul_buffer)

                self.cqi_gauge.labels(rnti=rnti).set(metrics['cqi'])
                self.snr_gauge.labels(rnti=rnti).set(metrics['snr'])
                self.avg_tx_throughput_gauge.labels(rnti=rnti).set(avg_tx_throughput)
                self.avg_rx_throughput_gauge.labels(rnti=rnti).set(avg_rx_throughput)
                self.avg_dl_buffer_gauge.labels(rnti=rnti).set(avg_dl_buffer)
                self.avg_ul_buffer_gauge.labels(rnti=rnti).set(avg_ul_buffer)

            self.avg_tot_tx_throughput_gauge.labels(non=1).set(sum(avg_tx_throughput_tot))
            self.avg_tot_rx_throughput_gauge.labels(non=1).set(sum(avg_rx_throughput_tot))
            self.avg_tot_dl_buffer_gauge.labels(non=1).set(sum(avg_dl_buffer_tot))
            self.avg_tot_ul_buffer_gauge.labels(non=1).set(sum(avg_dl_buffer_tot))
                # self.dl_bytes_gauge.labels(rnti=rnti).set(metrics['tx_bytes'])
                # self.ul_bytes_gauge.labels(rnti=rnti).set(metrics['rx_bytes'])
                # self.dl_buffer_gauge.labels(rnti=rnti).set(metrics['dl_buffer'])
                # self.ul_buffer_gauge.labels(rnti=rnti).set(metrics['ul_buffer'])
                # self.dl_tbs_gauge.labels(rnti=rnti).set(metrics['dl_tbs'])

            

    def calculate_moving_avg(self, rnti, metrics):
      
        if rnti not in self.tx_bytes_history:
            self.tx_bytes_history[rnti] = []
        tx_bytes = metrics['tx_bytes']
        self.tx_bytes_history[rnti].append(tx_bytes)

        if rnti not in self.rx_bytes_history:
            self.rx_bytes_history[rnti] = []
        rx_bytes = metrics['rx_bytes']
        self.rx_bytes_history[rnti].append(rx_bytes)

        if rnti not in self.dl_buffer_history:
            self.dl_buffer_history[rnti] = []
        dl_buffer = metrics['dl_buffer']
        self.dl_buffer_history[rnti].append(dl_buffer)

        if rnti not in self.ul_buffer_history:
            self.ul_buffer_history[rnti] = []
        ul_buffer = metrics['ul_buffer']
        self.ul_buffer_history[rnti].append(ul_buffer)

        if (self.tti_count - self.first_tti[rnti]) >= 2000:
            total_time = 2
            total_tx_bytes = sum(self.tx_bytes_history[rnti])
            total_rx_bytes = sum(self.rx_bytes_history[rnti])
            total_dl_buffer = sum(self.dl_buffer_history[rnti])
            total_ul_buffer = sum(self.ul_buffer_history[rnti])
            avg_tx_throughput = (total_tx_bytes * 8) / total_time
            avg_rx_throughput = (total_rx_bytes * 8) / total_time
            avg_dl_buffer = (total_dl_buffer * 8) / total_time
            avg_ul_buffer = (total_ul_buffer * 8) / total_time
            self.tx_bytes_history[rnti].pop(0)
            self.rx_bytes_history[rnti].pop(0)
            self.dl_buffer_history[rnti].pop(0)
            self.ul_buffer_history[rnti].pop(0)
            #print(avg_tx_throughput,metrics['tx_bytes'])
        else:
            avg_tx_throughput = 0
            avg_rx_throughput = 0
            avg_dl_buffer = 0
            avg_ul_buffer = 0
        
        return avg_tx_throughput, avg_rx_throughput, avg_dl_buffer, avg_ul_buffer

if __name__ == "__main__":
    monitor = PrometheusMonitor()

    # Create and start the periodic sending thread
    monitoring_thread = threading.Thread(target=monitor.update_metrics)
    monitoring_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the weight sending script.")