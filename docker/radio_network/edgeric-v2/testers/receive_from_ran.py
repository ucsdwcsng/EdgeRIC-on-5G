import zmq
import metrics_pb2  # This is the generated Python file from your .proto file

# Create a ZMQ context
context = zmq.Context()

# Create a subscriber socket
subscriber = context.socket(zmq.SUB)
subscriber.connect("ipc:///tmp/metrics")

# Subscribe to all messages
subscriber.setsockopt_string(zmq.SUBSCRIBE, "")

# Enable conflate mode to keep only the latest message
subscriber.setsockopt(zmq.CONFLATE, 1)

def get_metrics():
    ue_dict = {}
    tti_count = None

    print(" In main")
    while True:
        try:
            # Receive the message
            message = subscriber.recv()

            # Parse the received message using Protobuf
            metrics = metrics_pb2.Metrics()
            metrics.ParseFromString(message)

            # Store the TTI count
            tti_count = metrics.tti_cnt

            # Clear the ue_dict before storing new metrics
            ue_dict.clear()

            # Store the details for each UE in the dictionary
            for ue_metrics in metrics.ue_metrics:
                ue_dict[ue_metrics.rnti] = {
                    "cqi": ue_metrics.cqi,
                    "snr": ue_metrics.snr
                }

            # Print the TTI count and UE metrics dictionary for debugging
            print(f"TTI Count: {tti_count}")
            print(f"UE Metrics: {ue_dict}")

            # Optionally, break after one message for demo purposes
            # break

        except KeyboardInterrupt:
            print("Interrupted")
            break

    return tti_count, ue_dict

if __name__ == "__main__":
    tti_count, ue_dict = get_metrics()
    print(f"Final TTI Count: {tti_count}")
    print(f"Final UE Metrics Dictionary: {ue_dict}")

