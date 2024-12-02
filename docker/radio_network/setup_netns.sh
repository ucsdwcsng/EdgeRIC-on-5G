#!/bin/bash

# Add network namespaces
ip netns add ue1
ip netns add ue2
ip netns add ue3
ip netns add ue4

# cd /home/EdgeRIC-A-real-time-RIC
# cd srsRAN-5G-ER
# rm -rf build
# mkdir build
# cd build
# #cmake ../ -DCMAKE_BUILD_TYPE=Debug -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON
# cmake ../ -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON
# make -j `nproc`

# cd ../../srs-4G-UE
# rm -rf build
# mkdir build
# cd build
# cmake ../
# make -j `nproc`

# Keep the container running if needed
tail -f /dev/null
