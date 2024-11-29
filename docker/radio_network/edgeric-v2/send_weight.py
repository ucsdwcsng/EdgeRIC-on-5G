from edgeric_messenger import EdgericMessenger
import threading
import time
import numpy as np

class SendWeight:
    def __init__(self):
        self.messenger = EdgericMessenger(socket_type="weights")

    def periodic_send_weight(self):
        while True:
            tti_count, ue_dict = self.messenger.get_metrics(True)                # get metrics
            # if tti_count is not None:
            weight_array = self.generate_weight_array(ue_dict)                   # compute policy
            self.messenger.send_scheduling_weight(tti_count, weight_array, True) # send policy
    
    def generate_weight_array(self, ue_dict):
        weight_array = []
        weight_array = [
        17921, 0.7,  # RNTI 4601 with weight 0.7
        17922, 0.3,  # RNTI 4602 with weight 0.3  # RNTI 1003 with weight 0.2
        ]   
        # for rnti in ue_dict.keys():
        #     weight_value = np.random.rand()
        #     weight_array.extend([rnti, weight_value])

        return weight_array


if __name__ == "__main__":
    send_weight = SendWeight()

    # Create and start the periodic sending thread
    send_weight_thread = threading.Thread(target=send_weight.periodic_send_weight)
    send_weight_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the weight sending script.")



        
