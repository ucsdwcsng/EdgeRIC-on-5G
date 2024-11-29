# import zmq
# import control_weights_pb2
# import control_mcs_pb2
# import time
# import threading
# # Initialize the ZeroMQ context
# context = zmq.Context()

# # Create a subscriber socket for SchedulingWeights
# subscriber_weights_socket = context.socket(zmq.SUB)
# subscriber_weights_socket.setsockopt_string(zmq.SUBSCRIBE, "")
# subscriber_weights_socket.connect("ipc:///tmp/control_weights_actions")

# context2 = zmq.Context()
# # Create a subscriber socket for MCS
# subscriber_mcs_socket = context2.socket(zmq.SUB)
# subscriber_mcs_socket.setsockopt_string(zmq.SUBSCRIBE, "")
# subscriber_mcs_socket.connect("ipc:///tmp/control_mcs_actions")

# # Function to process and print SchedulingWeights messages
# def process_weights_message(message):
#     weights_msg = control_weights_pb2.SchedulingWeights()
#     weights_msg.ParseFromString(message)
#     print(f"Received SchedulingWeights - Ran Index: {weights_msg.ran_index}")
#     for i in range(0, len(weights_msg.weights), 2):
#         rnti = weights_msg.weights[i]
#         weight = weights_msg.weights[i + 1]
#         print(f"  RNTI: {rnti}, Weight: {weight}")

# # Function to process and print MCS messages
# def process_mcs_message(message):
#     mcs_msg = control_mcs_pb2.mcs_control()
#     mcs_msg.ParseFromString(message)
#     print(f"Received MCS Control - Ran Index: {mcs_msg.ran_index}")
#     for i in range(0, len(mcs_msg.mcs), 2):
#         rnti = mcs_msg.mcs[i]
#         mcs_value = mcs_msg.mcs[i + 1]
#         print(f"  RNTI: {rnti}, MCS: {mcs_value}")

# def receive_mcs():
#     while True:
#         time.sleep(0.001)
#         try:
#             message = subscriber_weights_socket.recv(zmq.DONTWAIT)
#             process_weights_message(message)
#         except zmq.Again:
#             # No message, continue to the next iteration
#             pass    
#         except Exception as e:
#             print(e)

# def receive_weight():
#     while True:
#         time.sleep(0.001)
#         try:
#             message = subscriber_mcs_socket.recv(zmq.DONTWAIT)
#             process_mcs_message(message)
#         except zmq.Again:
#             # No message, continue to the next iteration
#             pass    
#         except Exception as e:
#             print(e)

# if __name__ == "__main__":
#     rec_mcs_thread = threading.Thread(target=receive_mcs)
#     rec_mcs_thread.start()

#     rec_wt_thread = threading.Thread(target=receive_weight)
#     rec_wt_thread.start()
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("Stopping the MCS sending script.")

# ######################################################        

# # Continuously listen to both subscribers sequentially and process messages
# # # 
    

#     # try:
#     #     # Listen to SchedulingWeights socket
#     #     try:
#     #         message = subscriber_weights_socket.recv(zmq.DONTWAIT)
#     #         process_weights_message(message)
#     #     except Exception as e:
#     #         print(e)
#     #     # except zmq.Again:
#     #     #     print("No SchedulingWeights message received.")

#     #     # Listen to MCS socket
#     #     try:
#     #         message = subscriber_mcs_socket.recv(zmq.DONTWAIT)
#     #         process_mcs_message(message)
#     #     except Exception as e:
#     #         print(e)
#     #     # except zmq.Again:
#     #     #     print("No MCS message received.")
    
#     # except KeyboardInterrupt:
#     #     print("Terminating listener...")
#         # break

# # Clean up ZeroMQ context
# # context.term()
#########################################################
import zmq
import control_weights_pb2
import control_mcs_pb2
import time
from multiprocessing import Process

# Function to process and print SchedulingWeights messages
def process_weights_message(message):
    weights_msg = control_weights_pb2.SchedulingWeights()
    weights_msg.ParseFromString(message)
    print(f"Received SchedulingWeights - Ran Index: {weights_msg.ran_index}")
    for i in range(0, len(weights_msg.weights), 2):
        rnti = weights_msg.weights[i]
        weight = weights_msg.weights[i + 1]
        print(f"  RNTI: {rnti}, Weight: {weight}")

# Function to process and print MCS messages
def process_mcs_message(message):
    mcs_msg = control_mcs_pb2.mcs_control()
    mcs_msg.ParseFromString(message)
    print(f"Received MCS Control - Ran Index: {mcs_msg.ran_index}")
    for i in range(0, len(mcs_msg.mcs), 2):
        rnti = mcs_msg.mcs[i]
        mcs_value = mcs_msg.mcs[i + 1]
        print(f"  RNTI: {rnti}, MCS: {mcs_value}")

# Process for receiving SchedulingWeights
def receive_weights():
    context = zmq.Context()  # Create a new context for this process
    subscriber_weights_socket = context.socket(zmq.SUB)
    subscriber_weights_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    subscriber_weights_socket.connect("ipc:///tmp/control_weights_actions")
    while True:
        try:
            message = subscriber_weights_socket.recv()
            process_weights_message(message)
        except zmq.Again:
            pass
        except Exception as e:
            print(f"Error receiving SchedulingWeights: {e}")

# Process for receiving MCS Control
def receive_mcs():
    context = zmq.Context()  # Create a new context for this process
    subscriber_mcs_socket = context.socket(zmq.SUB)
    subscriber_mcs_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    subscriber_mcs_socket.connect("ipc:///tmp/control_mcs_actions")
    while True:
        try:
            message = subscriber_mcs_socket.recv()
            process_mcs_message(message)
        except zmq.Again:
            pass
        except Exception as e:
            print(f"Error receiving MCS Control: {e}")

# Start the processes
weights_process = Process(target=receive_weights)
weights_process.start()

mcs_process = Process(target=receive_mcs)
mcs_process.start()

# Keep the main process alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping the listeners.")

    weights_process.terminate()
    mcs_process.terminate()


