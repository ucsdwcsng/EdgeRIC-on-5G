from edgeric_messenger import EdgericMessenger
import threading
import time
import numpy as np

class SendMCS:
    def __init__(self):
        self.messenger = EdgericMessenger(socket_type="mcs")

    def periodic_send_mcs(self):
        while True:
            tti_count, ue_dict = self.messenger.get_metrics(True)  # get metrics
            #if tti_count is not None:
            mcs_array = self.generate_mcs_array(ue_dict)           # compute policy
            self.messenger.send_mcs(tti_count, mcs_array, True)    # send policy
    
    def generate_mcs_array(self, ue_dict):                         # Your Policy goes here
        mcs_array = []
        # mcs_array = [
        # 17921, 28,  # RNTI 4601 with MCS 20
        # 17922, 15,  # RNTI 4602 with MCS 10
        # ]
        for rnti in ue_dict.keys():
            mcs_value = np.random.randint(10, 20)  # Random MCS value between 10 and 28
            mcs_array.extend([rnti, mcs_value])

        return mcs_array

if __name__ == "__main__":
    send_mcs = SendMCS()

    # Create and start the periodic sending thread
    send_mcs_thread = threading.Thread(target=send_mcs.periodic_send_mcs)
    send_mcs_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the MCS sending script.")
