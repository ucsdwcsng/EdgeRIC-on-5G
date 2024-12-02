#!/bin/bash

# Add network namespaces

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
redis-server & 
tail -f /dev/null
