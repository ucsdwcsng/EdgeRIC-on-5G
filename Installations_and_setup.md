### How this repository is structured
```bash
├── /open5gs            # Contains the open5gs configs which should be copied to folder ~/etc/open5gs on the machine you are running this network 
├── /srsRAN_4G          # Contains the 4G srsue
├── /srsRAN_Project     # Contains the unmodified srsRAN gnb
├── /srsRAN_Project-ER  # Contains the modified srsRAN gnb with EdgeRIC hooks 
```
### Package Installations
```bash
# For UHD
sudo apt-get update
sudo apt-get install build-essential cmake libboost-all-dev libusb-1.0-0-dev python3 python3-numpy python3-mako
# For srsRAN
sudo apt-get install cmake make gcc g++ pkg-config libfftw3-dev libmbedtls-dev libsctp-dev libyaml-cpp-dev libgtest-dev
# OR - for ubuntu 20
sudo apt install libmbedtls-dev
sudo apt install libpcsclite-dev
sudo apt install libsctp-dev
sudo apt install libconfig++-dev
sudo apt install libbladerf-dev
sudo apt install libdw-dev libbfd-dev
sudo apt install libdwarf-dev libelf-dev
# install zmq
sudo apt-get install libzmq3-dev
```
### Open5gs installation on Ubuntu 20
Official documentation: [open5gs-quickstart](https://open5gs.org/open5gs/docs/guide/01-quickstart/)
```bash
sudo apt update
sudo apt install gnupg
curl -fsSL https://pgp.mongodb.com/server-6.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
sudo add-apt-repository ppa:open5gs/latest
sudo apt update
sudo apt install open5gs

# Install webui
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

 # Create deb repository
NODE_MAJOR=20
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list

 # Run Update and Install webui
sudo apt update
sudo apt install nodejs -y
curl -fsSL https://open5gs.org/open5gs/assets/webui/install | sudo -E bash -
```
**how to know open5gs is installed?**  
Run ``ps aux | grep open5gs`` --> this will show 16 active processes  
**Where are open5gs configs located?**  
``~/etc/open5gs`` --> folder contains all config files as .yaml --> to write, you need to change permission --> ``sudo chmod a+w ~/etc/open5gs/``  
This repository contains all the open5gs configs used in folder ``open5gs``  
**How to update UE data base on open5gs core network?**  
``http://localhost:9999`` --> username: admin, password: 1423, add all UE sim credentials, press ``Add a subscriber`` 

### UHD installation from source
```bash
https://github.com/EttusResearch/uhd.git
cd uhd
git checkout UHD-4.6 # or whichever UHD version desired
cd host
mkdir build
cd build
cmake ../
make
sudo make install
sudo ldconfig
```
### srsRAN installation from source
```bash
# to install the srsue
cd srsRAN_4G
mkdir build
cd build
cmake ../ # to build with zmq mode, use "cmake ../ -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON"
make
cd ../..
# to install the srsRAN gnb
cd srsRAN_Project # for vanilla srsRAN gnb or srsRAN_Project-ER for edgeric version of srsgnb
mkdir build
cd build
cmake ../ # to build with zmq mode, use "cmake ../ -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON"
make
cd ../..
```

### Config Files
``/srsRAN_4g/.config/ue-4g-zmq.conf`` --> config file to run 1 srsue in zmq mode, check section ``[usim]`` and appropriately add those credentials in the open5gs webui database  
``/srsRAN_4g/.config/ue1-4g-zmq.conf`` --> config file for UE1 in multi UE zmq mode, check section ``[usim]`` and appropriately add those credentials in the open5gs webui database  
``/srsRAN_4g/.config/ue2-4g-zmq.conf`` --> config file for UE2 in multi UE zmq mode, check section ``[usim]`` and appropriately add those credentials in the open5gs webui database  
``/srsRAN_Project/configs/n32-=ota-amarisoft.yml`` --> run srsgnb in Over the air mode with usrp N320, in section ``cell_cfg`` you can change the band and bandwidth of operation  
``/srsRAN_Project/configs/zmq-mode.yml`` --> run srsgnb in zmq mode with 1 srsue 
``/srsRAN_Project/configs/zmq-mode-multi-ue.yml`` --> run srsgnb in zmq mode for multiple UEs 

### Running the network
```bash
# Run gnb
cd srsRAN_Project/build/apps/gnb
sudo ./gnb -c ../../configs/<mention your config file name>
# Run UE
cd srsRAN_4G/build
sudo ./srsue/src/srsue ../.config/<mention your config file>
```
### Running multiple UEs in emulation mode
We need to use a grc broker in this case  
**Installing GNU radio**  
```bash
sudo apt update
sudo apt install gnuradio
```
For 2UEs, the gnu file is provided ``2ue-zmq-mode-23.04Mhz.py``  
Corresponding UE configs ``/srsRAN_4G/.config/ue1-zmq-mode.conf and ue2-zmq-mode.conf`` for the 2 UEs  
Corresponding gnb config: ``/srsRAN_Project/configs/zmq-mode-multi-ue.yml``
