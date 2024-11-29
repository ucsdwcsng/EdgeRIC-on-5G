import zmq
import control_weights_pb2
import time

context = zmq.Context()
subscriber_weights_socket = context.socket(zmq.SUB)
subscriber_weights_socket.setsockopt_string(zmq.SUBSCRIBE, "")
subscriber_weights_socket.connect("ipc:///tmp/control_weights_actions")

def process_weights_message(message):
    weights_msg = control_weights_pb2.SchedulingWeights()
    weights_msg.ParseFromString(message)
    print(f"Received SchedulingWeights - Ran Index: {weights_msg.ran_index}")
    for i in range(0, len(weights_msg.weights), 2):
        rnti = weights_msg.weights[i]
        weight = weights_msg.weights[i + 1]
        print(f"  RNTI: {rnti}, Weight: {weight}")

while True:
    time.sleep(0.001)
    try:
        message = subscriber_weights_socket.recv()
        process_weights_message(message)
        
    except zmq.Again:
        pass
    except Exception as e:
        print(f"Error receiving SchedulingWeights: {e}")
